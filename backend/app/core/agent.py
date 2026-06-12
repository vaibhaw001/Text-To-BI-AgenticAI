import os
import re
import traceback
import pandas as pd
from typing import Dict, Any, Tuple, List
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from app.sandbox.executor import execute_chart_code
from app.core.data import DataModel

load_dotenv()

# Extract code block from text
def extract_python_code(text: Any) -> str:
    if not isinstance(text, str):
        if isinstance(text, list):
            parts = []
            for part in text:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and 'text' in part:
                    parts.append(part['text'])
            text = "\n".join(parts)
        else:
            text = str(text) if text is not None else ""

    match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()

# System prompt for visual design rules (Grammar of Graphics & Tableau visuals) and Relational Modeling
SYSTEM_PROMPT = """You are a senior data scientist and visualization expert.
Your goal is to answer analytical queries about a relational database schema by preparing the data and mapping it to Tableau's Visual Grammar (Shelves).

You must NOT write raw Plotly graphing code. Instead, you must:
1. Write Python code to merge and prepare the data, assigning the final result to `df_chart`.
2. Define a dictionary named `chart_config` mapping the schema to visual shelves.

The `chart_config` dictionary MUST have the following structure:
{
    "mark": "bar" | "line" | "scatter" | "pie" | "area",
    "columns": ["X_Axis_Column"],  # X-axis / dimensions
    "rows": ["Y_Axis_Column"],     # Y-axis / measures
    "secondary_rows": ["Y2_Axis_Column"], # Optional: for dual-axis combo charts
    "secondary_mark": "line",             # Optional: mark type for the secondary axis
    "color": "Color_Column_or_None",
    "size": "Size_Column_or_None",
    "detail": "Detail_Column_or_None",
    "label": "Label_Column_or_None",
    "title": "Chart Title"
}

Execution Environment Rules:
- The DataFrames are loaded in your execution context as variables named matching their table names (e.g., `Sales`, `Products`, or `df` if a single-table dataset).
- Do NOT try to read or load the dataset. Do NOT use pd.read_csv() or define mock data.
- MULTI-TABLE MERGES (Power BI style): If the query requires columns from multiple tables, you MUST merge them first. Write valid pandas `pd.merge()` statements using the defined foreign-key relationships.
- The output code MUST define the final prepared dataframe as `df_chart` and the shelf assignments as `chart_config`.
- Return ONLY the raw python code inside a ```python ``` markdown block. No explanations, no markdown comments outside the code block, no print statements.
- Restrict imports to: pandas (as pd), numpy (as np), json, math, datetime, statsmodels, scipy, sklearn.

Time Intelligence & Forecasting Helpers (Already imported in execution environment, use directly if needed):
- `calculate_ytd(df, date_col, val_col)`: Returns a Pandas Series of chronological YTD cumulative sum values resetting at start of each calendar year.
- `calculate_rolling_average(df, date_col, val_col, window=7)`: Returns a Pandas Series of chronological rolling average values.
- `calculate_yoy_growth(df, date_col, val_col)`: Returns a DataFrame with columns: `[date_col, f'total_{val_col}', 'yoy_growth_percent']` containing monthly year-over-year growth percentage.
- `calculate_forecast(df, date_col, val_col, periods=30, confidence_level=0.95)`: Generates a future forecast using Holt-Winters Exponential Smoothing. Returns a DataFrame with columns: `[date_col, val_col, 'forecast', 'lower_ci', 'upper_ci']` where the forecasted dates contain actuals in `forecast` and confidence intervals in `lower_ci` / `upper_ci`.
- `calculate_trend_line(df, x_col, y_col, confidence_level=0.95)`: Performs linear OLS regression on x_col and y_col. Returns a DataFrame with columns: `[x_col, y_col, 'trend', 'lower_ci', 'upper_ci']`.
- `detect_anomalies(df, val_col, method='z_score', z_threshold=2.0, contamination=0.05)`: Identifies statistical outliers in a numeric column. Returns the input DataFrame with two new columns: `['is_anomaly' (bool), 'anomaly_description' (str)]` explaining the outlier spike/dip and the percentage deviation from average.
"""

def extract_chart_data_summary(fig: Any) -> str:
    """Extracts a concise, text-based summary of the data coordinates plotted inside the Figure."""
    summary_lines = []
    
    if not hasattr(fig, 'data') or not fig.data:
        return "No plotted data found in figure."
        
    for i, trace in enumerate(fig.data):
        trace_type = getattr(trace, 'type', 'unknown')
        trace_name = getattr(trace, 'name', f"trace_{i}")
        summary_lines.append(f"Trace {i} ('{trace_name}'): type={trace_type}")
        
        # Extract X and Y (common for bar, line, scatter)
        x_vals = getattr(trace, 'x', None)
        y_vals = getattr(trace, 'y', None)
        if x_vals is not None and y_vals is not None:
            try:
                x_list = list(x_vals)
                y_list = list(y_vals)
                summary_lines.append(f"  Plotted X-values: {x_list[:10]}")
                summary_lines.append(f"  Plotted Y-values: {y_list[:10]}")
            except Exception:
                pass
                
        # Extract labels and values (common for pie charts)
        labels = getattr(trace, 'labels', None)
        values = getattr(trace, 'values', None)
        if labels is not None and values is not None:
            try:
                l_list = list(labels)
                v_list = list(values)
                summary_lines.append(f"  Plotted Labels: {l_list[:10]}")
                summary_lines.append(f"  Plotted Values: {v_list[:10]}")
            except Exception:
                pass
                
    return "\n".join(summary_lines)

def generate_data_insights(prompt: str, chart_data_summary: str, llm: Any) -> str:
    """Generates a concise 2-3 sentence analytical summary of the chart findings using the LLM."""
    insights_prompt = f"""You are an expert business intelligence analyst.
Analyze the following chart data summary and write a concise, high-level analytical insight (2-3 sentences max) that explains the core findings or key trends shown in this visualization.

User query context:
"{prompt}"

Plotted Chart Data Summary:
{chart_data_summary}

Provide ONLY the descriptive text insight. Do not include introductory phrases like "Here is the summary" or markdown formatting. Keep it highly professional, factual, and numeric."""
    
    try:
        messages = [
            SystemMessage(content="You are a senior BI analyst who provides concise, accurate data insights."),
            HumanMessage(content=insights_prompt)
        ]
        response = llm.invoke(messages)
        return extract_python_code(response.content)
    except Exception as e:
        return f"Unable to generate AI data insights: {str(e)}"

def generate_chart_with_retry(
    prompt: str,
    schema_summary: str,
    data_model: DataModel,
    max_retries: int = 3
) -> Tuple[Any, List[Dict[str, Any]], str, str]:
    """
    Generates a chart using LLM-generated Plotly code, running it inside the executor sandbox.
    Implements a self-correction loop if execution fails.
    Also calls the LLM to generate descriptive insights based on the aggregated chart values.
    
    Returns:
        Tuple[go.Figure, List[dict], str, str]: The Plotly Figure, execution history, final code, and AI insights.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model_name = os.getenv("LLM_MODEL", "gpt-4o")
    
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY is not set. Please check your .env configuration.")
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.0,
            google_api_key=google_api_key
        )
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please check your .env configuration.")
        llm = ChatOpenAI(
            model=model_name,
            temperature=0.0,
            openai_api_key=openai_api_key
        )
    
    initial_user_prompt = f"""Relational Data Model Schema:
{schema_summary}

User Query:
"{prompt}"

Generate the Python code to prepare the data and define the Visual Grammar mapping. Merge tables if columns span multiple tables. Remember to assign the final dataframe to `df_chart` and the visual grammar dictionary to `chart_config`."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=initial_user_prompt)
    ]
    
    history = []
    attempt = 0
    
    while attempt <= max_retries:
        try:
            # 1. Call LLM (API call)
            response = llm.invoke(messages)
            raw_content = response.content
            code = extract_python_code(raw_content)
        except Exception as e:
            # API or connection error: abort immediately to prevent infinite code-fixing retries
            tb = traceback.format_exc()
            error_msg = f"LLM API Error: {type(e).__name__}: {str(e)}"
            history.append({
                "attempt": attempt + 1,
                "raw_response": "",
                "extracted_code": "",
                "status": "failed",
                "error": {
                    "message": error_msg,
                    "traceback": tb
                }
            })
            raise RuntimeError(f"Failed to query the LLM: {error_msg}") from e

        try:
            # 2. Execute Code
            history.append({
                "attempt": attempt + 1,
                "raw_response": raw_content,
                "extracted_code": code,
                "status": "pending",
                "error": None
            })
            
            # Execute the generated code passing the data_model's tables dict
            fig, executed_code = execute_chart_code(code, data_model.tables)
            
            # 3. Generate Analytical Insights from the plotted data
            chart_data_summary = extract_chart_data_summary(fig)
            insights = generate_data_insights(prompt, chart_data_summary, llm)
            
            history[-1]["status"] = "success"
            return fig, history, executed_code, insights
            
        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            history[-1]["status"] = "failed"
            history[-1]["error"] = {
                "message": error_msg,
                "traceback": tb
            }
            
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(
                    f"Failed to generate valid Plotly code after {max_retries + 1} attempts.\n"
                    f"Last error: {error_msg}\n"
                    f"Code attempted:\n{code}"
                ) from e
            
            messages.append(AIMessage(content=raw_content))
            correction_message = f"""The code execution failed with the following error:
{error_msg}

Please fix the error and write the complete corrected code. Make sure that:
1. You merge tables using pd.merge(TableA, TableB, left_on='...', right_on='...') if you need to use columns from different tables.
2. The DataFrame variables are already available in your environment (e.g. if tables are `Sales` and `Products`, they are available as `Sales` and `Products` variables). Do not reload them.
3. Check table and column spelling carefully against the schema.
4. Define the final prepared dataframe as `df_chart` and the shelf assignments as `chart_config`."""
            
            messages.append(HumanMessage(content=correction_message))
            
    raise RuntimeError("Unreachable state in chart generation retry loop.")
