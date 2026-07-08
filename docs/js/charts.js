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

/**
 * Make a Plotly time-series chart rescale its y-axis to the visible x-window.
 *
 * Plotly's `autorange` is computed once over the full data span, so zooming
 * into a narrow time window (via the rangeslider or an x-drag) leaves the
 * y-axis stretched across decades and the local variation looks flat. This
 * listens for x-range changes and refits the y-axis to just the points inside
 * the current window.
 *
 * @param {HTMLElement} gd      graph div returned by Plotly.newPlot
 * @param {Array<{x:Array,y:Array}>} series  the plotted series (x = dates)
 * @param {boolean} invertY     true for reversed axes (e.g. rank: #1 on top)
 * @param {number} padFrac      fraction of the visible span to pad above/below
 */
export function attachAutoscaleY(gd, series, invertY = false, padFrac = 0.08) {
    if (!gd || !gd.on) return;
    const toMs = (v) => (typeof v === 'number' ? v : new Date(v).getTime());
    // Pre-convert x to timestamps once; y stays as-is.
    const seriesMs = series.map((s) => ({ t: s.x.map(toMs), y: s.y }));

    function rescale() {
        const xa = gd.layout && gd.layout.xaxis;
        if (!xa) return;
        // Current visible x-window (concrete range unless the axis is autoranging).
        let lo = -Infinity, hi = Infinity;
        if (xa.range && !xa.autorange) { lo = toMs(xa.range[0]); hi = toMs(xa.range[1]); }

        let ymin = Infinity, ymax = -Infinity;
        for (const s of seriesMs) {
            for (let i = 0; i < s.y.length; i++) {
                const v = s.y[i];
                if (v == null || Number.isNaN(v)) continue;
                if (s.t[i] < lo || s.t[i] > hi) continue;
                if (v < ymin) ymin = v;
                if (v > ymax) ymax = v;
            }
        }
        if (ymin === Infinity) return; // nothing visible in this window

        const span = ymax - ymin;
        const pad = span > 0 ? span * padFrac : Math.max(1, Math.abs(ymax) * 0.02);
        ymin -= pad; ymax += pad;
        // On a reversed rank axis, don't pad past #1 into 0/negative territory.
        if (invertY && ymin < 0.5) ymin = 0.5;
        const newRange = invertY ? [ymax, ymin] : [ymin, ymax];

        gd._autoY = true;
        Plotly.relayout(gd, { 'yaxis.range': newRange }).then(() => { gd._autoY = false; });
    }

    gd.on('plotly_relayout', (ev) => {
        if (gd._autoY) return; // ignore the relayout we triggered ourselves
        const keys = Object.keys(ev);
        const touchesX = keys.some((k) => k.indexOf('xaxis') === 0);
        // Skip when the user set an explicit y-range (e.g. a box zoom) — respect it.
        const setsYRange = keys.some((k) => k.indexOf('yaxis.range') === 0);
        if (!touchesX || setsYRange) return;
        rescale();
    });

    rescale(); // fit the initial view
}

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
