declare module 'react-plotly.js/factory' {
    import * as React from 'react';
    export default function createPlotlyComponent(plotly: any): React.ComponentType<any>;
}

declare module 'plotly.js-dist-min' {
    const plotly: any;
    export default plotly;
}
