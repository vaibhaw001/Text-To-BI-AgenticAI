'use client';

import React from 'react';
import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';

// Create the custom Plotly component using the dist-min library to optimize bundle size
const Plot = createPlotlyComponent(Plotly);

interface PlotlyRenderProps {
  data: any[];
  layout: any;
  frames?: any[];
  config?: any;
  onChartClick?: (point: any, event?: any) => void;
}

export default function PlotlyRender({ data, layout, frames, config, onChartClick }: PlotlyRenderProps) {
  // Merge layout options for responsive and modern aesthetics
  const enhancedLayout = {
    ...layout,
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)', // transparent widget background
    plot_bgcolor: 'rgba(0,0,0,0)',  // transparent plot area
    font: {
      family: 'system-ui, -apple-system, sans-serif',
      color: '#a1a1aa', // tailwind zinc-400
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
    // Stylize grid lines and axes to fit the dark theme
    xaxis: {
      gridcolor: '#27272a', // zinc-800
      zerolinecolor: '#3f3f46', // zinc-700
      ...layout?.xaxis,
    },
    yaxis: {
      gridcolor: '#27272a',
      zerolinecolor: '#3f3f46',
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
      />
    </div>
  );
}
