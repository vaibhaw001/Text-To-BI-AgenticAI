'use client';

import React from 'react';
import dynamic from 'next/dynamic';

// Dynamically import PlotlyRender with ssr: false to prevent NextJS server-side rendering errors
const PlotlyRender = dynamic(() => import('./PlotlyRender'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center text-zinc-500">
      <div className="flex space-x-2 mb-2">
        <div className="h-2 w-2 bg-purple-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="h-2 w-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="h-2 w-2 bg-blue-500 rounded-full animate-bounce"></div>
      </div>
      <span className="text-xs font-medium tracking-wider animate-pulse">LOADING PLOTLY GRAPH...</span>
    </div>
  )
});

interface ChartWidgetProps {
  chartJson: any;
}

export default function ChartWidget({ chartJson }: ChartWidgetProps) {
  if (!chartJson) {
    return (
      <div className="w-full h-full flex items-center justify-center text-zinc-500 text-sm">
        No chart configurations received
      </div>
    );
  }
  
  return (
    <PlotlyRender 
      data={chartJson.data || []} 
      layout={chartJson.layout || {}}
      frames={chartJson.frames}
      config={chartJson.config}
    />
  );
}
