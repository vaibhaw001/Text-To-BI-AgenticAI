from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class DbConnectionConfig(BaseModel):
    db_type: str = Field(..., description="The type of database (e.g., 'sqlite' or 'postgresql')")
    connection_string: str = Field(..., description="SQLAlchemy connection URL (e.g. sqlite:///data.db)")
    table_name: Optional[str] = Field(None, description="The table name to load from the database")
    query: Optional[str] = Field(None, description="Optional SQL query to load data instead of a full table")
    direct_query: bool = Field(False, description="If true, generates and executes SQL directly instead of loading into Pandas")

class RelationshipConfig(BaseModel):
    from_table: str = Field(..., description="Source table name")
    from_column: str = Field(..., description="Source column name")
    to_table: str = Field(..., description="Target table name")
    to_column: str = Field(..., description="Target column name")
    cardinality: str = Field("1:N", description="Relationship cardinality (1:1, 1:N, N:1, M:N)")
    cross_filter_direction: str = Field("single", description="Filter propagation direction (single, both)")
    is_active: bool = Field(True, description="Whether the relationship is active by default")

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
    relationships: Optional[List[RelationshipConfig]] = Field(
        None, 
        description="List defining star schema relationships and filter propagation"
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

class InsightRequest(BaseModel):
    file_path: Optional[str] = Field(None, description="Path of dataset (for single table queries)")
    tables: Optional[List[TableConfig]] = Field(None, description="Optional configuration for multiple relational tables")
    relationships: Optional[List[RelationshipConfig]] = Field(None, description="Table relationships mapping")
    filters: Optional[Dict[str, Any]] = Field(None, description="Current active filters applied to the dashboard")
    metrics: Optional[List[MetricConfig]] = Field(None, description="Calculated metrics catalog definitions")
    
    target_column: str = Field(..., description="The dimension column of the clicked data point (e.g. 'Quarter' or 'Region')")
    target_value: Any = Field(..., description="The value of the clicked data point (e.g. '2026-Q1' or 'West')")
    metric_column: str = Field(..., description="The metric column of interest (e.g. 'Sales')")
    comparison_value: Optional[Any] = Field(None, description="Optional comparison value (e.g. '2025-Q4' or 'East')")
    question: Optional[str] = Field(None, description="Optional custom question typed by user (e.g. 'What drives sales in the West region?')")

class KeyInfluencerItem(BaseModel):
    factor: str = Field(..., description="Name of the driving factor (e.g., 'Category: Laptop')")
    impact: str = Field(..., description="Description of the statistical impact (e.g., 'Increases average by 2.5x')")
    percentage: Optional[float] = Field(None, description="Percentage contribution to growth (e.g. 64.0) if applicable")
    type: str = Field(..., description="Whether it has a positive ('increase') or negative ('decrease') impact")

class InsightResponse(BaseModel):
    success: bool = Field(..., description="True if analysis succeeded")
    summary: str = Field(..., description="Natural language executive summary generated by LLM")
    key_influencers: List[KeyInfluencerItem] = Field(..., description="List of key influencers / driver details")
    error: Optional[str] = Field(None, description="Error details if failed")

class TooltipRequest(BaseModel):
    file_path: Optional[str] = Field(None, description="Path of dataset")
    tables: Optional[List[TableConfig]] = Field(None, description="Relational tables")
    relationships: Optional[List[RelationshipConfig]] = Field(None, description="Table relationships")
    filters: Optional[Dict[str, Any]] = Field(None, description="Current dashboard filters")
    metrics: Optional[List[MetricConfig]] = Field(None, description="Calculated metrics definitions")
    
    target_column: str = Field(..., description="The category column of the hovered point")
    target_value: Any = Field(..., description="The value of the hovered point")
    metric_column: str = Field(..., description="The metric being measured")

class TooltipResponse(BaseModel):
    success: bool = Field(..., description="True if fetch succeeded")
    date_column: Optional[str] = Field(None, description="The auto-detected date column")
    data: List[Dict[str, Any]] = Field(..., description="Time-series data array")
    error: Optional[str] = Field(None, description="Error if failed")
