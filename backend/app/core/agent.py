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
Your goal is to write clean, valid, executable Python Plotly code to answer analytical queries about a relational database schema.

You must design visualizations using the Grammar of Graphics approach (like Tableau/ggplot2), ensuring:
1. Modern design: Use premium, tailored colors and clean layouts. Avoid raw default primary colors. Prefer cohesive color schemes, sleek gradients, or professional HSL colors.
2. Structure: Ensure proper title, axis labels with units, and visible legend (if mapping multiple series).
3. Aesthetics: Use clean layouts (e.g. template='plotly_dark' or 'plotly_white', hide outer borders, customize gridlines to be light and subtle).
4. Grammar of Graphics mapping: Match data dimensions (categorical, temporal) and measures (numerical values) to appropriate visual channels (X, Y, color, size, line style).

Execution Environment Rules:
- The DataFrames are loaded in your execution context as variables named matching their table names (e.g., `Sales`, `Products`, or `df` if a single-table dataset).
- Do NOT try to read or load the dataset. Do NOT use pd.read_csv() or define mock data.
- MULTI-TABLE MERGES (Power BI style): If the query requires columns from multiple tables, you MUST merge them first. Write valid pandas `pd.merge()` statements using the defined foreign-key relationships before generating the Plotly chart.
- The output code MUST define the final Plotly Figure and assign it to a variable named `fig`.
- Return ONLY the raw python code inside a ```python ``` markdown block. No explanations, no markdown comments outside the code block, no print statements.
- Do NOT use fig.show() or fig.write_html().
- Restrict imports to: pandas (as pd), plotly.express (as px), plotly.graph_objects (as go), numpy (as np), json, math, datetime.
"""

def generate_chart_with_retry(
    prompt: str,
    schema_summary: str,
    data_model: DataModel,
    max_retries: int = 3
) -> Tuple[Any, List[Dict[str, Any]], str]:
    """
    Generates a chart using LLM-generated Plotly code, running it inside the executor sandbox.
    Implements a self-correction loop if execution fails.
    
    Returns:
        Tuple[go.Figure, List[dict], str]: The final Plotly Figure, history of attempts, and the final corrected code.
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

Generate the Python Plotly code to answer this query. Merge tables if columns span multiple tables. Remember to assign the figure to the variable `fig`."""

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
            
            history[-1]["status"] = "success"
            return fig, history, executed_code
            
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
4. Define the final chart and assign it to the variable `fig`."""
            
            messages.append(HumanMessage(content=correction_message))
            
    raise RuntimeError("Unreachable state in chart generation retry loop.")
