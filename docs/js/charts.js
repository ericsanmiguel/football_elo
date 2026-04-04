/**
 * Shared Plotly chart configuration and helpers.
 * Supports dynamic theming via CSS custom properties.
 */

/** Read a CSS custom property value from :root */
function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Build chart layout using current theme colors */
export function getChartLayout() {
    const chartBg = cssVar('--chart-bg') || '#0f172a';
    const gridColor = cssVar('--chart-grid') || '#1e293b';
    const textColor = cssVar('--text-secondary') || '#94a3b8';
    const bgSecondary = cssVar('--bg-secondary') || '#111827';
    const borderColor = cssVar('--border') || '#1e293b';
    const accentColor = cssVar('--accent') || '#06d6a0';
    const textPrimary = cssVar('--text-primary') || '#f1f5f9';

    return {
        paper_bgcolor: chartBg,
        plot_bgcolor: chartBg,
        font: { family: 'Inter, sans-serif', color: textColor, size: 12 },
        xaxis: {
            gridcolor: gridColor,
            linecolor: gridColor,
            zerolinecolor: gridColor,
            tickfont: { size: 11 },
        },
        yaxis: {
            gridcolor: gridColor,
            linecolor: gridColor,
            zerolinecolor: gridColor,
            tickfont: { size: 11 },
            title: { text: 'Elo Rating', font: { size: 12 } },
        },
        margin: { l: 55, r: 20, t: 40, b: 50 },
        hoverlabel: {
            bgcolor: bgSecondary,
            bordercolor: accentColor,
            font: { color: textPrimary, size: 13 },
        },
        legend: {
            bgcolor: 'rgba(0,0,0,0)',
            font: { color: textColor, size: 11 },
        },
        hovermode: 'x unified',
    };
}

export const CHART_CONFIG = {
    displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
    displaylogo: false,
    responsive: true,
};

/** Default team color when not in the color map */
export const DEFAULT_COLOR = '#06d6a0';

/** Baseline rating line shape */
export function baselineShape(y = 1500) {
    const gridColor = cssVar('--chart-grid') || '#334155';
    return {
        type: 'line',
        x0: 0, x1: 1, xref: 'paper',
        y0: y, y1: y, yref: 'y',
        line: { color: gridColor, width: 1, dash: 'dash' },
    };
}
