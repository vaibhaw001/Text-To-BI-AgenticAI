import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly
from typing import Dict, Any, Tuple

# Set of allowed top-level modules for import
ALLOWED_MODULES = {'pandas', 'plotly', 'numpy', 'datetime', 'json', 'math'}

def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    base_module = name.split('.')[0]
    if base_module in ALLOWED_MODULES:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"Importing module '{name}' is not allowed in this execution sandbox.")

def calculate_ytd(df: pd.DataFrame, date_col: str, val_col: str) -> pd.Series:
    """Calculates chronological cumulative sum resetting at the start of each calendar year."""
    try:
        temp = df.copy()
        temp['__dt'] = pd.to_datetime(temp[date_col])
        temp['__yr'] = temp['__dt'].dt.year
        temp = temp.sort_values('__dt')
        return temp.groupby('__yr')[val_col].cumsum()
    except Exception as e:
        raise ValueError(f"Error calculating YTD on date column '{date_col}' and value column '{val_col}': {str(e)}")

def calculate_rolling_average(df: pd.DataFrame, date_col: str, val_col: str, window: int = 7) -> pd.Series:
    """Calculates chronological rolling average for a numeric column."""
    try:
        temp = df.copy()
        temp['__dt'] = pd.to_datetime(temp[date_col])
        temp = temp.sort_values('__dt')
        return temp[val_col].rolling(window=window, min_periods=1).mean()
    except Exception as e:
        raise ValueError(f"Error calculating rolling average: {str(e)}")

def calculate_yoy_growth(df: pd.DataFrame, date_col: str, val_col: str) -> pd.DataFrame:
    """
    Calculates year-over-year growth percentage.
    Returns a DataFrame with columns: [date_col, total_value, yoy_growth_percent].
    """
    try:
        temp = df.copy()
        temp['__dt'] = pd.to_datetime(temp[date_col])
        temp['__yr'] = temp['__dt'].dt.year
        temp['__mo'] = temp['__dt'].dt.month
        agg = temp.groupby(['__yr', '__mo']).agg({val_col: 'sum', date_col: 'first'}).reset_index()
        agg = agg.sort_values(['__yr', '__mo'])
        agg['val_prev_year'] = agg.groupby('__mo')[val_col].shift(1)
        agg['yoy_growth_percent'] = ((agg[val_col] - agg['val_prev_year']) / agg['val_prev_year']) * 100.0
        return agg[[date_col, val_col, 'yoy_growth_percent']].rename(columns={val_col: f'total_{val_col}'})
    except Exception as e:
        raise ValueError(f"Error calculating YoY growth: {str(e)}")

def execute_chart_code(code_str: str, tables: Dict[str, pd.DataFrame]) -> Tuple[go.Figure, str]:
    """
    Executes Python Plotly code against the provided dictionary of tables (DataFrames)
    in a restricted sandbox environment.
    
    Args:
        code_str (str): Python code containing Plotly visualization logic.
        tables (Dict[str, pd.DataFrame]): Dictionary mapping variable names to DataFrames.
        
    Returns:
        Tuple[go.Figure, str]: The generated Plotly Figure object and the cleaned code executed.
    
    Raises:
        Exception: Any error during execution or validation.
    """
    safe_builtins = {
        'print': print,
        'range': range,
        'len': len,
        'int': int,
        'float': float,
        'str': str,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'abs': abs,
        'sum': sum,
        'min': min,
        'max': max,
        'round': round,
        'enumerate': enumerate,
        'zip': zip,
        'any': any,
        'all': all,
        'sorted': sorted,
        'filter': filter,
        'map': map,
        'bool': bool,
        'isinstance': isinstance,
        '__import__': safe_import,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'KeyError': KeyError,
        'IndexError': IndexError,
        'AttributeError': AttributeError,
    }

    # Set up global environment
    global_env = {
        '__builtins__': safe_builtins,
        'pd': pd,
        'px': px,
        'go': go,
        'plotly': plotly,
        'calculate_ytd': calculate_ytd,
        'calculate_rolling_average': calculate_rolling_average,
        'calculate_yoy_growth': calculate_yoy_growth,
    }
    
    # Set up local environment, injecting all tables as variables in local scope
    local_env = {
        'fig': None,
        **tables
    }
    
    # Run the code
    exec(code_str, global_env, local_env)
    
    # Retrieve and validate result
    fig = local_env.get('fig')
    if fig is None:
        raise ValueError("Code executed successfully but failed to define a 'fig' variable.")
        
    if not isinstance(fig, (go.Figure, plotly.graph_objs.Figure)):
        raise TypeError(f"The 'fig' variable must be a Plotly Figure, found '{type(fig).__name__}'.")
        
    return fig, code_str
