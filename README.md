# Agentic Text-to-BI Application 📊✨

An advanced, agentic, natural language Business Intelligence (BI) platform designed to mimic **Power BI's relational data modeling** and **Tableau's visual grammar** using an LLM agent workflow.

This application allows users to query single or multiple datasets using plain English, automatically resolves relationships (joins), generates interactive Plotly visualizations, and renders them inside a responsive, drag-and-drop dashboard canvas alongside AI-generated analytical insights.

---

## 🚀 Key Features

### 1. Relational Data Modeling & Multi-Source Engine (Power BI Style)
- **Hybrid Data Sources & DirectQuery**: Connect to local `.csv` / `.xlsx` files or query live SQL databases (SQLite, PostgreSQL, Snowflake) directly using SQLAlchemy connection strings. Toggle `direct_query=True` to compile natural language into optimized SQL on-the-fly and stream aggregates without loading massive tables into memory.
- **Star Schema & Filter Propagation**: Define full Star Schema relationships with directionality (Single vs Both) and cardinality (1:N, M:N). Filtering a dimension table natively propagates semi-joins to filter the connected fact tables before any visualization rendering occurs.
- **Heuristics Auto-Relationship Detection**: If join keys are omitted, the backend heuristically maps tables using exact key matching (e.g., `store_id`) and key-substring matching (e.g., mapping `Products.id` to `Sales.product_id`).
- **DAX-Style Semantic Measure Engine**: A fully-fledged Python emulation layer injects DAX equivalents (`CALCULATE()`, `USERELATIONSHIP()`, `SUMX()`, `AVERAGEX()`, `DIVIDE()`) into the LLM execution sandbox, allowing context-aware dynamic KPI measures that adapt perfectly to the current dashboard slicers.
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

### 4. Advanced Analytics & Explaining Spikes/Dips (Tableau Einstein & Power BI Q&A)
- **Explain the Increase**: Click any data point to trigger growth change attribution analysis on sequential time periods, identifying which categorical factors contributed most to the variance.
- **Key Influencers (Machine Learning)**: Identifies drivers of segment membership or high metric values by training a Decision Tree regressor (`scikit-learn`'s `DecisionTreeRegressor`) and extracting combination rules on categorical dimensions.
- **Slide-out Insights Drawer**: A dedicated interactive drawer displaying growth attribution bar charts, Gemini executive summaries, and a follow-up Q&A text field for asking deeper questions about the data point.

### 5. Automated Time-Series Forecasting & Trend Lines
- **Holt-Winters Forecasting**: Injects double/triple Exponential Smoothing forecast models (`statsmodels.tsa.holtwinters`) into the sandbox globals, allowing the LLM to plot chronological forecasts with predictive confidence bands.
- **OLS Trend Line Fitting**: Instantiates OLS linear regressions (`statsmodels.api.OLS`) over date or categorical timelines to render trend lines and error margin bands.
- **Plotly Confidence Shading**: Integrates styling instructions into the system prompt to guide the LLM in rendering shaded confidence intervals using translucent Plotly Scatter fills (`fill='toself'`).

### 6. Statistical Anomaly Detection & Annotations
- **Outlier Flagging**: Exposes a sandboxed `detect_anomalies` helper supporting both standard deviation **Z-scores** and tree-based **Isolation Forests** (`sklearn.ensemble`).
- **Interactive Tooltip Annotations**: Appends detailed outlier descriptions (e.g., Spike vs Dip, deviation percentage, and Z-score). Instructs the LLM to overlay red circle markers on anomalies and link hover indicators to the anomaly explanation text.

### 7. Dashboard Bookmarks & Layout States
- **Executive Bookmarks**: Save the active dashboard configuration (the layout positions of all charts, active cross-filtering slicers, and selected pages).
- **Bookmarks Panel**: Access a sliding bookmarks drawer to quickly toggle, rename, and load pre-configured report states.

### 8. Advanced Chart Types & Interactive Tooltips
- **Dual-Axis & Combo Charts**: Compare multiple metrics with vastly different scales on a single visualization using dual Y-axes (e.g., Sales as bars on the left axis, and Margin % as a line on the right axis). The grammar syntax explicitly supports independent mark assignments for secondary axes.
- **Viz in Tooltip**: Hovering over a data point triggers an ultra-fast backend heuristic endpoint that intercepts the event, filters data to the specific category, aggregates chronological historical trends, and renders an elegant micro-chart directly inside the cursor tooltip—all in milliseconds without waiting for the LLM.

### 9. Multi-Page Reports, Customizer, Downloads, & PDF Export
- **Multi-Page Reports (Report Tabs)**: Organize your workspace across multiple pages/tabs (e.g. "Sales Overview" and "Product Deep-Dive"). Pages support inline renaming (double-click to edit) and deletion. Widgets are completely scoped to the page they were generated in.
- **Visual Style Customizer**: Tweak active charts directly from the dashboard: swap chart type (bar, line, scatter, pie), change color schemes (Indigo, Emerald, Amber, Rose, Violet), and show/hide gridlines.
- **Multi-Format Active Downloads**: Click the download button on any widget to export the active tab: standalone interactive HTML files, text summaries, or raw Python sandbox scripts.
- **Export PDF**: Click the header print button to export the entire dashboard layout as a clean, stacked PDF, automatically styled for export.

### 10. Safe Sandbox & Self-Correction Loop
- **Execution Sandbox**: Generated Python code runs locally inside a restricted execution sandbox, limiting builtins and allowing only essential data libraries (`pandas`, `numpy`, `plotly`, `datetime`, `json`, `math`, `statsmodels`, `scipy`, `sklearn`).
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


### 3. Run the Next.js Frontend
Navigate to the `frontend/` directory, install node modules, and start the Next.js development server:
```bash
cd frontend
npm install
npm run dev
```

---
## 🔗 Relational Data Modeling & Custom Metrics

The application supports advanced multi-table models, live database loading, and custom metrics:

1. **Toggle Model View**: Click the **Model** toggle in the navbar to open advanced configuration.
2. **Configure Data Tables**: 
   - Add multiple tables.
   - Choose **File** source to upload local CSV/Excel files, or **Database** source to connect to SQL engines using SQLAlchemy connection URIs.
   - You can optionally enable **DirectQuery** to skip loading tables into Pandas and execute queries natively against the database.
3. **Set Join Relationships (Star Schema)**: Define explicit foreign key relationships (e.g., `Sales.product_id` to `Products.id`), configure Cardinality (1:N), and set Cross-Filter Direction (Single or Both). Or leave blank to let the heuristic engine resolve columns automatically.
4. **Define Custom Calculated Columns / Measures**: Add custom DAX-style formulas to the Metrics Catalog to be used by the visualization agent.
5. **Ask Plain English Queries**: Enter your prompt (e.g. *"Show ProfitMargin by category"* or *"Plot rolling average sales over time"*).
6. **Multi-Page Dashboard Scoping**: Add pages using the `➕ Add Page` button in the report pages bar above the canvas. Rename pages by double-clicking the page name or clicking the pencil ✏️ icon. Widgets and dashboard layouts are scoped to the active page, enabling multi-tab dashboard storytelling.

---

## 🧪 Testing

A comprehensive unit test suite is included to verify schema extraction, code execution sandboxing, API endpoints, auto-relationship detection, and the self-correction retry loop:
```bash
cd backend
.\venv\Scripts\python -m unittest tests/test_backend.py
```
