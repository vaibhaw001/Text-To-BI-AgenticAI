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

def auto_detect_relationships(tables: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
    """
    Heuristically detects primary/foreign key connections across multiple DataFrames.
    Mimics Power BI's automatic relationship detection.
    """
    relationships = {}
    table_names = list(tables.keys())
    if len(table_names) < 2:
        return {}
        
    for i in range(len(table_names)):
        for j in range(len(table_names)):
            if i == j:
                continue
            table_a = table_names[i]
            table_b = table_names[j]
            cols_a = [str(c) for c in tables[table_a].columns]
            cols_b = [str(c) for c in tables[table_b].columns]
            
            # Heuristic 1: Exact matching column names (e.g. both have 'product_id' or 'store_id')
            # Ignore common non-key columns
            ignored_cols = {'date', 'name', 'description', 'status', 'id', 'index', 'sales', 'revenue', 'quantity', 'amount'}
            for col in cols_a:
                if col in cols_b and col.lower() not in ignored_cols:
                    # Link table_a.col to table_b.col
                    if table_a not in relationships:
                        relationships[table_a] = []
                    if col not in relationships[table_a]:
                        relationships[table_a].append(col)
                        
                    if table_b not in relationships:
                        relationships[table_b] = []
                    if col not in relationships[table_b]:
                        relationships[table_b].append(col)
            
            # Heuristic 2: Substring key match
            # e.g., table_b name is 'Products' (singular: 'product') and has primary key 'id'
            # table_a name is 'Sales' and has foreign key 'product_id' or 'productid'
            for col_b in cols_b:
                if col_b.lower() == 'id':
                    singular_b = table_b.lower()
                    if singular_b.endswith('s') and len(singular_b) > 1:
                        singular_b = singular_b[:-1] # convert 'products' to 'product'
                    
                    target_patterns = {f"{singular_b}_id", f"{singular_b}id", f"{singular_b}_key"}
                    for col_a in cols_a:
                        if col_a.lower() in target_patterns:
                            # Link foreign key table_a and primary key table_b
                            if table_a not in relationships:
                                relationships[table_a] = []
                            if col_a not in relationships[table_a]:
                                relationships[table_a].append(col_a)
                                
                            if table_b not in relationships:
                                relationships[table_b] = []
                            if col_b not in relationships[table_b]:
                                relationships[table_b].append(col_b)
    return relationships

class DataModel:
    def __init__(self, tables: Dict[str, pd.DataFrame], relationships: Dict[str, List[str]] = None):
        """
        Manages multiple Pandas DataFrames and their Power BI-style foreign-key relationships.
        
        Args:
            tables (Dict[str, pd.DataFrame]): Mapping of Table Name -> Pandas DataFrame
            relationships (Dict[str, List[str]]): Defines keys for relationships:
                e.g., {'Sales': ['product_id'], 'Products': ['id']}
                If empty or None, relationships are auto-detected.
        """
        self.tables = tables
        
        # If relationships are not provided, run auto-detection heuristics
        if not relationships and len(tables) >= 2:
            self.relationships = auto_detect_relationships(tables)
        else:
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
