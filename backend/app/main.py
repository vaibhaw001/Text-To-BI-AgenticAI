import os
import json
import logging
import shutil
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.schema import ChartRequest, ChartResponse
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

@app.post("/api/generate-chart", response_model=ChartResponse)
async def generate_chart(request: ChartRequest):
    logger.info(f"Received chart request. Prompt: {request.prompt}")
    
    try:
        # 1. Initialize DataModel based on single or multi-table request
        if request.tables:
            logger.info(f"Initializing relational model with {len(request.tables)} tables.")
            loaded_tables = {}
            for t_config in request.tables:
                loaded_tables[t_config.name] = read_dataset(t_config.path)
            
            data_model = DataModel(tables=loaded_tables, relationships=request.relationships)
            
        elif request.file_path:
            logger.info(f"Initializing single-table model from: {request.file_path}")
            df = read_dataset(request.file_path)
            data_model = DataModel(tables={"df": df}, relationships={})
            
        else:
            raise ValueError("Either 'file_path' or 'tables' must be provided in the request.")

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
