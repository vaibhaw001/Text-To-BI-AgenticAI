import os
from typing import Dict, Any, Tuple
import pandas as pd
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_openai import ChatOpenAI

def execute_direct_query(prompt: str, connection_string: str) -> pd.DataFrame:
    """
    Translates a natural language query into SQL, executes it against the database,
    and returns the result as a Pandas DataFrame.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model_name = os.getenv("LLM_MODEL", "gpt-4o")
    
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.0)
    else:
        llm = ChatOpenAI(model=model_name, temperature=0.0)
        
    engine = create_engine(connection_string)
    db = SQLDatabase(engine)
    
    # Create the SQL chain
    chain = create_sql_query_chain(llm, db)
    
    # Generate SQL
    sql_query = chain.invoke({"question": prompt})
    
    # Langchain sometimes adds markdown block syntax around sql
    sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
    
    # Execute SQL and return DataFrame
    df = pd.read_sql(sql_query, engine)
    
    return df
