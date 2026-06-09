# Agentic Text-to-BI Application 📊✨

An advanced, agentic, natural language Business Intelligence (BI) platform designed to mimic **Power BI's relational data modeling** and **Tableau's visual grammar** using an LLM agent workflow.

This application allows users to query single or multiple datasets using plain English, automatically resolves relationships (joins), generates interactive Plotly visualizations, and renders them inside a responsive, drag-and-drop dashboard canvas alongside AI-generated analytical insights.

---

## 🚀 Key Features

### 1. Interactive Filters (Power BI Slicers & Tableau Cross-Filtering)
- **Tableau-Style Cross-Filtering**: Click on any segment, bar, or point in *any* chart on the dashboard. The application captures the click, extracts the column name/value, and automatically slices all other charts on the dashboard to match.
- **Power BI-Style Slicer Panel**: Active filters are listed in an interactive header banner. Users can review active filters and clear them one-by-one or reset all filters.
- **Backend-Driven Query Slicing**: To prevent raw data transfer, the frontend sends the active filter dict to the backend. The backend slices the dataframes using Pandas (`df = df[df[col] == val]`) *before* executing Plotly generation. This dynamically recalculates averages, counts, and sums correctly.

### 2. Natural Language Data Insights (AI Summaries)
- **Data Trace Extraction**: The backend extracts the plotted coordinates (aggregated X/Y coordinates or pie slices) directly from the Plotly figure traces (not the raw database, keeping transaction data secure).
- **Secondary LLM Summarization**: Passes the plotted data to the LLM to generate a concise 2-3 sentence analytical summary.
- **Inspectable BI Cards**: The frontend dashboard widgets feature a tab bar at the bottom allowing users to toggle between:
  - **📊 Chart**: The interactive React-Plotly visualization.
  - **💡 Insights**: The AI-generated descriptive summary of findings.
  - **💻 Code**: The raw Python code that generated the chart.

### 3. Auto-Relationship Detection (Power BI Style)
- **Heuristics Join Engine**: If relationships are left blank, the engine automatically resolves how tables connect:
  - **Exact Key Matching**: Columns with matching names (e.g. `store_id`, `product_id`) across tables are mapped.
  - **Singular ID Substring Matching**: Automatically maps primary keys to foreign keys (e.g. mapping `Products.id` to `Sales.product_id` or `productid`).
- The LLM receives this schema and automatically writes `pd.merge()` code to perform joins.

### 4. Safe Execution Sandbox
- Generated Python code is executed locally in a restricted sandbox context, limiting available builtins, pre-injecting data tables as variables, and strictly restricting imports (allowing only `pandas`, `plotly`, `numpy`, `datetime`, `json`, `math`).

### 5. Self-Correction Loop
- If execution fails, the backend catches the traceback error and feeds it back to the agent. It attempts self-correction up to 3 times before returning a failure.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js (App Router), Tailwind CSS, [React-Plotly.js](https://github.com/plotly/react-plotly.js/), [React-Grid-Layout](https://github.com/react-grid-layout/react-grid-layout)
- **Backend**: Python (FastAPI), Pandas/SQL, [LangChain](https://github.com/langchain-ai/langchain)
- **Agent / LLM**: Google Gemini (`gemini-3.5-flash`) via LangChain Google GenAI
- **Visualization Engine**: Plotly (Python generates the Plotly JSON schema, Next.js renders it client-side)

---

## 🚀 Getting Started

### 1. Prerequisite: Add API Key
Create a `.env` file inside the `backend/` directory (you can copy `backend/.env.example` as a template):
```env
GOOGLE_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=google
LLM_MODEL=gemini-3.5-flash
```

### 2. Run the Backend API
Navigate to the `backend/` directory, set up a virtual environment, install dependencies, and start the FastAPI server:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The FastAPI documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Run the Next.js Frontend
Navigate to the `frontend/` directory, install node modules, and start the Next.js development server:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to view the dashboard.

---

## 🔗 Relational Data Modeling (Power BI Style)

The application supports multi-table schemas:
1. Click the **Model** toggle in the search bar.
2. Configure multiple dataset tables (e.g. `Sales` at `F:/path/to/sales.csv`, `Products` at `F:/path/to/products.csv`).
3. Define the joining key relationships (or leave them blank to use automatic relationship heuristics).
4. Enter your query (e.g. *"Show sales by product category as a bar chart"*). 

---

## 🧪 Testing

A comprehensive unit test suite is included to verify schema extraction, code execution sandboxing, API endpoints, auto-relationship detection, and the self-correction retry loop:
```bash
cd backend
.\venv\Scripts\python -m unittest tests/test_backend.py
```
