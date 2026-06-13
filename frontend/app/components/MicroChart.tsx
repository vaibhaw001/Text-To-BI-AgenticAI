'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js/factory').then(mod => {
  const Plotly = require('plotly.js-dist-min');
  return mod.default(Plotly);
}), { ssr: false });

interface MicroChartProps {
  dashboardContext: any;
  targetCol: string;
  targetVal: any;
  metricCol: string;
}

export default function MicroChart({ dashboardContext, targetCol, targetVal, metricCol }: MicroChartProps) {
  const [data, setData] = useState<any[]>([]);
  const [dateCol, setDateCol] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    
    async function fetchData() {
      setIsLoading(true);
      setError(null);
      try {
        const payload: any = {
          file_path: dashboardContext.filePath,
          filters: dashboardContext.globalFilters,
          target_column: targetCol,
          target_value: targetVal,
          metric_column: metricCol,
        };

        if (dashboardContext.useMultipleTables) {
          payload.tables = dashboardContext.tablesInput.map((t: any) => {
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
          if (dashboardContext.relationshipsInput?.length > 0) {
            const apiRel: Record<string, string[]> = {};
            dashboardContext.relationshipsInput.forEach((r: any) => {
              if (r.from_table && r.from_col) apiRel[r.from_table] = [r.from_col];
              if (r.to_table && r.to_col) apiRel[r.to_table] = [r.to_col];
            });
            payload.relationships = apiRel;
          }
        }

        if (dashboardContext.metricsInput?.length > 0) {
          payload.metrics = dashboardContext.metricsInput.map((m: any) => ({
            name: m.name,
            expression: m.expression,
            table: m.table
          }));
        }

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/tooltip-data`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const result = await response.json();
        
        if (!isMounted) return;

        if (result.success) {
          setData(result.data || []);
          setDateCol(result.date_column || 'Distribution');
        } else {
          setError(result.error || 'Failed to fetch');
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Network error');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [dashboardContext, targetCol, targetVal, metricCol]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-4">
        <div className="animate-spin h-5 w-5 border-2 border-purple-500 border-t-transparent rounded-full mb-2"></div>
        <span className="text-[10px] text-zinc-400">Loading historical trend...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 text-[10px] text-red-400">
        Trend Error: {error}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="p-3 text-[10px] text-zinc-500">
        No trend data available.
      </div>
    );
  }

  // Build minimal chart data
  const x = data.map(d => d.label);
  const y = data.map(d => d.value);

  const plotData = [
    {
      x,
      y,
      type: 'scatter',
      mode: 'lines+markers',
      line: { color: '#8b5cf6', width: 2 },
      marker: { size: 4, color: '#8b5cf6' },
      fill: 'tozeroy',
      fillcolor: 'rgba(139, 92, 246, 0.1)',
      hoverinfo: 'none' // Don't show tooltip on tooltip
    }
  ];

  const plotLayout = {
    autosize: true,
    margin: { l: 20, r: 10, t: 10, b: 20, pad: 0 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    xaxis: { 
      showgrid: false, 
      zeroline: false, 
      showticklabels: true,
      tickfont: { size: 8, color: '#a1a1aa' },
      fixedrange: true
    },
    yaxis: { 
      showgrid: true, 
      gridcolor: '#27272a', 
      zeroline: false, 
      showticklabels: true,
      tickfont: { size: 8, color: '#a1a1aa' },
      fixedrange: true
    },
    font: { family: 'system-ui, -apple-system, sans-serif' }
  };

  return (
    <div className="w-[200px] h-[120px] pt-1">
      <div className="px-2 pb-1 flex justify-between items-center border-b border-zinc-800/50 mb-1">
        <span className="text-[9px] font-semibold text-zinc-400 uppercase tracking-wider">{dateCol} Trend</span>
      </div>
      <div className="w-full h-full pb-4">
        <Plot
          data={plotData as any}
          layout={plotLayout}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler={true}
        />
      </div>
    </div>
  );
}
