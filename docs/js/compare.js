/**
 * Compare teams view — overlay multiple team histories on one chart.
 */

import { getRankings, getTeamHistory, getTeamColors } from './data.js';
import { getChartLayout, CHART_CONFIG, DEFAULT_COLOR, baselineShape } from './charts.js';
import { el, formatRating } from './utils.js';

let selectedSlugs = [];
let allTeams = [];
let colors = {};

export async function render(container, ...initialSlugs) {
    container.innerHTML = '<div class="loading">Loading...</div>';

    const [rankings, teamColors] = await Promise.all([
        getRankings(),
        getTeamColors(),
    ]);
    allTeams = rankings.teams;
    colors = teamColors;
    selectedSlugs = initialSlugs.filter(s => s && allTeams.some(t => t.slug === s));

    container.innerHTML = '';

    // Title
    container.appendChild(el('a', { class: 'back-link', href: '#/', html: '&larr; Back to Rankings' }));
    container.appendChild(el('h1', {
        class: 'team-header',
        html: '<h1 style="font-family:var(--font-display);font-weight:800;font-size:2.2rem;text-transform:uppercase">Compare Teams</h1>',
    }));

    // Team selector
    const selectorCard = el('div', { class: 'card' });
    const searchRow = el('div', { class: 'filter-bar' });

    const searchInput = el('input', {
        class: 'search-input',
        type: 'text',
        placeholder: 'Search and add a team (up to 5)...',
    });
    searchRow.appendChild(searchInput);
    selectorCard.appendChild(searchRow);

    // Dropdown for search results
    const dropdown = el('div', {
        class: 'search-dropdown',
        style: 'position:relative;',
    });
    const dropdownList = el('div', {
        style: `
            position:absolute; top:0; left:0; right:0; z-index:50;
            background:var(--bg-surface); border:1px solid var(--border);
            border-radius:8px; max-height:200px; overflow-y:auto; display:none;
        `,
    });
    dropdown.appendChild(dropdownList);
    selectorCard.appendChild(dropdown);

    // Chips container
    const chipsContainer = el('div', { class: 'team-chips', id: 'team-chips' });
    selectorCard.appendChild(chipsContainer);
    container.appendChild(selectorCard);

    // Chart
    const chartCard = el('div', { class: 'card' }, [
        el('h2', { text: 'Rating History' }),
        el('div', { class: 'chart-container', id: 'compare-chart' }),
    ]);
    container.appendChild(chartCard);

    // Stats comparison
    const statsCard = el('div', { class: 'card', id: 'compare-stats' });
    container.appendChild(statsCard);

    // Wire up search
    searchInput.addEventListener('input', () => {
        const q = searchInput.value.toLowerCase();
        if (q.length < 1) { dropdownList.style.display = 'none'; return; }
        const matches = allTeams
            .filter(t => t.team.toLowerCase().includes(q) && !selectedSlugs.includes(t.slug))
            .slice(0, 8);
        dropdownList.innerHTML = '';
        if (matches.length === 0) { dropdownList.style.display = 'none'; return; }
        for (const t of matches) {
            const item = el('div', {
                text: `${t.team} (#${t.rank} — ${formatRating(t.rating)})`,
                style: `padding:10px 14px; cursor:pointer; color:var(--text-primary);
                        font-size:0.9rem; border-bottom:1px solid var(--border);`,
                onclick: () => {
                    if (selectedSlugs.length >= 5) return;
                    selectedSlugs.push(t.slug);
                    searchInput.value = '';
                    dropdownList.style.display = 'none';
                    updateView();
                },
                onmouseenter: (e) => { e.target.style.background = 'var(--bg-tertiary)'; },
                onmouseleave: (e) => { e.target.style.background = 'transparent'; },
            });
            dropdownList.appendChild(item);
        }
        dropdownList.style.display = 'block';
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!selectorCard.contains(e.target)) dropdownList.style.display = 'none';
    });

    // Initial render
    if (selectedSlugs.length > 0) updateView();
    else renderEmptyChart();
}

async function updateView() {
    renderChips();
    await renderCompareChart();
    renderStats();
}

function renderChips() {
    const container = document.getElementById('team-chips');
    if (!container) return;
    container.innerHTML = '';
    for (const slug of selectedSlugs) {
        const team = allTeams.find(t => t.slug === slug);
        if (!team) continue;
        const chip = el('div', { class: 'team-chip' }, [
            document.createTextNode(team.team),
            el('span', {
                class: 'team-chip-remove',
                text: '\u00d7',
                onclick: (e) => {
                    e.stopPropagation();
                    selectedSlugs = selectedSlugs.filter(s => s !== slug);
                    updateView();
                },
            }),
        ]);
        container.appendChild(chip);
    }
}

async function renderCompareChart() {
    if (selectedSlugs.length === 0) { renderEmptyChart(); return; }

    const traces = [];
    for (const slug of selectedSlugs) {
        const data = await getTeamHistory(slug);
        const team = allTeams.find(t => t.slug === slug);
        const color = colors[slug] || DEFAULT_COLOR;
        traces.push({
            x: data.history.map(h => h.date),
            y: data.history.map(h => h.ra),
            type: 'scatter',
            mode: 'lines',
            name: team?.team || slug,
            line: { color: color === '#ffffff' ? '#94a3b8' : color, width: 2 },
        });
    }

    const layout = {
        ...getChartLayout(),
        shapes: [baselineShape()],
        xaxis: {
            ...getChartLayout().xaxis,
            range: ['1990-01-01', undefined],
        },
    };

    Plotly.newPlot('compare-chart', traces, layout, CHART_CONFIG);
}

function renderEmptyChart() {
    const chartEl = document.getElementById('compare-chart');
    if (chartEl) chartEl.innerHTML = '<p style="text-align:center;color:var(--text-tertiary);padding:60px 0">Select teams above to compare their rating histories.</p>';
}

function renderStats() {
    const container = document.getElementById('compare-stats');
    if (!container) return;
    if (selectedSlugs.length === 0) { container.innerHTML = ''; return; }

    const header = el('h2', { text: 'Stats Comparison' });

    const table = el('table', { class: 'matches-table' });
    const thead = el('thead');
    const tr = el('tr');
    for (const h of ['Team', 'Rank', 'Rating', 'Peak', 'Matches']) {
        tr.appendChild(el('th', { text: h }));
    }
    thead.appendChild(tr);
    table.appendChild(thead);

    const tbody = el('tbody');
    for (const slug of selectedSlugs) {
        const t = allTeams.find(t => t.slug === slug);
        if (!t) continue;
        const row = el('tr');
        row.appendChild(el('td', { text: t.team, style: 'color:var(--text-primary);font-weight:500' }));
        row.appendChild(el('td', { text: `#${t.rank}` }));
        row.appendChild(el('td', { text: formatRating(t.rating) }));
        row.appendChild(el('td', { text: formatRating(t.peak_rating) }));
        row.appendChild(el('td', { text: t.matches_played.toString() }));
        tbody.appendChild(row);
    }
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(header);
    container.appendChild(table);
}
