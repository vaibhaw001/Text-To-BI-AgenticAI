import os
import pandas as pd
from typing import Dict, List, Any

def read_dataset(file_path: str) -> pd.DataFrame:
    """Reads a dataset from a file path supporting CSV and Excel format."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found at path: {file_path}")
    
    _, ext = os.path.splitext(file_path.lower())
    if ext == '.csv':
        return pd.read_csv(file_path)
    elif ext in ['.xls', '.xlsx']:
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Only CSV and Excel (.xls, .xlsx) are supported.")

class DataModel:
    def __init__(self, tables: Dict[str, pd.DataFrame], relationships: Dict[str, List[str]] = None):
        """
        Manages multiple Pandas DataFrames and their Power BI-style foreign-key relationships.
        
        Args:
            tables (Dict[str, pd.DataFrame]): Mapping of Table Name -> Pandas DataFrame
            relationships (Dict[str, List[str]]): Defines keys for relationships:
                e.g., {'Sales': ['product_id'], 'Products': ['id']}
                This indicates that 'Sales' table's 'product_id' connects to 'Products' table's 'id'.
        """
        self.tables = tables
        self.relationships = relationships or {}

    def get_schema_summary(self) -> str:
        """
        Generates a comprehensive summary of the relational data model including table schemas,
        sample rows, and table join relationships for LLM prompting.
        """
        summary_lines = ["# Relational Data Model Schema\n"]
        
        # 1. Add schemas for all tables
        for table_name, df in self.tables.items():
            summary_lines.append(f"## Table: {table_name}")
            summary_lines.append("### Columns & Types:")
            summary_lines.append("Column Name | Pandas/Python Data Type")
            summary_lines.append("--- | ---")
            
            dtypes_dict = df.dtypes.astype(str).to_dict()
            for col, dtype in dtypes_dict.items():
                summary_lines.append(f"`{col}` | {dtype}")
                
            # Generate 3-row sample table
            sample_df = df.head(3)
            headers = list(sample_df.columns)
            summary_lines.append("\n### 3-Row Sample Data:")
            summary_lines.append("| " + " | ".join(headers) + " |")
            summary_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            
            for _, row in sample_df.iterrows():
                str_vals = []
                for val in row:
                    val_str = str(val).replace("\n", " ").replace("|", "\\|")
                    str_vals.append(val_str)
                summary_lines.append("| " + " | ".join(str_vals) + " |")
            
            summary_lines.append("\n---\n")

        # 2. Add Relationships
        summary_lines.append("## Table Relationships (Foreign Key Mappings)")
        if not self.relationships:
            summary_lines.append("No relationships defined. If queries span multiple tables, search for matching column names to merge.")
        else:
            summary_lines.append("These tables connect using the following key column mappings:")
            for tbl, cols in self.relationships.items():
                summary_lines.append(f"- Table `{tbl}` joins using columns: `{cols}`")
            summary_lines.append("\n*Note: To query across tables, perform a merge using pd.merge() on these key columns first.*")

        return "\n".join(summary_lines)
