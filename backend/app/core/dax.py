import pandas as pd
import numpy as np
from typing import Callable, Any, List

def CALCULATE(df: pd.DataFrame, measure: Callable[[pd.DataFrame], Any], *filters: pd.Series) -> Any:
    """
    Evaluates an expression in a context that is modified by the specified filters.
    
    Args:
        df: The DataFrame to filter.
        measure: A lambda function that computes the metric on the filtered DataFrame.
        *filters: Boolean Series (masks) to apply.
        
    Example:
        CALCULATE(df, lambda d: d['Sales'].sum(), d['Region'] == 'North', d['Year'] == 2026)
    """
    temp_df = df.copy()
    for f in filters:
        if isinstance(f, pd.Series) and f.dtype == bool:
            temp_df = temp_df[f]
    return measure(temp_df)

def SUMX(df: pd.DataFrame, expression: Callable[[pd.Series], float]) -> float:
    """
    Returns the sum of an expression evaluated for each row in a table.
    
    Args:
        df: The DataFrame.
        expression: A lambda function operating on a row (pd.Series) to compute a value.
        
    Example:
        SUMX(df, lambda row: row['Quantity'] * row['Unit Price'])
    """
    try:
        # Vectorized apply is faster if expression can be applied across DataFrame
        return df.apply(expression, axis=1).sum()
    except Exception:
        return 0.0

def AVERAGEX(df: pd.DataFrame, expression: Callable[[pd.Series], float]) -> float:
    """
    Returns the average (arithmetic mean) of an expression evaluated for each row in a table.
    """
    try:
        return df.apply(expression, axis=1).mean()
    except Exception:
        return 0.0

def USERELATIONSHIP(df1: pd.DataFrame, df2: pd.DataFrame, col1: str, col2: str, how: str = "inner") -> pd.DataFrame:
    """
    Specifies the relationship to be used in a specific calculation.
    In Pandas context, this explicitly merges two dataframes on the specified columns.
    
    Args:
        df1: First DataFrame.
        df2: Second DataFrame.
        col1: Column from first DataFrame.
        col2: Column from second DataFrame.
        how: Merge type ('inner', 'left', 'right', 'outer').
    """
    return pd.merge(df1, df2, left_on=col1, right_on=col2, how=how)

def DIVIDE(numerator: float, denominator: float, alternate_result: float = 0.0) -> float:
    """
    Performs division and returns alternate result or 0 on division by zero.
    """
    if denominator == 0 or pd.isna(denominator):
        return alternate_result
    return numerator / denominator
