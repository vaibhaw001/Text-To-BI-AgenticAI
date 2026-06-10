import os
import json
import logging
import shutil
import pandas as pd
import sqlalchemy as sa
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.schema import ChartRequest, ChartResponse, DbConnectionConfig, MetricConfig
from app.core.data import read_dataset, DataModel
from app.core.agent import generate_chart_with_retry

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
async def generate_chart(request: ChartRequest):
    logger.info(f"Received chart request. Prompt: {request.prompt}")
    
    try:
        # 1. Initialize DataModel based on single or multi-table request
        if request.tables:
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
            data_model = DataModel(tables={"df": df}, relationships={})
            
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
            data_model=data_model
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

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
