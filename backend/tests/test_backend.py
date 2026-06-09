import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import plotly.graph_objects as go
from fastapi.testclient import TestClient

# Add parent directory to path to find app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.data import read_dataset, DataModel
from app.sandbox.executor import execute_chart_code
from app.main import app

class TestBackendComponents(unittest.TestCase):
    
    def setUp(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), "sample_sales.csv")
        self.df = pd.read_csv(self.csv_path)

    def test_read_dataset(self):
        df = read_dataset(self.csv_path)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 10)
        self.assertIn("Sales", df.columns)

    def test_data_model_schema_summary(self):
        # Create a DataModel with two mock tables
        sales_df = pd.DataFrame({
            "product_id": [1, 2],
            "sales_amount": [100.0, 200.0]
        })
        products_df = pd.DataFrame({
            "id": [1, 2],
            "product_name": ["A", "B"]
        })
        
        relationships = {"Sales": ["product_id"], "Products": ["id"]}
        dm = DataModel(tables={"Sales": sales_df, "Products": products_df}, relationships=relationships)
        
        summary = dm.get_schema_summary()
        self.assertIn("## Table: Sales", summary)
        self.assertIn("## Table: Products", summary)
        self.assertIn("product_id", summary)
        self.assertIn("sales_amount", summary)
        self.assertIn("product_name", summary)
        self.assertIn("Table Relationships", summary)
        self.assertIn("Table `Sales` joins using columns: `['product_id']`", summary)

    def test_auto_detect_relationships(self):
        sales_df = pd.DataFrame({
            "product_id": [1, 2],
            "sales_amount": [100.0, 200.0]
        })
        products_df = pd.DataFrame({
            "id": [1, 2],
            "product_name": ["A", "B"]
        })
        
        # When relationships are empty/None, they should be auto-detected
        dm = DataModel(tables={"Sales": sales_df, "Products": products_df}, relationships=None)
        
        self.assertIn("Sales", dm.relationships)
        self.assertIn("Products", dm.relationships)
        self.assertEqual(dm.relationships["Sales"], ["product_id"])
        self.assertEqual(dm.relationships["Products"], ["id"])

    def test_execute_chart_code_success(self):
        code = """
import plotly.express as px
fig = px.bar(df, x='Product', y='Sales', title='Sales by Product')
"""
        fig, executed = execute_chart_code(code, {"df": self.df})
        self.assertIsNotNone(fig)
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(fig.layout.title.text, "Sales by Product")

    def test_execute_chart_code_multi_table(self):
        # Set up two tables in environment
        sales_df = pd.DataFrame({
            "product_id": [101, 102, 101],
            "Sales": [1200.0, 150.0, 600.0]
        })
        products_df = pd.DataFrame({
            "id": [101, 102],
            "Category": ["Electronics", "Appliances"]
        })
        
        code = """
import pandas as pd
import plotly.express as px
merged = pd.merge(Sales, Products, left_on='product_id', right_on='id')
fig = px.bar(merged, x='Category', y='Sales')
"""
        fig, executed = execute_chart_code(code, {"Sales": sales_df, "Products": products_df})
        self.assertIsNotNone(fig)
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 1) # Has one data series

    def test_execute_chart_code_no_fig(self):
        code = """
x = 10
"""
        with self.assertRaises(ValueError) as context:
            execute_chart_code(code, {"df": self.df})
        self.assertIn("failed to define a 'fig' variable", str(context.exception))

    def test_execute_chart_code_invalid_import(self):
        code = """
import os
"""
        with self.assertRaises(ImportError) as context:
            execute_chart_code(code, {"df": self.df})
        self.assertIn("Importing module 'os' is not allowed", str(context.exception))

    @patch('app.core.agent.ChatOpenAI')
    def test_api_endpoint_success(self, mock_chat_openai):
        # Mock LLM response
        mock_llm_instance = MagicMock()
        mock_chat_openai.return_value = mock_llm_instance
        
        mock_response = MagicMock()
        mock_response.content = """
```python
import plotly.express as px
fig = px.bar(df, x='Category', y='Sales')
```
"""
        mock_response_insights = MagicMock()
        mock_response_insights.content = "Plotted bar chart showing Sales distribution by Category."
        
        # side_effect provides response for code gen followed by insights gen
        mock_llm_instance.invoke.side_effect = [mock_response, mock_response_insights]

        # Use FastAPI TestClient
        client = TestClient(app)
        
        # We need to temporarily set an API key so check in agent doesn't throw
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "LLM_PROVIDER": "openai"}):
            response = client.post(
                "/api/generate-chart",
                json={
                    "prompt": "Show me sales by category",
                    "file_path": self.csv_path
                }
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIsNotNone(data["chart_json"])
            self.assertIn("data", data["chart_json"])
            self.assertIn("Category", data["code"])

    @patch('app.core.agent.ChatOpenAI')
    def test_api_endpoint_self_correction_loop(self, mock_chat_openai):
        # Mock LLM responses: First response generates error code, second response fixes it
        mock_llm_instance = MagicMock()
        mock_chat_openai.return_value = mock_llm_instance
        
        mock_response_1 = MagicMock()
        mock_response_1.content = """
```python
# Bad column name 'Revenue' instead of 'Sales'
import plotly.express as px
fig = px.bar(df, x='Category', y='Revenue')
```
"""
        mock_response_2 = MagicMock()
        mock_response_2.content = """
```python
import plotly.express as px
fig = px.bar(df, x='Category', y='Sales')
```
"""
        mock_response_insights = MagicMock()
        mock_response_insights.content = "Corrected visualization of Category vs Sales."
        
        # Return bad response first, then good response, then insights
        mock_llm_instance.invoke.side_effect = [mock_response_1, mock_response_2, mock_response_insights]

        client = TestClient(app)
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "LLM_PROVIDER": "openai"}):
            response = client.post(
                "/api/generate-chart",
                json={
                    "prompt": "Show me sales by category",
                    "file_path": self.csv_path
                }
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertEqual(len(data["history"]), 2)
            self.assertEqual(data["history"][0]["status"], "failed")
            self.assertIn("ValueError", data["history"][0]["error"]["message"])
            self.assertEqual(data["history"][1]["status"], "success")

    @patch('app.core.agent.ChatOpenAI')
    def test_api_endpoint_with_filters(self, mock_chat_openai):
        mock_llm_instance = MagicMock()
        mock_chat_openai.return_value = mock_llm_instance
        
        mock_response = MagicMock()
        mock_response.content = """
```python
import plotly.express as px
fig = px.bar(df, x='Category', y='Sales')
```
"""
        mock_response_insights = MagicMock()
        mock_response_insights.content = "Plotted bar chart for Category vs Sales under filters."
        mock_llm_instance.invoke.side_effect = [mock_response, mock_response_insights]

        client = TestClient(app)
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key", "LLM_PROVIDER": "openai"}):
            response = client.post(
                "/api/generate-chart",
                json={
                    "prompt": "Show me sales by category",
                    "file_path": self.csv_path,
                    "filters": {"Region": "North"}
                }
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIsNotNone(data["chart_json"])

    def test_api_upload_file(self):
        client = TestClient(app)
        import io
        csv_data = b"Category,Sales\nElectronics,100\nAppliances,200\n"
        file = io.BytesIO(csv_data)
        
        response = client.post(
            "/api/upload",
            files={"file": ("test_upload_file.csv", file, "text/csv")}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["file_name"], "test_upload_file.csv")
        self.assertTrue(os.path.exists(data["file_path"]))
        
        # Clean up the uploaded file
        if os.path.exists(data["file_path"]):
            os.remove(data["file_path"])

if __name__ == "__main__":
    unittest.main()
