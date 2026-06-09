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
