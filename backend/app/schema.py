from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class DbConnectionConfig(BaseModel):
    db_type: str = Field(..., description="The type of database (e.g., 'sqlite' or 'postgresql')")
    connection_string: str = Field(..., description="SQLAlchemy connection URL (e.g. sqlite:///data.db)")
    table_name: Optional[str] = Field(None, description="The table name to load from the database")
    query: Optional[str] = Field(None, description="Optional SQL query to load data instead of a full table")

class TableConfig(BaseModel):
    name: str = Field(..., description="The variable name assigned to the table (e.g., 'Sales')")
    path: Optional[str] = Field(None, description="The absolute path to the dataset file (CSV or Excel)")
    db_connection: Optional[DbConnectionConfig] = Field(None, description="Database connection details if loading from a DB")

class MetricConfig(BaseModel):
    name: str = Field(..., description="The name of the metric column")
    expression: str = Field(..., description="Calculated metric expression (e.g., '(Revenue - Cost) / Revenue')")
    table: str = Field(..., description="The target table name to append the metric column to")

class ChartRequest(BaseModel):
    prompt: str = Field(..., description="The visualization and analysis instruction from the user")
    file_path: Optional[str] = Field(None, description="Path of dataset (for single table queries)")
    tables: Optional[List[TableConfig]] = Field(None, description="Optional configuration for multiple relational tables")
    relationships: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="Dictionary defining foreign key mappings (e.g. {'Sales': ['product_id'], 'Products': ['id']})"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Dictionary of filters to slice the dataset prior to code execution (e.g. {'Region': 'North'})"
    )
    metrics: Optional[List[MetricConfig]] = Field(
        None,
        description="Calculated metrics catalog definitions"
    )

class ChartResponse(BaseModel):
    success: bool = Field(..., description="Whether the chart was successfully generated and executed")
    chart_json: Optional[Dict[str, Any]] = Field(None, description="The Plotly JSON schema for the generated figure")
    code: Optional[str] = Field(None, description="The final Python code that successfully created the figure")
    insights: Optional[str] = Field(None, description="AI-generated text analysis describing findings from the chart data")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Execution history with code attempts and tracebacks if any")
    error: Optional[str] = Field(None, description="Error message if the generation failed after all retries")
