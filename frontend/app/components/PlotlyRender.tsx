'use client';

import React, { useState } from 'react';
import createPlotlyComponent from 'react-plotly.js/factory';
import MicroChart from './MicroChart';
import Plotly from 'plotly.js-dist-min';

// Create the custom Plotly component using the dist-min library to optimize bundle size
const Plot = createPlotlyComponent(Plotly);

interface PlotlyRenderProps {
  data: any[];
  layout: any;
  frames?: any[];
  config?: any;
  onChartClick?: (point: any, event?: any) => void;
  widgetId?: string;
  dashboardContext?: any;
}

export default function PlotlyRender({ data, layout, frames, config, onChartClick, widgetId, dashboardContext }: PlotlyRenderProps) {
  const [hoverState, setHoverState] = useState<{
    visible: boolean;
    x: number;
    y: number;
    targetCol: string;
    targetVal: any;
    metricCol: string;
  } | null>(null);

  // Merge layout options for responsive and modern aesthetics
  const enhancedLayout = {
    ...layout,
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)', // transparent widget background
    plot_bgcolor: 'rgba(0,0,0,0)',  // transparent plot area
    font: {
      family: 'system-ui, -apple-system, sans-serif',
      color: '#3f3f46', // tailwind zinc-700 (fits light/pastel theme)
      ...layout?.font,
    },
    // Force responsiveness
    margin: {
      l: 50,
      r: 30,
      t: 50,
      b: 50,
      pad: 4,
      ...layout?.margin,
    },
    // Stylize grid lines and axes to fit the light pastel theme
    xaxis: {
      gridcolor: '#e4e4e7', // zinc-200 (light gridlines)
      zerolinecolor: '#d4d4d8', // zinc-300
      ...layout?.xaxis,
    },
    yaxis: {
      gridcolor: '#e4e4e7', // zinc-200 (light gridlines)
      zerolinecolor: '#d4d4d8', // zinc-300
      ...layout?.yaxis,
    }
  };

  const defaultConfig = {
    responsive: true,
    displayModeBar: 'hover',
    displaylogo: false,
    ...config,
  };

  return (
    <div className="w-full h-full flex items-center justify-center overflow-hidden">
      <Plot
        data={data}
        layout={enhancedLayout}
        frames={frames}
        config={defaultConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        onClick={(clickData: any) => {
          if (onChartClick && clickData && clickData.points && clickData.points.length > 0) {
            onChartClick(clickData.points[0], clickData.event);
          }
        }}
        onHover={(hoverData: any) => {
          if (!dashboardContext) return; // Viz in tooltip disabled if no context
          if (hoverData && hoverData.points && hoverData.points.length > 0) {
            const pt = hoverData.points[0];
            const e = hoverData.event;
            
            // Heuristically determine what the target and metric are.
            // Typically x is category and y is value, or label is category and value is value.
            let tCol = pt.data.xsrc || pt.data.name || 'Category';
            let tVal = pt.x !== undefined ? pt.x : pt.label;
            let mCol = pt.data.ysrc || 'Value';
            
            if (pt.data.orientation === 'h') {
              tVal = pt.y !== undefined ? pt.y : pt.label;
            }

            if (tVal !== undefined && pt.y !== undefined) {
              setHoverState({
                visible: true,
                x: e.clientX,
                y: e.clientY,
                targetCol: String(tCol),
                targetVal: tVal,
                metricCol: String(mCol)
              });
            }
          }
        }}
        onUnhover={() => {
          setHoverState(null);
        }}
      />
      
      {/* Custom Tooltip Portal */}
      {hoverState && hoverState.visible && dashboardContext && (
        <div 
          className="fixed z-50 bg-zinc-950/95 border border-zinc-800 rounded-lg shadow-xl py-2 px-3 animate-fadeIn pointer-events-none backdrop-blur-md"
          style={{ 
            top: Math.min(hoverState.y + 15, typeof window !== 'undefined' ? window.innerHeight - 200 : 500), 
            left: Math.min(hoverState.x + 15, typeof window !== 'undefined' ? window.innerWidth - 250 : 100),
            // ensure it doesn't go off-screen
            transform: 'translate(0, 0)'
          }}
        >
          <div className="flex flex-col text-xs text-zinc-300">
            <span className="font-bold mb-1 border-b border-zinc-800 pb-1">{hoverState.targetVal}</span>
            <MicroChart 
              dashboardContext={dashboardContext}
              targetCol={hoverState.targetCol}
              targetVal={hoverState.targetVal}
              metricCol={hoverState.metricCol}
            />
          </div>
        </div>
      )}
    </div>
  );
}
