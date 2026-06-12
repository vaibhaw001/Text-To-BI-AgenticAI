import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly
from typing import Dict, Any, Tuple

# Set of allowed top-level modules for import
ALLOWED_MODULES = {'pandas', 'plotly', 'numpy', 'datetime', 'json', 'math', 'statsmodels', 'scipy', 'sklearn'}


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

def calculate_forecast(
    df: pd.DataFrame, 
    date_col: str, 
    val_col: str, 
    periods: int = 30, 
    confidence_level: float = 0.95
) -> pd.DataFrame:
    """
    Computes time-series forecast using Holt-Winters Exponential Smoothing.
    Returns a DataFrame with columns: [date_col, val_col, 'forecast', 'lower_ci', 'upper_ci'].
    """
    import numpy as np
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from scipy.stats import norm
    import logging
    
    logger = logging.getLogger("text-to-bi-backend.forecast")
    
    try:
        temp = df.copy()
        temp[date_col] = pd.to_datetime(temp[date_col])
        daily_series = temp.groupby(date_col)[val_col].sum().sort_index()
        
        freq = pd.infer_freq(daily_series.index)
        if not freq:
            freq = 'D'
        daily_series = daily_series.asfreq(freq, fill_value=0.0)
        
        n_obs = len(daily_series)
        seasonal_periods = 7 if freq == 'D' else (12 if freq in ['M', 'MS'] else 4)
        
        trend_type = 'add' if n_obs >= 4 else None
        seasonal_type = 'add' if n_obs >= (seasonal_periods * 2) else None
        
        model = ExponentialSmoothing(
            daily_series,
            trend=trend_type,
            seasonal=seasonal_type,
            seasonal_periods=seasonal_periods if seasonal_type else None
        )
        fit = model.fit()
        
        forecast_series = fit.forecast(periods)
        
        residuals = fit.resid
        se_residual = np.std(residuals) if len(residuals) > 0 else 0.0
        
        alpha = 1.0 - confidence_level
        z_val = norm.ppf(1.0 - alpha / 2.0)
        
        forecast_dates = forecast_series.index
        forecast_vals = forecast_series.values
        
        lower_bounds = []
        upper_bounds = []
        for h in range(1, periods + 1):
            se_h = se_residual * np.sqrt(h)
            lower_bounds.append(forecast_vals[h - 1] - z_val * se_h)
            upper_bounds.append(forecast_vals[h - 1] + z_val * se_h)
            
        hist_df = pd.DataFrame({
            date_col: daily_series.index,
            val_col: daily_series.values,
            'forecast': np.nan,
            'lower_ci': np.nan,
            'upper_ci': np.nan
        })
        
        fore_df = pd.DataFrame({
            date_col: forecast_dates,
            val_col: np.nan,
            'forecast': forecast_vals,
            'lower_ci': lower_bounds,
            'upper_ci': upper_bounds
        })
        
        result = pd.concat([hist_df, fore_df], ignore_index=True)
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            result[date_col] = result[date_col].dt.strftime('%Y-%m-%d')
            
        return result
        
    except Exception as e:
        logger.error(f"Forecasting error: {str(e)}")
        try:
            temp = df.copy()
            temp[date_col] = pd.to_datetime(temp[date_col])
            daily_series = temp.groupby(date_col)[val_col].sum().sort_index()
            x_vals = np.arange(len(daily_series))
            y_vals = daily_series.values
            slope, intercept = np.polyfit(x_vals, y_vals, 1)
            
            future_x = np.arange(len(daily_series), len(daily_series) + periods)
            future_y = slope * future_x + intercept
            
            se_residual = np.std(y_vals - (slope * x_vals + intercept)) if len(y_vals) > 1 else 1.0
            z_val = 1.96
            
            lower_bounds = [future_y[i] - z_val * se_residual * np.sqrt(i + 1) for i in range(periods)]
            upper_bounds = [future_y[i] + z_val * se_residual * np.sqrt(i + 1) for i in range(periods)]
            
            freq = pd.infer_freq(daily_series.index) or 'D'
            # Fixed date offset logic
            last_date = daily_series.index[-1]
            future_dates = pd.date_range(start=last_date + pd.tseries.frequencies.to_offset(freq), periods=periods, freq=freq)
            
            hist_df = pd.DataFrame({
                date_col: daily_series.index,
                val_col: y_vals,
                'forecast': np.nan,
                'lower_ci': np.nan,
                'upper_ci': np.nan
            })
            fore_df = pd.DataFrame({
                date_col: future_dates,
                val_col: np.nan,
                'forecast': future_y,
                'lower_ci': lower_bounds,
                'upper_ci': upper_bounds
            })
            result = pd.concat([hist_df, fore_df], ignore_index=True)
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                result[date_col] = result[date_col].dt.strftime('%Y-%m-%d')
            return result
        except Exception as fallback_err:
            raise ValueError(f"Forecasting failed and fallback also failed: {str(fallback_err)}")

def calculate_trend_line(
    df: pd.DataFrame, 
    x_col: str, 
    y_col: str, 
    confidence_level: float = 0.95
) -> pd.DataFrame:
    """
    Computes linear regression trend line and confidence bands.
    Returns a DataFrame with columns: [x_col, y_col, 'trend', 'lower_ci', 'upper_ci'].
    """
    import statsmodels.api as sm
    import numpy as np
    import logging
    
    logger = logging.getLogger("text-to-bi-backend.trend")
    
    try:
        temp = df.copy()
        
        is_date = False
        if pd.api.types.is_datetime64_any_dtype(temp[x_col]) or temp[x_col].dtype == 'object':
            try:
                temp['__x_dt'] = pd.to_datetime(temp[x_col])
                temp['__x_num'] = temp['__x_dt'].apply(lambda x: x.toordinal())
                x_vals = temp['__x_num'].values
                is_date = True
            except Exception:
                x_vals = np.arange(len(temp))
        else:
            x_vals = temp[x_col].values
            
        y_vals = temp[y_col].values
        
        X = sm.add_constant(x_vals)
        model = sm.OLS(y_vals, X)
        results = model.fit()
        
        predictions = results.get_prediction(X)
        summary_frame = predictions.summary_frame(alpha=1.0 - confidence_level)
        
        temp['trend'] = summary_frame['mean'].values
        temp['lower_ci'] = summary_frame['mean_ci_lower'].values
        temp['upper_ci'] = summary_frame['mean_ci_upper'].values
        
        cols = [x_col, y_col, 'trend', 'lower_ci', 'upper_ci']
        return temp[cols]
        
    except Exception as e:
        logger.error(f"Trend line error: {str(e)}")
        try:
            temp = df.copy()
            x_raw = np.arange(len(temp))
            y_vals = temp[y_col].values
            slope, intercept = np.polyfit(x_raw, y_vals, 1)
            y_pred = slope * x_raw + intercept
            
            residuals = y_vals - y_pred
            std_err = np.std(residuals) if len(residuals) > 0 else 1.0
            
            temp['trend'] = y_pred
            temp['lower_ci'] = y_pred - 1.96 * std_err
            temp['upper_ci'] = y_pred + 1.96 * std_err
            
            cols = [x_col, y_col, 'trend', 'lower_ci', 'upper_ci']
            return temp[cols]
        except Exception as fallback_err:
            raise ValueError(f"Trend line failed: {str(fallback_err)}")

def detect_anomalies(
    df: pd.DataFrame,
    val_col: str,
    method: str = 'z_score',
    z_threshold: float = 2.0,
    contamination: float = 0.05
) -> pd.DataFrame:
    """
    Identifies anomalies in a DataFrame for a numeric column.
    Returns the input DataFrame with two new columns:
      - 'is_anomaly': boolean Series (True for outliers, False otherwise)
      - 'anomaly_description': string Series explaining the anomaly (spike or dip, deviation info)
    """
    import numpy as np
    import logging
    
    logger = logging.getLogger("text-to-bi-backend.anomalies")
    
    try:
        temp = df.copy()
        if len(temp) == 0:
            temp['is_anomaly'] = pd.Series(dtype=bool)
            temp['anomaly_description'] = pd.Series(dtype=str)
            return temp
            
        y_vals = pd.to_numeric(temp[val_col], errors='coerce').fillna(0.0).values
        
        is_anomaly = np.zeros(len(temp), dtype=bool)
        descriptions = [""] * len(temp)
        
        # Calculate base statistics for description
        mean_val = np.mean(y_vals)
        std_val = np.std(y_vals)
        
        if method == 'z_score':
            if std_val > 0:
                z_scores = (y_vals - mean_val) / std_val
                is_anomaly = np.abs(z_scores) > z_threshold
            else:
                is_anomaly = np.zeros(len(temp), dtype=bool)
        elif method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            X = y_vals.reshape(-1, 1)
            clf = IsolationForest(contamination=contamination, random_state=42)
            preds = clf.fit_predict(X)
            is_anomaly = preds == -1
        else:
            raise ValueError(f"Unknown anomaly detection method: '{method}'. Supported: 'z_score', 'isolation_forest'")
            
        # Build descriptions
        for i in range(len(temp)):
            if is_anomaly[i]:
                val = y_vals[i]
                diff_mean = val - mean_val
                direction = "Spike" if diff_mean >= 0 else "Dip"
                pct_dev = (diff_mean / mean_val * 100.0) if mean_val != 0 else 0.0
                z_info = f", Z-score: {diff_mean/std_val:.2f}" if std_val > 0 else ""
                descriptions[i] = f"Outlier ({direction}): {val:.2f} ({pct_dev:+.1f}% from avg{z_info})"
            else:
                descriptions[i] = "Normal"
                
        temp['is_anomaly'] = is_anomaly
        temp['anomaly_description'] = descriptions
        return temp
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {str(e)}")
        try:
            temp = df.copy()
            y_vals = pd.to_numeric(temp[val_col], errors='coerce').fillna(0.0).values
            mean_val = np.mean(y_vals)
            std_val = np.std(y_vals) if np.std(y_vals) > 0 else 1.0
            
            is_anomaly = np.abs(y_vals - mean_val) > (z_threshold * std_val)
            descriptions = []
            for i, val in enumerate(y_vals):
                if is_anomaly[i]:
                    dir_str = "Spike" if val >= mean_val else "Dip"
                    descriptions.append(f"Outlier ({dir_str}): {val:.2f}")
                else:
                    descriptions.append("Normal")
            temp['is_anomaly'] = is_anomaly
            temp['anomaly_description'] = descriptions
            return temp
        except Exception as fallback_err:
            raise ValueError(f"Anomaly detection failed: {str(fallback_err)}")

def build_figure_from_grammar(df: pd.DataFrame, chart_config: Dict[str, Any]) -> go.Figure:
    """
    Builds a Plotly figure based on Tableau Visual Grammar shelves.
    """
    mark = chart_config.get("mark", "bar").lower()
    columns = chart_config.get("columns", [])
    rows = chart_config.get("rows", [])
    color = chart_config.get("color")
    size = chart_config.get("size")
    detail = chart_config.get("detail")  # For grouping without color
    label = chart_config.get("label")
    title = chart_config.get("title", "")

    x_col = columns[0] if columns else None
    y_col = rows[0] if rows else None
    
    kwargs = {}
    if color and color in df.columns:
        kwargs["color"] = color
    if size and size in df.columns and mark in ['scatter']:
        kwargs["size"] = size
    if label and label in df.columns:
        kwargs["text"] = label
        
    if detail and detail in df.columns and mark in ['line', 'scatter']:
        if 'color' not in kwargs: # Detail is usually for separation when color isn't used
            kwargs['color'] = detail
        elif kwargs.get('color') != detail:
            kwargs['symbol'] = detail # Fallback mapping detail to symbol for scatter

    try:
        if mark == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title, **kwargs)
        elif mark == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, **kwargs)
        elif mark == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=title, **kwargs)
        elif mark == "pie":
            names = x_col or color
            values = y_col
            fig = px.pie(df, names=names, values=values, title=title, **kwargs)
        elif mark == "area":
            fig = px.area(df, x=x_col, y=y_col, title=title, **kwargs)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=title, **kwargs)
            
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=60, b=40),
            title_x=0.5,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)', zerolinecolor='rgba(0,0,0,0.2)')
        
        return fig
    except Exception as e:
        raise ValueError(f"Error building figure from grammar: {str(e)}")

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
        'calculate_forecast': calculate_forecast,
        'calculate_trend_line': calculate_trend_line,
        'detect_anomalies': detect_anomalies,
    }
    
    # Set up local environment, injecting all tables as variables in local scope
    local_env = {
        'df_chart': None,
        'chart_config': None,
        'fig': None,
        **tables
    }
    
    # Run the code
    exec(code_str, global_env, local_env)
    
    # Retrieve and validate result
    df_chart = local_env.get('df_chart')
    chart_config = local_env.get('chart_config')
    fig = local_env.get('fig')
    
    # If LLM still assigned fig directly, we can optionally support it,
    # but primarily we want df_chart and chart_config.
    if df_chart is not None and chart_config is not None:
        fig = build_figure_from_grammar(df_chart, chart_config)
    elif fig is None:
        raise ValueError("Code executed successfully but failed to define 'df_chart' and 'chart_config', or 'fig'.")
        
    if not isinstance(fig, (go.Figure, plotly.graph_objs.Figure)):
        raise TypeError(f"The constructed figure must be a Plotly Figure, found '{type(fig).__name__}'.")
        
    return fig, code_str
