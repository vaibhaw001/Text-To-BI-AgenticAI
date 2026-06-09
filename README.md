# Agentic Text-to-BI Application 📊✨

An advanced, agentic, natural language Business Intelligence (BI) platform designed to mimic **Power BI's relational data modeling** and **Tableau's visual grammar** using an LLM agent workflow.

This application allows users to query single or multiple datasets using plain English, automatically resolves relationships (joins), generates interactive Plotly visualizations, and renders them inside a responsive, drag-and-drop dashboard canvas.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js (App Router), Tailwind CSS, [React-Plotly.js](https://github.com/plotly/react-plotly.js/), [React-Grid-Layout](https://github.com/react-grid-layout/react-grid-layout)
- **Backend**: Python (FastAPI), Pandas/SQL, [LangChain](https://github.com/langchain-ai/langchain)
- **Agent / LLM**: Google Gemini (`gemini-3.5-flash`) via LangChain Google GenAI
- **Visualization Engine**: Plotly (Python generates the Plotly JSON schema, Next.js renders it client-side)

---

## 📐 Architecture Rules & Security

1. **Zero Raw Data to LLM**: The backend *never* sends raw data rows to the LLM. It only extracts and sends metadata: column names, data types, and a 3-row markdown sample table.
2. **Grammar of Graphics**: The LLM agent acts as a visualization data scientist, mapping dimensions (categories, dates) and measures (numeric values) to appropriate Plotly visual channels (X, Y, colors, sizes).
3. **Execution Sandbox**: Generated Python code is executed locally in a restricted sandbox context, limiting available builtins, pre-injecting data tables as variables, and strictly restricting imports (allowing only `pandas`, `plotly`, `numpy`, `datetime`, `json`, `math`).
4. **Self-Correction Retry Loop**: If the execution throws a syntax, value, or runtime error (e.g. invalid columns), the backend catches the traceback error and feeds it back to the Gemini agent. It attempts self-correction up to 3 times before returning a failure.

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
3. Define the joining key relationships (e.g., table `Sales` joins using `product_id` to table `Products` using `id`).
4. Enter your query (e.g. *"Show sales by product category as a bar chart"*). 
5. The LLM agent reads this relational mapping, automatically writes the Pandas `pd.merge()` code to join the tables, and creates the chart.

---

## 🧪 Testing

A comprehensive unit test suite is included to verify schema extraction, code execution sandboxing, API endpoints, and the self-correction retry loop:
```bash
cd backend
.\venv\Scripts\python -m unittest tests/test_backend.py
```
