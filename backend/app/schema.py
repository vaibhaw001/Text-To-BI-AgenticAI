from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class TableConfig(BaseModel):
    name: str = Field(..., description="The variable name assigned to the table (e.g., 'Sales')")
    path: str = Field(..., description="The absolute path to the dataset file (CSV or Excel)")

class ChartRequest(BaseModel):
    prompt: str = Field(..., description="The visualization and analysis instruction from the user")
    file_path: Optional[str] = Field(None, description="Path of dataset (for single table queries)")
    tables: Optional[List[TableConfig]] = Field(None, description="Optional configuration for multiple relational tables")
    relationships: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="Dictionary defining foreign key mappings (e.g. {'Sales': ['product_id'], 'Products': ['id']})"
    )

class ChartResponse(BaseModel):
    success: bool = Field(..., description="Whether the chart was successfully generated and executed")
    chart_json: Optional[Dict[str, Any]] = Field(None, description="The Plotly JSON schema for the generated figure")
    code: Optional[str] = Field(None, description="The final Python code that successfully created the figure")
    insights: Optional[str] = Field(None, description="AI-generated text analysis describing findings from the chart data")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Execution history with code attempts and tracebacks if any")
    error: Optional[str] = Field(None, description="Error message if the generation failed after all retries")
