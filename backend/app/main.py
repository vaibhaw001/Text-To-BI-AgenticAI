import os
import json
import logging
import shutil
import pandas as pd
import sqlalchemy as sa
from fastapi import FastAPI, HTTPException, File, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional

from app.schema import ChartRequest, ChartResponse, DbConnectionConfig, MetricConfig, InsightRequest, InsightResponse, TooltipRequest, TooltipResponse
from app.core.data import read_dataset, DataModel
from app.core.agent import generate_chart_with_retry
from app.core.analytics import merge_data_model, perform_change_attribution, perform_key_influencers, generate_analytics_summary

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("text-to-bi-backend")

load_dotenv()

app = FastAPI(
    title="Agentic Text-to-BI Backend",
    description="FastAPI service for transforming natural language queries into Plotly visualizations using LangChain and a secure execution engine.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust in production to allow only Next.js frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "text-to-bi-backend"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"Received file upload request: {file.filename}")
    try:
        # Create data directory under backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(backend_dir, "data")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        absolute_path = os.path.abspath(file_path)
        logger.info(f"File saved successfully to {absolute_path}")
        
        return {
            "success": True,
            "file_name": file.filename,
            "file_path": absolute_path
        }
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

def read_db_table(config: DbConnectionConfig) -> pd.DataFrame:
    try:
        engine = sa.create_engine(config.connection_string)
        with engine.connect() as conn:
            if config.query:
                logger.info(f"Loading data via query from connection string: {config.connection_string}")
                return pd.read_sql_query(sa.text(config.query), conn)
            elif config.table_name:
                logger.info(f"Loading table '{config.table_name}' from connection string: {config.connection_string}")
                return pd.read_sql_query(sa.text(f"SELECT * FROM {config.table_name}"), conn)
            else:
                raise ValueError("Either 'table_name' or 'query' must be specified in the database connection configuration.")
    except Exception as e:
        logger.error(f"Failed to read database table: {str(e)}", exc_info=True)
        raise ValueError(f"Database error: {str(e)}")

@app.post("/api/test-db")
async def test_db_connection(config: DbConnectionConfig):
    logger.info(f"Testing DB connection for {config.connection_string}")
    try:
        engine = sa.create_engine(config.connection_string)
        with engine.connect() as conn:
            if config.query:
                df = pd.read_sql_query(sa.text(f"SELECT * FROM ({config.query}) as subq LIMIT 5"), conn)
            elif config.table_name:
                df = pd.read_sql_query(sa.text(f"SELECT * FROM {config.table_name} LIMIT 5"), conn)
            else:
                conn.execute(sa.text("SELECT 1"))
                return {"success": True, "columns": [], "sample_rows": [], "message": "Connection successful!"}
                
            cols = list(df.columns)
            rows = df.head(3).to_dict(orient="records")
            # Convert non-serializable objects (like datetime) to string representation
            import datetime
            for r in rows:
                for k, v in r.items():
                    if isinstance(v, (datetime.date, datetime.datetime)):
                        r[k] = str(v)
            
            return {
                "success": True,
                "columns": cols,
                "sample_rows": rows,
                "message": f"Successfully connected! Found columns: {', '.join(cols)}"
            }
    except Exception as e:
        logger.error(f"DB Connection test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/generate-chart", response_model=ChartResponse)
async def generate_chart(request: ChartRequest, x_api_key: Optional[str] = Header(None)):
    logger.info(f"Received chart request. Prompt: {request.prompt}")
    
    try:
        is_direct_query = any(t.db_connection and t.db_connection.direct_query for t in request.tables) if request.tables else False
        
        # 1. Initialize DataModel based on single or multi-table request
        if is_direct_query:
            logger.info("Using DirectQuery Mode for database connection.")
            from app.core.direct_query import execute_direct_query
            # Get the first direct_query connection string
            conn_string = next(t.db_connection.connection_string for t in request.tables if t.db_connection and t.db_connection.direct_query)
            
            # Execute SQL via LLM and get result
            df = execute_direct_query(request.prompt, conn_string, x_api_key)
            data_model = DataModel(tables={"df_direct": df}, relationships=[])
            
            # Since the data is already aggregated by the SQL query, 
            # we append a hint to the prompt for the visualization agent
            request.prompt = f"Using the pre-aggregated data, {request.prompt}"
            
        elif request.tables:
            logger.info(f"Initializing relational model with {len(request.tables)} tables.")
            loaded_tables = {}
            for t_config in request.tables:
                if t_config.db_connection:
                    loaded_tables[t_config.name] = read_db_table(t_config.db_connection)
                elif t_config.path:
                    loaded_tables[t_config.name] = read_dataset(t_config.path)
                else:
                    raise ValueError(f"Table '{t_config.name}' must have either 'path' or 'db_connection' configured.")
            
            data_model = DataModel(tables=loaded_tables, relationships=request.relationships)
            
        elif request.file_path:
            logger.info(f"Initializing single-table model from: {request.file_path}")
            df = read_dataset(request.file_path)
            data_model = DataModel(tables={"df": df}, relationships=[])
            
        else:
            raise ValueError("Either 'file_path' or 'tables' must be provided in the request.")

        # Evaluate custom calculated metrics on loaded DataFrames
        if request.metrics:
            logger.info(f"Evaluating custom metrics: {len(request.metrics)}")
            for metric in request.metrics:
                tbl_name = metric.table
                if len(data_model.tables) == 1:
                    tbl_name = list(data_model.tables.keys())[0]
                
                if tbl_name in data_model.tables:
                    df = data_model.tables[tbl_name]
                    try:
                        data_model.tables[tbl_name][metric.name] = df.eval(metric.expression)
                        logger.info(f"Evaluated metric column '{metric.name}' successfully on table '{tbl_name}'")
                    except Exception as e:
                        logger.error(f"Failed to evaluate metric expression '{metric.expression}' on table '{tbl_name}': {str(e)}")
                        raise ValueError(f"Failed to calculate metric '{metric.name}' on '{tbl_name}': {str(e)}")
                else:
                    raise ValueError(f"Target table '{tbl_name}' for metric '{metric.name}' was not found in the loaded data model.")

        # Apply filters to DataFrames if provided
        if request.filters:
            logger.info(f"Applying filters to dataset: {request.filters}")
            for col, val in request.filters.items():
                for tbl_name, df in data_model.tables.items():
                    if col in df.columns:
                        if isinstance(val, list):
                            data_model.tables[tbl_name] = df[df[col].isin(val)]
                        else:
                            data_model.tables[tbl_name] = df[df[col] == val]

        # 2. Extract schema summary
        schema_summary = data_model.get_schema_summary()
        
        # Append calculated metrics context to schema_summary for LLM visibility
        if request.metrics:
            schema_summary += "\n\n## Custom Calculated Metrics (Pre-calculated and available as columns):\n"
            for metric in request.metrics:
                target_name = list(data_model.tables.keys())[0] if len(data_model.tables) == 1 else metric.table
                schema_summary += f"- Table `{target_name}` contains custom column `{metric.name}` calculated as: `{metric.expression}`\n"
        
        logger.debug(f"Generated schema summary:\n{schema_summary}")
        
        # 3. Call agent with self-correction loop
        fig, history, final_code, insights = generate_chart_with_retry(
            prompt=request.prompt,
            schema_summary=schema_summary,
            data_model=data_model,
            api_key=x_api_key
        )
        
        # 4. Convert figure to JSON representation
        chart_dict = json.loads(fig.to_json())
        logger.info("Successfully generated chart and converted to JSON.")
        
        return ChartResponse(
            success=True,
            chart_json=chart_dict,
            code=final_code,
            insights=insights,
            history=history
        )
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        return ChartResponse(
            success=False,
            error=f"File not found: {str(e)}",
            history=[]
        )
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return ChartResponse(
            success=False,
            error=str(e),
            history=[]
        )
    except Exception as e:
        logger.error(f"Unexpected error during chart generation: {str(e)}", exc_info=True)
        return ChartResponse(
            success=False,
            error=f"Execution/Generation Error: {str(e)}",
            history=locals().get('history', [])
        )

@app.post("/api/explain-insight", response_model=InsightResponse)
async def explain_insight(request: InsightRequest, x_api_key: Optional[str] = Header(None)):
    import numpy as np
    logger.info(f"Received explain-insight request. Target: {request.target_column}={request.target_value}, Metric: {request.metric_column}")
    try:
        # 1. Load the data (similar to generate-chart)
        if request.tables:
            logger.info(f"Loading relational tables: {len(request.tables)}")
            loaded_tables = {}
            for t_config in request.tables:
                if t_config.db_connection:
                    loaded_tables[t_config.name] = read_db_table(t_config.db_connection)
                elif t_config.path:
                    loaded_tables[t_config.name] = read_dataset(t_config.path)
                else:
                    raise ValueError(f"Table '{t_config.name}' must have either 'path' or 'db_connection' configured.")
            data_model = DataModel(tables=loaded_tables, relationships=request.relationships)
        elif request.file_path:
            logger.info(f"Loading single table: {request.file_path}")
            df = read_dataset(request.file_path)
            data_model = DataModel(tables={"df": df}, relationships=[])
        else:
            raise ValueError("Either 'file_path' or 'tables' must be provided in the request.")

        # Evaluate custom calculated metrics on loaded DataFrames
        if request.metrics:
            logger.info(f"Evaluating custom metrics: {len(request.metrics)}")
            for metric in request.metrics:
                tbl_name = metric.table
                if len(data_model.tables) == 1:
                    tbl_name = list(data_model.tables.keys())[0]
                
                if tbl_name in data_model.tables:
                    df = data_model.tables[tbl_name]
                    try:
                        data_model.tables[tbl_name][metric.name] = df.eval(metric.expression)
                    except Exception as e:
                        logger.error(f"Failed to evaluate metric '{metric.name}' on table '{tbl_name}': {str(e)}")
                        raise ValueError(f"Failed to calculate metric '{metric.name}': {str(e)}")
                else:
                    raise ValueError(f"Target table '{tbl_name}' for metric '{metric.name}' not found.")

        # Apply filters to DataFrames if provided
        if request.filters:
            logger.info(f"Applying filters to dataset: {request.filters}")
            for col, val in request.filters.items():
                for tbl_name, df in data_model.tables.items():
                    if col in df.columns:
                        if isinstance(val, list):
                            data_model.tables[tbl_name] = df[df[col].isin(val)]
                        else:
                            data_model.tables[tbl_name] = df[df[col] == val]

        # 2. Merge data model tables into a single unified DataFrame
        df_merged = merge_data_model(data_model)
        if df_merged.empty:
            raise ValueError("The dataset is empty after loading and filtering.")

        # Verify target column and metric column exist
        if request.target_column not in df_merged.columns:
            raise ValueError(f"Target column '{request.target_column}' was not found in the dataset columns: {list(df_merged.columns)}")
        
        # Verify metric column
        if request.metric_column not in df_merged.columns:
            # Case insensitive search
            found = False
            for col in df_merged.columns:
                if col.lower() == request.metric_column.lower():
                    request.metric_column = col
                    found = True
                    break
            if not found:
                numeric_cols = df_merged.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    request.metric_column = numeric_cols[0]
                else:
                    raise ValueError(f"Metric column '{request.metric_column}' was not found, and no numeric fallback column exists.")

        if not x_api_key:
            raise ValueError("API Key is required. Please provide it in the frontend settings.")
            
        # 3. Instantiate LLM based on environment configuration
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model_name = os.getenv("LLM_MODEL", "gpt-4o")
        
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.0,
                google_api_key=x_api_key
            )
        elif provider == "groq":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model_name,
                temperature=0.0,
                openai_api_key=x_api_key,
                openai_api_base="https://api.groq.com/openai/v1"
            )
        else:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model_name,
                temperature=0.0,
                openai_api_key=x_api_key
            )

        # 4. Perform Statistical Analysis
        baseline_stats = {}
        if request.comparison_value is not None:
            # Change Attribution
            comp_val, target_val, drivers = perform_change_attribution(
                df_merged,
                request.target_column,
                request.target_value,
                request.comparison_value,
                request.metric_column
            )
            net_change = target_val - comp_val
            pct_change = (net_change / comp_val) * 100.0 if comp_val != 0 else 0.0
            baseline_stats = {
                "comp_total": comp_val,
                "target_total": target_val,
                "net_change": net_change,
                "pct_change": pct_change
            }
            influencers = [
                KeyInfluencerItem(
                    factor=d["factor"],
                    impact=f"Contributed {d['percentage']}% ({d['absolute_change']:.2f} absolute) to the total change",
                    percentage=d["percentage"],
                    type=d["type"]
                ) for d in drivers
            ]
        else:
            # Key Influencers / drivers
            drivers = perform_key_influencers(
                df_merged,
                request.target_column,
                request.target_value,
                request.metric_column
            )
            baseline_avg = float(df_merged[request.metric_column].mean()) if len(df_merged) > 0 else 0.0
            baseline_stats = {
                "baseline_avg": baseline_avg
            }
            influencers = [
                KeyInfluencerItem(
                    factor=d["factor"],
                    impact=d["impact"],
                    percentage=d["percentage"],
                    type=d["type"]
                ) for d in drivers
            ]

        # 5. Generate AI Executive Summary via LLM
        summary = generate_analytics_summary(
            metric_col=request.metric_column,
            target_col=request.target_column,
            target_val=request.target_value,
            comparison_val=request.comparison_value,
            question=request.question,
            baseline_stats=baseline_stats,
            drivers=drivers,
            llm=llm
        )

        return InsightResponse(
            success=True,
            summary=summary,
            key_influencers=influencers
        )

    except Exception as e:
        logger.error(f"Error in explain-insight: {str(e)}", exc_info=True)
        return InsightResponse(
            success=False,
            summary=f"Analysis failed: {str(e)}",
            key_influencers=[],
            error=str(e)
        )

@app.post("/api/tooltip-data", response_model=TooltipResponse)
async def get_tooltip_data(request: TooltipRequest):
    import numpy as np
    logger.info(f"Received tooltip-data request. Target: {request.target_column}={request.target_value}, Metric: {request.metric_column}")
    try:
        # Load the data
        if request.tables:
            loaded_tables = {}
            for t_config in request.tables:
                if t_config.db_connection:
                    loaded_tables[t_config.name] = read_db_table(t_config.db_connection)
                elif t_config.path:
                    loaded_tables[t_config.name] = read_dataset(t_config.path)
                else:
                    raise ValueError(f"Table '{t_config.name}' must have either 'path' or 'db_connection' configured.")
            data_model = DataModel(tables=loaded_tables, relationships=request.relationships)
        elif request.file_path:
            df = read_dataset(request.file_path)
            data_model = DataModel(tables={"df": df}, relationships=[])
        else:
            raise ValueError("Either 'file_path' or 'tables' must be provided.")

        # Apply global filters first
        if request.filters:
            for col, val in request.filters.items():
                for tbl_name, df in data_model.tables.items():
                    if col in df.columns:
                        if isinstance(val, list):
                            data_model.tables[tbl_name] = df[df[col].isin(val)]
                        else:
                            data_model.tables[tbl_name] = df[df[col] == val]

        # Merge data model into a single DataFrame
        df_merged = merge_data_model(data_model)
        if df_merged.empty:
            raise ValueError("Dataset is empty.")

        # Resolve metric column
        if request.metric_column not in df_merged.columns:
            for col in df_merged.columns:
                if col.lower() == request.metric_column.lower():
                    request.metric_column = col
                    break

        # Filter by hovered value
        if request.target_column in df_merged.columns:
            # Handle potential string conversions for matching
            df_filtered = df_merged[df_merged[request.target_column].astype(str) == str(request.target_value)]
        else:
            df_filtered = df_merged

        # Identify date column for historical trend
        date_col = None
        for col in df_filtered.columns:
            if pd.api.types.is_datetime64_any_dtype(df_filtered[col]):
                date_col = col
                break
        
        # If no strict datetime, check string columns that might be dates
        if not date_col:
            for col in df_filtered.columns:
                if 'date' in col.lower() or 'month' in col.lower() or 'year' in col.lower():
                    date_col = col
                    break
                    
        # Grouping logic
        if date_col:
            # Group by date column and sum the metric
            # Drop NaNs in date
            df_trend = df_filtered.dropna(subset=[date_col])
            
            # Sort chronologically if it's a datetime
            if pd.api.types.is_datetime64_any_dtype(df_trend[date_col]):
                df_trend = df_trend.sort_values(by=date_col)
                df_trend[date_col] = df_trend[date_col].dt.strftime('%Y-%m-%d')
            
            grouped = df_trend.groupby(date_col)[request.metric_column].sum().reset_index()
            # Rename for uniform frontend parsing
            grouped = grouped.rename(columns={date_col: 'label', request.metric_column: 'value'})
            
            data_out = grouped.to_dict(orient="records")
            return TooltipResponse(success=True, date_column=date_col, data=data_out)
        else:
            # No date column found, fallback to distribution of another categorical column
            cat_cols = df_filtered.select_dtypes(include=['object', 'category']).columns
            fallback_col = None
            for c in cat_cols:
                if c != request.target_column and df_filtered[c].nunique() > 1:
                    fallback_col = c
                    break
                    
            if fallback_col:
                grouped = df_filtered.groupby(fallback_col)[request.metric_column].sum().reset_index()
                grouped = grouped.rename(columns={fallback_col: 'label', request.metric_column: 'value'})
                data_out = grouped.to_dict(orient="records")
                return TooltipResponse(success=True, date_column=fallback_col, data=data_out)
            else:
                # Absolute fallback
                val = float(df_filtered[request.metric_column].sum())
                return TooltipResponse(success=True, date_column="Total", data=[{"label": "Total", "value": val}])

    except Exception as e:
        logger.error(f"Error in tooltip-data: {str(e)}", exc_info=True)
        return TooltipResponse(success=False, data=[], error=str(e))

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
