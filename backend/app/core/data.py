import os
import pandas as pd
from typing import Dict, List, Any, Optional
from app.schema import RelationshipConfig

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

def auto_detect_relationships(tables: Dict[str, pd.DataFrame]) -> List[RelationshipConfig]:
    """
    Heuristically detects primary/foreign key connections across multiple DataFrames.
    Mimics Power BI's automatic relationship detection.
    """
    relationships = []
    table_names = list(tables.keys())
    if len(table_names) < 2:
        return []
        
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
                    rel = RelationshipConfig(
                        from_table=table_a,
                        from_column=col,
                        to_table=table_b,
                        to_column=col,
                        cardinality="1:N", # Guess default
                        cross_filter_direction="single",
                        is_active=True
                    )
                    # Check if inverse already exists to avoid duplicates
                    if not any((r.from_table == table_b and r.to_table == table_a and r.from_column == col) for r in relationships):
                        relationships.append(rel)
            
            # Heuristic 2: Substring key match
            for col_b in cols_b:
                if col_b.lower() == 'id':
                    singular_b = table_b.lower()
                    if singular_b.endswith('s') and len(singular_b) > 1:
                        singular_b = singular_b[:-1]
                    
                    target_patterns = {f"{singular_b}_id", f"{singular_b}id", f"{singular_b}_key"}
                    for col_a in cols_a:
                        if col_a.lower() in target_patterns:
                            rel = RelationshipConfig(
                                from_table=table_a, # e.g. Sales
                                from_column=col_a,  # e.g. product_id
                                to_table=table_b,   # e.g. Products
                                to_column=col_b,    # e.g. id
                                cardinality="N:1",  # Many sales to one product
                                cross_filter_direction="single",
                                is_active=True
                            )
                            if not any((r.from_table == table_a and r.to_table == table_b and r.from_column == col_a) for r in relationships):
                                relationships.append(rel)
    return relationships

class DataModel:
    def __init__(self, tables: Dict[str, pd.DataFrame], relationships: Optional[List[RelationshipConfig]] = None):
        """
        Manages multiple Pandas DataFrames and their Power BI-style foreign-key relationships.
        """
        self.tables = tables
        
        # If relationships are not provided, run auto-detection heuristics
        if not relationships and len(tables) >= 2:
            self.relationships = auto_detect_relationships(tables)
        else:
            self.relationships = relationships or []

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
        summary_lines.append("## Table Relationships (Star Schema)")
        if not self.relationships:
            summary_lines.append("No relationships defined. If queries span multiple tables, search for matching column names to merge.")
        else:
            summary_lines.append("These tables connect using the following key column mappings:")
            for rel in self.relationships:
                status = "Active" if rel.is_active else "Inactive"
                summary_lines.append(
                    f"- **{rel.from_table}.{rel.from_column}** ↔ **{rel.to_table}.{rel.to_column}** "
                    f"({rel.cardinality}, {rel.cross_filter_direction} direction, {status})"
                )
            summary_lines.append("\n*Note: To query across tables, perform a merge using pd.merge() on these key columns first.*")

        return "\n".join(summary_lines)

    def propagate_filters(self, initial_filters: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        Applies filters and propagates them through the relationship graph.
        Currently returns the filtered tables.
        """
        # A full DAX-like filter propagation is complex. 
        # For now, we apply filters directly to tables if the column exists.
        filtered_tables = {name: df.copy() for name, df in self.tables.items()}
        
        for col_name, val in initial_filters.items():
            for t_name, df in filtered_tables.items():
                if col_name in df.columns:
                    if isinstance(val, list):
                        filtered_tables[t_name] = df[df[col_name].isin(val)]
                    else:
                        filtered_tables[t_name] = df[df[col_name] == val]
                        
        # Basic filter propagation: if Table A is filtered, and 1:N exists from A -> B (single direction), filter B.
        # This requires tracking row counts and applying semi-joins.
        # For simplicity in this implementation, we apply semi-joins iteratively until stabilization.
        changed = True
        while changed:
            changed = False
            for rel in self.relationships:
                if not rel.is_active: continue
                
                # if single direction: filter flows from '1' side to 'N' side. 
                # Let's assume from_table is N and to_table is 1 (N:1) or vice versa.
                # Actually, standard Power BI propagates from 1 to N.
                if rel.cardinality == "N:1" or rel.cardinality == "M:1":
                    source, target = rel.to_table, rel.from_table
                    s_col, t_col = rel.to_column, rel.from_column
                elif rel.cardinality == "1:N" or rel.cardinality == "1:M":
                    source, target = rel.from_table, rel.to_table
                    s_col, t_col = rel.from_column, rel.to_column
                else: # 1:1 or both
                    source, target = rel.from_table, rel.to_table
                    s_col, t_col = rel.from_column, rel.to_column
                    
                # Propagate from source to target
                if source in filtered_tables and target in filtered_tables:
                    s_df = filtered_tables[source]
                    t_df = filtered_tables[target]
                    
                    if len(s_df) < len(self.tables[source]): # Source was filtered
                        valid_keys = s_df[s_col].unique()
                        orig_len = len(t_df)
                        filtered_tables[target] = t_df[t_df[t_col].isin(valid_keys)]
                        if len(filtered_tables[target]) < orig_len:
                            changed = True
                            
                # If bidirectional, also propagate back
                if rel.cross_filter_direction == "both":
                    if source in filtered_tables and target in filtered_tables:
                        t_df = filtered_tables[target]
                        s_df = filtered_tables[source]
                        
                        if len(t_df) < len(self.tables[target]): # Target was filtered
                            valid_keys = t_df[t_col].unique()
                            orig_len = len(s_df)
                            filtered_tables[source] = s_df[s_df[s_col].isin(valid_keys)]
                            if len(filtered_tables[source]) < orig_len:
                                changed = True
        
        return filtered_tables
