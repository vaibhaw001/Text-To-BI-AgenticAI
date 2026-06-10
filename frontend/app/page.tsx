'use client';

import React, { useState, useEffect } from 'react';
import { Responsive, useContainerWidth } from 'react-grid-layout';
import ChartWidget from './components/ChartWidget';

const ResponsiveGrid = Responsive as any;

interface Widget {
  id: string;
  title: string;
  chartJson: any;
  code: string;
  prompt: string;
  insights?: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export default function Dashboard() {
  const [prompt, setPrompt] = useState('');
  const [filePath, setFilePath] = useState('f:\\vaibhaw\\ai agentic da\\backend\\tests\\sample_sales.csv');
  const [uploadedFileName, setUploadedFileName] = useState<string | null>('sample_sales.csv');
  const [uploading, setUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [layouts, setLayouts] = useState<any>({ lg: [] });
  
  // Track active tab view for each widget card ('chart' | 'insights' | 'code')
  const [widgetTabs, setWidgetTabs] = useState<Record<string, 'chart' | 'insights' | 'code'>>({});

  // Global filters representing Power BI slicers & Tableau cross-filtering
  const [globalFilters, setGlobalFilters] = useState<Record<string, any>>({});

  const getWidgetTab = (id: string) => widgetTabs[id] || 'chart';
  const setWidgetTab = (id: string, tab: 'chart' | 'insights' | 'code') => {
    setWidgetTabs(prev => ({ ...prev, [id]: tab }));
  };

  // Responsive container width hooks from react-grid-layout v2+
  const { width, containerRef, mounted } = useContainerWidth();

  // Custom relationship builder states (Power BI style)
  const [useMultipleTables, setUseMultipleTables] = useState(false);
  const [tablesInput, setTablesInput] = useState<{
    name: string;
    path: string;
    fileName?: string;
    sourceType: 'file' | 'db';
    dbType: 'sqlite' | 'postgresql';
    dbConn: string;
    dbTable?: string;
    dbQuery?: string;
    dbVerified?: boolean;
    dbError?: string;
  }[]>([
    {
      name: 'Sales',
      path: 'f:\\vaibhaw\\ai agentic da\\backend\\tests\\sample_sales.csv',
      fileName: 'sample_sales.csv',
      sourceType: 'file',
      dbType: 'sqlite',
      dbConn: 'sqlite:///backend/data/chinook.db',
      dbTable: '',
      dbQuery: '',
      dbVerified: false
    }
  ]);
  const [relationshipsInput, setRelationshipsInput] = useState<{ from_table: string; from_col: string; to_table: string; to_col: string }[]>([]);
  const [multiUploading, setMultiUploading] = useState<Record<number, boolean>>({});
  
  // Custom metrics catalog states
  const [metricsInput, setMetricsInput] = useState<{ name: string; expression: string; table: string }[]>([]);
  
  // Widget customization states
  const [customizingWidgetId, setCustomizingWidgetId] = useState<string | null>(null);

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('http://127.0.0.1:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Upload failed');
      }

      const data = await res.json();
      if (data.success && data.file_path) {
        setFilePath(data.file_path);
        setUploadedFileName(file.name);
      } else {
        throw new Error('Upload failed on server');
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const handleMultiTableFileUpload = async (idx: number, file: File) => {
    setMultiUploading(prev => ({ ...prev, [idx]: true }));
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('http://127.0.0.1:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Upload failed');
      }

      const data = await res.json();
      if (data.success && data.file_path) {
        const copy = [...tablesInput];
        copy[idx].path = data.file_path;
        copy[idx].fileName = file.name;
        // Auto-populate table name from filename if name is empty
        if (!copy[idx].name) {
          const cleanName = file.name.split('.')[0].replace(/[^a-zA-Z0-9]/g, '');
          copy[idx].name = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
        }
        setTablesInput(copy);
      } else {
        throw new Error('Upload failed on server');
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || `Failed to upload file for table ${idx + 1}`);
    } finally {
      setMultiUploading(prev => ({ ...prev, [idx]: false }));
    }
  };

  const handleTestDbConnection = async (idx: number) => {
    const table = tablesInput[idx];
    if (!table.dbConn) {
      const copy = [...tablesInput];
      copy[idx].dbError = 'Connection string is required';
      copy[idx].dbVerified = false;
      setTablesInput(copy);
      return;
    }

    const copy = [...tablesInput];
    copy[idx].dbError = undefined;
    copy[idx].dbVerified = false;
    setTablesInput(copy);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/test-db', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          db_type: table.dbType,
          connection_string: table.dbConn,
          table_name: table.dbTable || null,
          query: table.dbQuery || null,
        }),
      });

      const data = await res.json();
      const updated = [...tablesInput];
      if (res.ok && data.success) {
        updated[idx].dbVerified = true;
        updated[idx].dbError = undefined;
        if (!updated[idx].name && table.dbTable) {
          updated[idx].name = table.dbTable;
        }
      } else {
        updated[idx].dbVerified = false;
        updated[idx].dbError = data.error || 'Connection failed';
      }
      setTablesInput(updated);
    } catch (err: any) {
      console.error(err);
      const updated = [...tablesInput];
      updated[idx].dbVerified = false;
      updated[idx].dbError = err.message || 'Network error connecting to DB';
      setTablesInput(updated);
    }
  };

  const customizeWidgetVisual = (
    widgetId: string, 
    customConfig: { chartType?: string; color?: string; showGrid?: boolean }
  ) => {
    setWidgets(prev => prev.map(w => {
      if (w.id !== widgetId) return w;
      
      const chartJsonCopy = JSON.parse(JSON.stringify(w.chartJson));
      
      if (chartJsonCopy.data && chartJsonCopy.data.length > 0) {
        chartJsonCopy.data.forEach((trace: any) => {
          if (customConfig.chartType) {
            if (customConfig.chartType === 'line') {
              trace.type = 'scatter';
              trace.mode = 'lines+markers';
            } else if (customConfig.chartType === 'bar') {
              trace.type = 'bar';
              delete trace.mode;
            } else if (customConfig.chartType === 'scatter') {
              trace.type = 'scatter';
              trace.mode = 'markers';
            } else if (customConfig.chartType === 'pie') {
              trace.type = 'pie';
              if (trace.x && trace.y) {
                trace.labels = trace.x;
                trace.values = trace.y;
              }
            }
          }
          if (customConfig.color) {
            if (trace.type === 'pie') {
              trace.marker = { ...trace.marker, colors: [customConfig.color, '#6366f1', '#10b981', '#f59e0b', '#ec4899'] };
            } else {
              trace.marker = { ...trace.marker, color: customConfig.color };
              trace.line = { ...trace.line, color: customConfig.color };
            }
          }
        });
      }

      if (customConfig.showGrid !== undefined && chartJsonCopy.layout) {
        if (!chartJsonCopy.layout.xaxis) chartJsonCopy.layout.xaxis = {};
        if (!chartJsonCopy.layout.yaxis) chartJsonCopy.layout.yaxis = {};
        chartJsonCopy.layout.xaxis.showgrid = customConfig.showGrid;
        chartJsonCopy.layout.yaxis.showgrid = customConfig.showGrid;
      }
      
      return { ...w, chartJson: chartJsonCopy };
    }));
  };

  // Trigger reloading of all active widgets whenever the global filter changes
  useEffect(() => {
    if (widgets.length > 0) {
      refreshAllWidgets(globalFilters);
    }
  }, [globalFilters]);

  const refreshAllWidgets = async (activeFilters: Record<string, any>) => {
    setIsLoading(true);
    setError(null);
    try {
      const updatedWidgets = await Promise.all(widgets.map(async (w) => {
        const payload: any = {
          prompt: w.prompt,
          filters: activeFilters,
        };

        if (useMultipleTables) {
          payload.tables = tablesInput.map(t => {
            const tConf: any = { name: t.name };
            if (t.sourceType === 'db') {
              tConf.db_connection = {
                db_type: t.dbType,
                connection_string: t.dbConn,
                table_name: t.dbTable || null,
                query: t.dbQuery || null
              };
            } else {
              tConf.path = t.path;
            }
            return tConf;
          });
          if (relationshipsInput.length > 0) {
            const apiRel: Record<string, string[]> = {};
            relationshipsInput.forEach(r => {
              if (r.from_table && r.from_col) apiRel[r.from_table] = [r.from_col];
              if (r.to_table && r.to_col) apiRel[r.to_table] = [r.to_col];
            });
            payload.relationships = apiRel;
          }
        } else {
          payload.file_path = filePath;
        }

        if (metricsInput.length > 0) {
          payload.metrics = metricsInput.map(m => ({
            name: m.name,
            expression: m.expression,
            table: m.table
          }));
        }

        const response = await fetch('http://127.0.0.1:8000/api/generate-chart', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Failed to update chart.');
        }

        return {
          ...w,
          chartJson: data.chart_json,
          code: data.code,
          insights: data.insights,
        };
      }));

      setWidgets(updatedWidgets);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to apply filter to dashboard charts.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLayoutChange = (currentLayout: any, allLayouts: any) => {
    setLayouts(allLayouts);
    setWidgets((prevWidgets) =>
      prevWidgets.map((w) => {
        const match = currentLayout.find((item: any) => item.i === w.id);
        if (match) {
          return {
            ...w,
            x: match.x,
            y: match.y,
            w: match.w,
            h: match.h,
          };
        }
        return w;
      })
    );
  };

  const handleAddWidget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const payload: any = {
        prompt: prompt,
        filters: globalFilters, // Pass active filter states
      };

      if (useMultipleTables) {
        payload.tables = tablesInput.map(t => {
          const tConf: any = { name: t.name };
          if (t.sourceType === 'db') {
            tConf.db_connection = {
              db_type: t.dbType,
              connection_string: t.dbConn,
              table_name: t.dbTable || null,
              query: t.dbQuery || null
            };
          } else {
            tConf.path = t.path;
          }
          return tConf;
        });
        if (relationshipsInput.length > 0) {
          const apiRel: Record<string, string[]> = {};
          relationshipsInput.forEach(r => {
            if (r.from_table && r.from_col) apiRel[r.from_table] = [r.from_col];
            if (r.to_table && r.to_col) apiRel[r.to_table] = [r.to_col];
          });
          payload.relationships = apiRel;
        }
      } else {
        payload.file_path = filePath;
      }

      if (metricsInput.length > 0) {
        payload.metrics = metricsInput.map(m => ({
          name: m.name,
          expression: m.expression,
          table: m.table
        }));
      }

      const response = await fetch('http://127.0.0.1:8000/api/generate-chart', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to generate visual chart.');
      }

      const newId = `widget_${Date.now()}`;
      const title = data.chart_json?.layout?.title?.text || `Chart: ${prompt.slice(0, 30)}...`;
      
      const newWidget: Widget = {
        id: newId,
        title: title,
        chartJson: data.chart_json,
        code: data.code,
        prompt: prompt,
        insights: data.insights,
        x: 0,
        y: widgets.length * 4,
        w: 6,
        h: 4,
      };

      const updatedWidgets = [...widgets, newWidget];
      setWidgets(updatedWidgets);
      
      setLayouts({
        lg: updatedWidgets.map((w) => ({
          i: w.id,
          x: w.x,
          y: w.y,
          w: w.w,
          h: w.h,
          minW: 3,
          minH: 2,
        })),
      });

      setPrompt('');
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteWidget = (id: string) => {
    const updated = widgets.filter((w) => w.id !== id);
    setWidgets(updated);
    setLayouts({
      lg: updated.map((w) => ({
        i: w.id,
        x: w.x,
        y: w.y,
        w: w.w,
        h: w.h,
        minW: 3,
        minH: 2,
      })),
    });
  };

  const handleDownloadWidget = (w: Widget) => {
    const activeTab = getWidgetTab(w.id);
    const safeTitle = w.title.replace(/[^a-zA-Z0-9]/g, '_');
    
    if (activeTab === 'chart') {
      const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${w.title}</title>
  <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
  <style>
    body {
      background-color: #09090b;
      color: #fafafa;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    #chart-container {
      width: 90%;
      max-width: 1000px;
      background: #18181b;
      border: 1px solid #27272a;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    h2 {
      margin-top: 0;
      margin-bottom: 15px;
      font-size: 1.25rem;
      font-weight: 600;
      border-bottom: 1px solid #27272a;
      padding-bottom: 10px;
    }
  </style>
</head>
<body>
  <div id="chart-container">
    <h2>${w.title}</h2>
    <div id="plotly-chart" style="width: 100%; height: 500px;"></div>
  </div>
  <script>
    const data = ${JSON.stringify(w.chartJson?.data || [])};
    const layout = ${JSON.stringify(w.chartJson?.layout || {})};
    if (layout) {
      layout.paper_bgcolor = 'rgba(0,0,0,0)';
      layout.plot_bgcolor = 'rgba(0,0,0,0)';
      if (layout.font) layout.font.color = '#e4e4e7';
      layout.margin = { t: 40, r: 40, b: 40, l: 60 };
    }
    Plotly.newPlot('plotly-chart', data, layout, { responsive: true });
  </script>
</body>
</html>`;
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeTitle}_chart.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (activeTab === 'insights') {
      const textContent = `AI Analytical Insights for: ${w.title}\nQuery Prompt: ${w.prompt}\n\n${w.insights || ''}`;
      const blob = new Blob([textContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeTitle}_insights.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (activeTab === 'code') {
      const blob = new Blob([w.code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeTitle}_code.py`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  // Tableau Cross-Filtering: Capture clicks on Plotly points and apply as a dashboard filter
  const handleChartClick = (point: any) => {
    console.log("Chart clicked:", point);
    
    // 1. Try to extract column name from X or Y axis titles (which holds DF column names)
    let colName = point.xaxis?.title?.text;
    let val = point.x;

    if (point.yaxis?.title?.text && isNaN(Number(point.y))) {
      colName = point.yaxis.title.text;
      val = point.y;
    }

    // Pie chart fallback
    if (!colName && point.label) {
      colName = point.data?.labelsrc || 'Category';
      val = point.label;
    }

    if (!colName) {
      // General fallback
      colName = 'Category';
    }

    // Clean column name (removing HTML formatting Plotly sometimes adds)
    colName = colName.replace(/<[^>]*>/g, '').trim();
    
    if (colName && val !== undefined) {
      setGlobalFilters(prev => ({
        ...prev,
        [colName]: val
      }));
    }
  };

  const handleClearFilter = (col: string) => {
    setGlobalFilters(prev => {
      const copy = { ...prev };
      delete copy[col];
      return copy;
    });
  };

  const handleClearAllFilters = () => {
    setGlobalFilters({});
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* Top Navbar */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-purple-600 via-indigo-600 to-blue-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              BI
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white">Agentic Text-to-BI</h1>
              <p className="text-xs text-zinc-500">Power BI Relational Model & Tableau Visual Grammar</p>
            </div>
          </div>

          {/* Prompt Form */}
          <form onSubmit={handleAddWidget} className="flex-1 w-full max-w-3xl flex flex-col sm:flex-row items-center gap-2">
            <div className="relative flex-1 w-full">
              <input
                type="text"
                placeholder="Ask for a visualization (e.g. 'Show me sales by region as a pie chart')..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full pl-4 pr-16 py-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 focus:outline-none focus:ring-2 focus:ring-purple-500/50 text-sm text-white placeholder-zinc-500 backdrop-blur-sm transition-all"
                disabled={isLoading}
              />
              <button 
                type="button" 
                onClick={() => setUseMultipleTables(!useMultipleTables)}
                title="Toggle Relational Modeling Options"
                className={`absolute right-3 top-2.5 text-xs font-semibold px-2 py-1 rounded transition-colors ${useMultipleTables ? 'bg-purple-500 text-white' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'}`}
              >
                Model
              </button>
            </div>

            {!useMultipleTables && (
              <div className="relative w-full sm:w-64">
                <input
                  type="file"
                  id="single-file-upload"
                  className="hidden"
                  accept=".csv,.xlsx,.xls"
                  disabled={isLoading || uploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file);
                  }}
                />
                <label
                  htmlFor="single-file-upload"
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 text-xs text-zinc-300 backdrop-blur-sm cursor-pointer hover:bg-zinc-850 hover:border-zinc-700 transition-all ${uploading ? 'opacity-70 cursor-not-allowed' : ''}`}
                >
                  <span className="truncate max-w-[170px]">
                    {uploading ? (
                      <span className="flex items-center gap-1">
                        <span className="h-3 w-3 animate-spin rounded-full border border-zinc-500 border-t-white"></span>
                        Uploading...
                      </span>
                    ) : uploadedFileName ? (
                      `📁 ${uploadedFileName}`
                    ) : (
                      '📁 Upload Dataset'
                    )}
                  </span>
                  {!uploading && (
                    <span className="text-[10px] text-purple-400 font-medium px-1.5 py-0.5 rounded bg-purple-950/40 border border-purple-800/30">
                      Browse
                    </span>
                  )}
                </label>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !prompt.trim()}
              className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/35 hover:shadow-indigo-500/50 active:scale-95 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></div>
                  Generating...
                </>
              ) : (
                'Generate Chart'
              )}
            </button>

            {widgets.length > 0 && (
              <button
                type="button"
                onClick={() => window.print()}
                className="w-full sm:w-auto px-4 py-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 font-medium text-sm transition-all active:scale-95 flex items-center justify-center gap-2 no-print"
                title="Save Entire Dashboard as PDF"
              >
                🖨️ Export PDF
              </button>
            )}
          </form>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6 sm:px-6 lg:px-8">
        
        {/* Power BI-style Active Slicers Pane */}
        {Object.keys(globalFilters).length > 0 && (
          <div className="mb-6 p-4 rounded-xl border border-indigo-500/20 bg-indigo-950/10 backdrop-blur-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fadeIn shadow-lg shadow-indigo-500/5">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-bold text-indigo-400 flex items-center gap-1 mr-1">
                <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
                ⚡ Interactive Filters (Tableau Cross-Filter):
              </span>
              {Object.entries(globalFilters).map(([col, val]) => (
                <span 
                  key={col} 
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-950 border border-indigo-800 text-indigo-200 shadow-sm"
                >
                  <span className="text-zinc-400">{col}:</span>
                  <span className="font-semibold text-white">{String(val)}</span>
                  <button 
                    type="button"
                    onClick={() => handleClearFilter(col)} 
                    className="hover:text-red-400 font-bold ml-1 transition-colors text-sm leading-none"
                    title="Remove Filter"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <button 
              type="button"
              onClick={handleClearAllFilters}
              className="text-xs text-zinc-400 hover:text-white underline font-semibold transition-colors shrink-0"
            >
              Reset Filters
            </button>
          </div>
        )}

        {/* Advanced Relationship modeling panel */}
        {useMultipleTables && (
          <div className="mb-6 p-4 rounded-xl border border-zinc-800 bg-zinc-900/40 backdrop-blur-sm animate-fadeIn">
            <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-purple-500"></span> Relational Data Modeling (Power BI style)
            </h2>
            <p className="text-xs text-zinc-500 mb-4">
              Configure multiple source datasets and define their join relationships. Columns with identical names will be auto-joined if left blank.
            </p>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Tables configuration */}
              <div className="space-y-3">
                <span className="text-xs font-semibold text-zinc-400">📁 1. Data Tables</span>
                {tablesInput.map((t, idx) => (
                  <div key={idx} className="flex flex-col gap-2 p-3 rounded-lg border border-zinc-800 bg-zinc-950/40">
                    <div className="flex gap-2 items-center">
                      <input 
                        type="text" 
                        placeholder="Table Name" 
                        value={t.name}
                        onChange={(e) => {
                          const copy = [...tablesInput];
                          copy[idx].name = e.target.value;
                          setTablesInput(copy);
                        }}
                        className="w-1/2 px-2 py-1 rounded bg-zinc-900 border border-zinc-850 text-xs text-white"
                      />
                      
                      <select
                        value={t.sourceType}
                        onChange={(e) => {
                          const copy = [...tablesInput];
                          copy[idx].sourceType = e.target.value as 'file' | 'db';
                          setTablesInput(copy);
                        }}
                        className="px-2 py-1 rounded bg-zinc-900 border border-zinc-850 text-xs text-zinc-300"
                      >
                        <option value="file">File</option>
                        <option value="db">Database</option>
                      </select>

                      <button 
                        type="button" 
                        onClick={() => setTablesInput(tablesInput.filter((_, i) => i !== idx))}
                        className="text-xs text-red-400 hover:text-red-300 ml-auto px-1"
                      >
                        Delete
                      </button>
                    </div>

                    {t.sourceType === 'file' ? (
                      <div className="relative w-full">
                        <input
                          type="file"
                          id={`multi-file-upload-${idx}`}
                          className="hidden"
                          accept=".csv,.xlsx,.xls"
                          disabled={isLoading || multiUploading[idx]}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleMultiTableFileUpload(idx, file);
                          }}
                        />
                        <label
                          htmlFor={`multi-file-upload-${idx}`}
                          className={`w-full flex items-center justify-between px-2 py-1 rounded border border-zinc-800 bg-zinc-900 text-xs text-zinc-300 cursor-pointer hover:bg-zinc-850 hover:border-zinc-750 transition-all ${multiUploading[idx] ? 'opacity-70 cursor-not-allowed' : ''}`}
                        >
                          <span className="truncate max-w-[170px]">
                            {multiUploading[idx] ? (
                              <span className="flex items-center gap-1">
                                <span className="h-3 w-3 animate-spin rounded-full border border-zinc-550 border-t-white"></span>
                                Uploading...
                              </span>
                            ) : t.fileName ? (
                              `📁 ${t.fileName}`
                            ) : (
                              '📁 Select File'
                            )}
                          </span>
                          {!multiUploading[idx] && (
                            <span className="text-[10px] text-purple-400 font-medium px-1 rounded bg-purple-950/20">
                              Upload
                            </span>
                          )}
                        </label>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-1.5 border-t border-zinc-850 pt-2">
                        <div className="flex gap-2">
                          <select
                            value={t.dbType}
                            onChange={(e) => {
                              const copy = [...tablesInput];
                              copy[idx].dbType = e.target.value as 'sqlite' | 'postgresql';
                              setTablesInput(copy);
                            }}
                            className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 w-1/3"
                          >
                            <option value="sqlite">SQLite</option>
                            <option value="postgresql">Postgres</option>
                          </select>
                          <input
                            type="text"
                            placeholder="URI (e.g. sqlite:///Chinook.db)"
                            value={t.dbConn}
                            onChange={(e) => {
                              const copy = [...tablesInput];
                              copy[idx].dbConn = e.target.value;
                              setTablesInput(copy);
                            }}
                            className="flex-1 px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-[11px] text-white"
                          />
                        </div>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            placeholder="Table Name"
                            value={t.dbTable || ''}
                            onChange={(e) => {
                              const copy = [...tablesInput];
                              copy[idx].dbTable = e.target.value;
                              setTablesInput(copy);
                            }}
                            className="w-1/2 px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-[11px] text-white"
                          />
                          <input
                            type="text"
                            placeholder="Or Query"
                            value={t.dbQuery || ''}
                            onChange={(e) => {
                              const copy = [...tablesInput];
                              copy[idx].dbQuery = e.target.value;
                              setTablesInput(copy);
                            }}
                            className="flex-1 px-2 py-1 rounded bg-zinc-900 border border-zinc-800 text-[11px] text-white"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-2 mt-1">
                          <button
                            type="button"
                            onClick={() => handleTestDbConnection(idx)}
                            className="px-2 py-0.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-medium text-[10px] transition-all active:scale-95"
                          >
                            Test Connection
                          </button>
                          {t.dbVerified && (
                            <span className="text-[10px] text-emerald-400 font-bold">✅ Verified</span>
                          )}
                          {t.dbError && (
                            <span className="text-[9px] text-red-400 max-w-[120px] truncate" title={t.dbError}>
                              ❌ Failed
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setTablesInput([...tablesInput, { 
                    name: '', 
                    path: '', 
                    fileName: '', 
                    sourceType: 'file',
                    dbType: 'sqlite',
                    dbConn: 'sqlite:///backend/data/chinook.db'
                  }])}
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 mt-1"
                >
                  + Add Table
                </button>
              </div>

              {/* Relationships configuration */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-zinc-400">2. Relationships (Foreign Keys) - Optional</span>
                {relationshipsInput.length === 0 ? (
                  <p className="text-xs text-zinc-600 italic">No relationships defined. Heuristics will automatically auto-join tables (e.g. matching store_id or product_id to id).</p>
                ) : (
                  relationshipsInput.map((r, idx) => (
                    <div key={idx} className="flex gap-1.5 items-center text-xs">
                      <input 
                        type="text" 
                        placeholder="Table A" 
                        value={r.from_table}
                        onChange={(e) => {
                          const copy = [...relationshipsInput];
                          copy[idx].from_table = e.target.value;
                          setRelationshipsInput(copy);
                        }}
                        className="w-[20%] px-1.5 py-1 rounded bg-zinc-950 border border-zinc-800 text-white text-[11px]"
                      />
                      <input 
                        type="text" 
                        placeholder="Col A" 
                        value={r.from_col}
                        onChange={(e) => {
                          const copy = [...relationshipsInput];
                          copy[idx].from_col = e.target.value;
                          setRelationshipsInput(copy);
                        }}
                        className="w-[25%] px-1.5 py-1 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 text-[11px]"
                      />
                      <span className="text-zinc-600">→</span>
                      <input 
                        type="text" 
                        placeholder="Table B" 
                        value={r.to_table}
                        onChange={(e) => {
                          const copy = [...relationshipsInput];
                          copy[idx].to_table = e.target.value;
                          setRelationshipsInput(copy);
                        }}
                        className="w-[20%] px-1.5 py-1 rounded bg-zinc-950 border border-zinc-800 text-white text-[11px]"
                      />
                      <input 
                        type="text" 
                        placeholder="Col B" 
                        value={r.to_col}
                        onChange={(e) => {
                          const copy = [...relationshipsInput];
                          copy[idx].to_col = e.target.value;
                          setRelationshipsInput(copy);
                        }}
                        className="w-[25%] px-1.5 py-1 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 text-[11px]"
                      />
                      <button 
                        type="button" 
                        onClick={() => setRelationshipsInput(relationshipsInput.filter((_, i) => i !== idx))}
                        className="text-red-400 hover:text-red-300 px-1"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
                <button
                  type="button"
                  onClick={() => setRelationshipsInput([...relationshipsInput, { from_table: '', from_col: '', to_table: '', to_col: '' }])}
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 mt-1"
                >
                  + Define Relationship
                </button>
              </div>

              {/* Metrics Catalog configuration */}
              <div className="space-y-3">
                <span className="text-xs font-semibold text-zinc-400 flex items-center gap-1">
                  📐 3. Metrics Catalog (Calculated Columns)
                </span>
                {metricsInput.length === 0 ? (
                  <p className="text-xs text-zinc-600 italic">No calculated metrics defined. Add formulas like Margin = (Sales - Cost) / Sales.</p>
                ) : (
                  <div className="space-y-2">
                    {metricsInput.map((m, idx) => (
                      <div key={idx} className="flex flex-col gap-1.5 p-2 rounded border border-zinc-800 bg-zinc-950/30">
                        <div className="flex gap-1.5 items-center justify-between">
                          <input
                            type="text"
                            placeholder="Name (e.g. Margin)"
                            value={m.name}
                            onChange={(e) => {
                              const copy = [...metricsInput];
                              copy[idx].name = e.target.value;
                              setMetricsInput(copy);
                            }}
                            className="w-1/3 px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-850 text-xs text-white font-semibold"
                          />
                          <select
                            value={m.table}
                            onChange={(e) => {
                              const copy = [...metricsInput];
                              copy[idx].table = e.target.value;
                              setMetricsInput(copy);
                            }}
                            className="px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-850 text-xs text-zinc-300"
                          >
                            <option value="df">df (Default)</option>
                            {tablesInput.filter(t => t.name).map(t => (
                              <option key={t.name} value={t.name}>{t.name}</option>
                            ))}
                          </select>
                          <button
                            type="button"
                            onClick={() => setMetricsInput(metricsInput.filter((_, i) => i !== idx))}
                            className="text-red-400 hover:text-red-300 text-xs px-1"
                          >
                            ×
                          </button>
                        </div>
                        <input
                          type="text"
                          placeholder="Formula: (Revenue - Cost) / Revenue"
                          value={m.expression}
                          onChange={(e) => {
                            const copy = [...metricsInput];
                            copy[idx].expression = e.target.value;
                            setMetricsInput(copy);
                          }}
                          className="w-full px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-850 text-[11px] text-zinc-300 font-mono"
                        />
                      </div>
                    ))}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setMetricsInput([...metricsInput, { name: '', expression: '', table: tablesInput[0]?.name || 'df' }])}
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 mt-1"
                >
                  + Add Calculated Metric
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div className="mb-6 p-4 rounded-lg border border-red-500/20 bg-red-950/20 text-red-400 text-sm flex items-start gap-3">
            <span className="mt-0.5 text-base">⚠️</span>
            <div className="flex-1">
              <span className="font-bold">Generation Failed: </span>
              {error}
            </div>
          </div>
        )}

        {/* Grid Canvas */}
        {!mounted ? (
          <div className="flex flex-col items-center justify-center min-h-[400px] text-zinc-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            <p className="mt-4 text-xs font-medium tracking-wider">PREPARING DASHBOARD CANVAS...</p>
          </div>
        ) : widgets.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-[400px] border-2 border-dashed border-zinc-800 rounded-xl p-12 text-center bg-zinc-900/10 backdrop-blur-sm mt-4">
            <div className="h-12 w-12 rounded-lg bg-zinc-900 flex items-center justify-center text-zinc-500 font-bold mb-4">
              📊
            </div>
            <h3 className="text-md font-bold text-zinc-300">Your BI Canvas is Empty</h3>
            <p className="text-sm text-zinc-500 max-w-sm mt-1">
              Type an analytical query in the search bar above to generate a ChartWidget and place it on your dashboard canvas.
            </p>
          </div>
        ) : (
          <div ref={containerRef} className="bg-zinc-950/40 rounded-xl border border-zinc-850 p-2 min-h-[500px]">
            <ResponsiveGrid
              className="layout"
              layouts={layouts}
              width={width}
              breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
              cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
              rowHeight={100}
              onLayoutChange={handleLayoutChange}
              draggableHandle=".widget-drag-handle"
              margin={[16, 16]}
            >
              {widgets.map((w) => (
                <div 
                  key={w.id} 
                  className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/40 backdrop-blur-md overflow-hidden hover:border-zinc-700/80 transition-all select-none shadow-md group animate-scaleIn"
                >
                  {/* Widget Header */}
                  <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/85 px-4 py-2 cursor-default">
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      <div className="widget-drag-handle cursor-grab active:cursor-grabbing text-zinc-500 hover:text-zinc-300 px-1 -ml-1">
                        ⋮⋮
                      </div>
                      <h3 className="text-xs font-semibold text-zinc-300 truncate tracking-wide max-w-[200px]" title={w.title}>
                        {w.title}
                      </h3>
                    </div>
                    
                    <div className="flex items-center space-x-1 no-print">
                      <button
                        type="button"
                        onClick={() => setCustomizingWidgetId(customizingWidgetId === w.id ? null : w.id)}
                        className={`text-zinc-500 hover:text-purple-400 transition-colors p-1 ${customizingWidgetId === w.id ? 'text-purple-400' : ''}`}
                        title="Customize Widget Style"
                      >
                        ⚙️
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDownloadWidget(w)}
                        className="text-zinc-500 hover:text-blue-400 transition-colors p-1"
                        title={`Download ${getWidgetTab(w.id) === 'chart' ? 'Interactive Chart (HTML)' : getWidgetTab(w.id) === 'insights' ? 'AI Insights (TXT)' : 'Python Code (PY)'}`}
                      >
                        📥
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteWidget(w.id)}
                        className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                        title="Remove Widget"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* Visual Customize Panel */}
                  {customizingWidgetId === w.id && (
                    <div className="flex flex-wrap items-center gap-3 bg-zinc-900 border-b border-zinc-800 px-4 py-2.5 text-[10px] text-zinc-400 animate-slideDown select-text">
                      <span className="font-semibold text-zinc-300 mr-1">⚙️ Customizer:</span>
                      
                      <div className="flex items-center gap-1.5">
                        <span>Type:</span>
                        <div className="flex gap-1">
                          {['bar', 'line', 'scatter', 'pie'].map(t => (
                            <button
                              key={t}
                              type="button"
                              onClick={() => customizeWidgetVisual(w.id, { chartType: t })}
                              className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 hover:bg-zinc-850 hover:text-white capitalize transition-all"
                            >
                              {t}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 ml-2">
                        <span>Color:</span>
                        <div className="flex gap-1.5">
                          {[
                            { name: 'Indigo', value: '#6366f1' },
                            { name: 'Emerald', value: '#10b981' },
                            { name: 'Amber', value: '#f59e0b' },
                            { name: 'Rose', value: '#f43f5e' },
                            { name: 'Violet', value: '#8b5cf6' }
                          ].map(c => (
                            <button
                              key={c.name}
                              type="button"
                              onClick={() => customizeWidgetVisual(w.id, { color: c.value })}
                              style={{ backgroundColor: c.value }}
                              className="h-3.5 w-3.5 rounded-full border border-white/10 hover:scale-110 active:scale-95 transition-all"
                              title={c.name}
                            />
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 ml-auto">
                        <span>Grid:</span>
                        <div className="flex gap-1">
                          <button
                            type="button"
                            onClick={() => customizeWidgetVisual(w.id, { showGrid: true })}
                            className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 hover:bg-zinc-850 hover:text-white"
                          >
                            Show
                          </button>
                          <button
                            type="button"
                            onClick={() => customizeWidgetVisual(w.id, { showGrid: false })}
                            className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 hover:bg-zinc-850 hover:text-white"
                          >
                            Hide
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Widget Body */}
                  <div className="flex-1 w-full relative overflow-hidden bg-zinc-950/20 flex flex-col justify-between">
                    <div className="flex-1 w-full relative overflow-hidden">
                      {getWidgetTab(w.id) === 'chart' && (
                        <div className="w-full h-full p-2">
                          <ChartWidget 
                            chartJson={w.chartJson} 
                            onChartClick={handleChartClick} // Tableau Cross-Filtering trigger
                          />
                        </div>
                      )}
                      
                      {getWidgetTab(w.id) === 'insights' && (
                        <div className="w-full h-full p-4 overflow-y-auto text-xs text-zinc-300 leading-relaxed flex flex-col justify-start select-text">
                          <span className="font-bold text-zinc-400 block mb-2">💡 AI Analytical Insights:</span>
                          <p>{w.insights || "No insights generated for this visualization."}</p>
                        </div>
                      )}
                      
                      {getWidgetTab(w.id) === 'code' && (
                        <div className="w-full h-full p-3 overflow-y-auto font-mono text-[10px] text-zinc-400 bg-zinc-950/40 select-text">
                          <span className="font-semibold text-zinc-500 block mb-2">Generated Python Plotly code:</span>
                          <pre className="whitespace-pre-wrap">{w.code}</pre>
                        </div>
                      )}
                    </div>

                    {/* Widget Footer Tab Bar */}
                    <div className="flex border-t border-zinc-800/80 bg-zinc-900/50 text-[10px] font-medium text-zinc-500 select-none">
                      <button 
                        type="button"
                        onClick={() => setWidgetTab(w.id, 'chart')} 
                        className={`flex-1 py-2 text-center transition-colors ${getWidgetTab(w.id) === 'chart' ? 'text-purple-400 border-t border-purple-500 bg-zinc-950/25 font-semibold' : 'hover:text-zinc-350 hover:bg-zinc-800/20'}`}
                      >
                        📊 Chart
                      </button>
                      {w.insights && (
                        <button 
                          type="button"
                          onClick={() => setWidgetTab(w.id, 'insights')} 
                          className={`flex-1 py-2 text-center transition-colors ${getWidgetTab(w.id) === 'insights' ? 'text-indigo-400 border-t border-indigo-500 bg-zinc-950/25 font-semibold' : 'hover:text-zinc-350 hover:bg-zinc-800/20'}`}
                        >
                          💡 Insights
                        </button>
                      )}
                      <button 
                        type="button"
                        onClick={() => setWidgetTab(w.id, 'code')} 
                        className={`flex-1 py-2 text-center transition-colors ${getWidgetTab(w.id) === 'code' ? 'text-blue-400 border-t border-blue-500 bg-zinc-950/25 font-semibold' : 'hover:text-zinc-350 hover:bg-zinc-800/20'}`}
                      >
                        💻 Code
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </ResponsiveGrid>
          </div>
        )}
      </main>
    </div>
  );
}
