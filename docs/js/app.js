/**
 * SPA router and initialization.
 */

import { render as renderRankings } from './rankings.js';
import { render as renderTeam } from './team.js';
import { render as renderCompare } from './compare.js';
import { render as renderMethodology } from './methodology.js';

const app = document.getElementById('app');

const routes = [
    { pattern: /^#\/team\/(.+)$/, handler: (m) => renderTeam(app, m[1]) },
    { pattern: /^#\/compare\/(.+)\/(.+)$/, handler: (m) => renderCompare(app, m[1], m[2]) },
    { pattern: /^#\/compare\/(.+)$/, handler: (m) => renderCompare(app, m[1]) },
    { pattern: /^#\/compare$/, handler: () => renderCompare(app) },
    { pattern: /^#\/methodology$/, handler: () => renderMethodology(app) },
    { pattern: /^#\/$/, handler: () => renderRankings(app) },
];

function updateActiveNav() {
    const hash = window.location.hash || '#/';
    document.querySelectorAll('.nav-link').forEach(link => {
        const route = link.dataset.route;
        let isActive = false;
        if (route === 'rankings') isActive = hash === '#/' || hash === '';
        else if (route === 'compare') isActive = hash.startsWith('#/compare');
        else if (route === 'history') isActive = hash.startsWith('#/history');
        else if (route === 'methodology') isActive = hash === '#/methodology';
        link.classList.toggle('active', isActive);
    });
}

async function navigate() {
    const hash = window.location.hash || '#/';
    updateActiveNav();

    for (const route of routes) {
        const match = hash.match(route.pattern);
        if (match) {
            try {
                await route.handler(match);
            } catch (err) {
                console.error('Route error:', err);
                app.innerHTML = `<div class="loading">Error loading page. Check console for details.</div>`;
            }
            return;
        }
    }

    // Default: rankings
    try {
        await renderRankings(app);
    } catch (err) {
        console.error('Route error:', err);
        app.innerHTML = `<div class="loading">Error loading page.</div>`;
    }
}

window.addEventListener('hashchange', navigate);
window.addEventListener('DOMContentLoaded', navigate);

// Theme toggle
function initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'dark'); // default dark
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeButton(theme);
}

function updateThemeButton(theme) {
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = theme === 'dark' ? '\u2600' : '\u263D'; // sun / moon
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeButton(next);
    // Re-layout any visible Plotly charts with new theme colors
    requestAnimationFrame(relayoutPlotlyCharts);
}

function relayoutPlotlyCharts() {
    const style = getComputedStyle(document.documentElement);
    const chartBg = style.getPropertyValue('--chart-bg').trim();
    const gridColor = style.getPropertyValue('--chart-grid').trim();
    const textColor = style.getPropertyValue('--text-secondary').trim();
    const bgSecondary = style.getPropertyValue('--bg-secondary').trim();
    const borderColor = style.getPropertyValue('--border').trim();
    const accentColor = style.getPropertyValue('--accent').trim();
    const textPrimary = style.getPropertyValue('--text-primary').trim();

    const update = {
        paper_bgcolor: chartBg,
        plot_bgcolor: chartBg,
        'font.color': textColor,
        'xaxis.gridcolor': gridColor,
        'xaxis.linecolor': gridColor,
        'xaxis.zerolinecolor': gridColor,
        'yaxis.gridcolor': gridColor,
        'yaxis.linecolor': gridColor,
        'yaxis.zerolinecolor': gridColor,
        'hoverlabel.bgcolor': bgSecondary,
        'hoverlabel.bordercolor': accentColor,
        'hoverlabel.font.color': textPrimary,
        'legend.font.color': textColor,
        'xaxis.rangeslider.bgcolor': bgSecondary,
        'xaxis.rangeslider.bordercolor': borderColor,
    };

    // Find all Plotly chart divs and relayout them
    document.querySelectorAll('.chart-container').forEach(div => {
        if (div.data) {  // Plotly attaches .data to rendered charts
            Plotly.relayout(div, update);
        }
    });
}

document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
initTheme();

// Initial load
navigate();
