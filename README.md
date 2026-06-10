# Agentic Text-to-BI Application 📊✨

An advanced, agentic, natural language Business Intelligence (BI) platform designed to mimic **Power BI's relational data modeling** and **Tableau's visual grammar** using an LLM agent workflow.

This application allows users to query single or multiple datasets using plain English, automatically resolves relationships (joins), generates interactive Plotly visualizations, and renders them inside a responsive, drag-and-drop dashboard canvas alongside AI-generated analytical insights.

---

## 🚀 Key Features

### 1. Relational Data Modeling & Multi-Source Engine (Power BI Style)
- **Hybrid Data Sources**: Connect to local `.csv` / `.xlsx` files or query live SQL databases (SQLite, PostgreSQL) directly using SQLAlchemy connection strings.
- **Heuristics Auto-Relationship Detection**: If join keys are omitted, the backend heuristically maps tables using exact key matching (e.g., `store_id`) and key-substring matching (e.g., mapping `Products.id` to `Sales.product_id`).
- **Custom Calculated Metrics Catalog**: Define calculated columns in the data model (e.g., `Margin = (Sales - Cost) / Sales`) which are pre-evaluated using Pandas `.eval()` and registered for the LLM to easily query.
- **Time Intelligence Sandbox Helpers**: Pre-injected sandbox functions (`calculate_ytd`, `calculate_rolling_average`, `calculate_yoy_growth`) allow the LLM to generate accurate chronological aggregates easily.

### 2. Interactive Slicers & Tableau Cross-Filtering
- **Cross-Filtering**: Clicking a point or bar in any chart captures the clicked value and automatically slices all other charts on the dashboard to match.
- **Active Slicer Panel**: A dedicated active filters panel at the top shows all active filters, letting users reset them individually or clear all filters.
- **Pandas Slicing Pre-Execution**: Filters are applied directly in Pandas on the backend *before* chart generation, ensuring accurate secondary aggregates (averages, counts, sums).

### 3. Inspectable BI Cards & AI Data Insights
- **Data Trace Insights Extraction**: Analytical coordinate data is extracted from active Plotly traces and summarized by a secondary Gemini LLM agent into a concise 2-3 sentence summary.
- **Multi-Tab Widget Switcher**: Toggle between:
  - **📊 Chart**: Interactive, responsive React-Plotly visualization.
  - **💡 Insights**: AI descriptive summary of trace findings.
  - **💻 Code**: The raw Python code executed in the sandbox.

### 4. Customizer Panel, Downloads, & PDF Export
- **Visual Style Customizer**: Tweak active charts directly from the dashboard: swap chart type (bar, line, scatter, pie), change color schemes (Indigo, Emerald, Amber, Rose, Violet), and show/hide gridlines.
- **Multi-Format Active Downloads**: Click the download button on any widget to export the active tab:
  - Chart Tab -> Standalone interactive HTML page (Plotly embed).
  - Insights Tab -> Analytical report text file.
  - Code Tab -> Sandboxed executable Python script.
- **Export PDF**: Click the header print button to launch the system print dialog and export the entire dashboard layout as a clean, stacked PDF, automatically styled for export.

### 5. Safe Sandbox & Self-Correction Loop
- **Execution Sandbox**: Generated Python code runs locally inside a restricted execution sandbox, limiting builtins and allowing only essential data libraries (`pandas`, `numpy`, `plotly`, `datetime`, `json`, `math`).
- **Traceback Self-Correction**: When syntax or execution errors are raised, the error is fed back to the LLM for self-correction (retries up to 3 times).

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
## 🔗 Relational Data Modeling & Custom Metrics

The application supports advanced multi-table models, live database loading, and custom metrics:

1. **Toggle Model View**: Click the **Model** toggle in the navbar to open advanced configuration.
2. **Configure Data Tables**: 
   - Add multiple tables.
   - Choose **File** source to upload local CSV/Excel files, or **Database** source to connect to SQLite or PostgreSQL engines using SQLAlchemy connection URIs. Verify connections instantly using the **Test Connection** button.
3. **Set Join Relationships**: Define explicit foreign key relationships (e.g., `Sales.product_id` to `Products.id`), or leave blank to let the heuristic engine resolve columns automatically.
4. **Define Custom Calculated Columns**: Add custom formulas to the Metrics Catalog (e.g. `ProfitMargin` with formula `(Sales - Cost) / Sales` on table `df`).
5. **Ask Plain English Queries**: Enter your prompt (e.g. *"Show ProfitMargin by category"* or *"Plot rolling average sales over time"*).

---

## 🧪 Testing

A comprehensive unit test suite is included to verify schema extraction, code execution sandboxing, API endpoints, auto-relationship detection, and the self-correction retry loop:
```bash
cd backend
.\venv\Scripts\python -m unittest tests/test_backend.py
```
