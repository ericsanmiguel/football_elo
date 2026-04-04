/**
 * Team detail view — rating history chart, stats, recent matches,
 * chart toggle (Elo/Trend/Ranking), top wins, worst losses.
 */

import { getRankings, getTeamHistory, getTeamColors, getTeamFlags } from './data.js';
import { CHART_CONFIG, DEFAULT_COLOR, baselineShape, getChartLayout } from './charts.js';
import { el, formatRating, formatChange, changeClass, flagImg } from './utils.js';

let currentChartMode = 'elo';
let cachedHistory = null;
let cachedColor = null;
let cachedTeamName = null;

export async function render(container, slug) {
    container.innerHTML = '<div class="loading">Loading team data...</div>';

    const [rankings, teamData, colors, flags] = await Promise.all([
        getRankings(),
        getTeamHistory(slug),
        getTeamColors(),
        getTeamFlags(),
    ]);

    const teamInfo = rankings.teams.find(t => t.slug === slug);
    if (!teamInfo) {
        container.innerHTML = '<p>Team not found.</p>';
        return;
    }

    const history = teamData.history;
    const color = colors[slug] || DEFAULT_COLOR;
    const flagCode = flags[slug];
    cachedHistory = history;
    cachedColor = color;
    cachedTeamName = teamInfo.team;
    currentChartMode = 'elo';

    container.innerHTML = '';

    // Back link
    container.appendChild(el('a', { class: 'back-link', href: '#/', html: '&larr; Back to Rankings' }));

    // Header with flag
    const header = el('div', { class: 'team-header' });
    const flag = flagImg(flagCode, teamInfo.team, 'lg');
    if (flag) header.appendChild(flag);
    header.appendChild(el('h1', { text: teamInfo.team }));
    header.appendChild(el('span', { class: 'team-rank-badge', text: `#${teamInfo.rank}` }));
    container.appendChild(header);

    // Big rating
    const lastChange = history.length > 0 ? history[history.length - 1].rc : 0;
    const ratingDiv = el('div', { class: 'team-rating-big' }, [
        document.createTextNode(formatRating(teamInfo.rating)),
        el('span', {
            class: `team-rating-change ${changeClass(lastChange)}`,
            text: formatChange(lastChange),
        }),
    ]);
    container.appendChild(ratingDiv);

    // Stats cards (6 cards: peak, lowest, best rank, worst rank, matches, record)
    const peakRating = Math.max(...history.map(h => h.ra));
    const peakDate = history.find(h => h.ra === peakRating)?.date || '';
    const lowRating = Math.min(...history.map(h => h.ra));
    const wins = history.filter(h => h.ts > h.os).length;
    const draws = history.filter(h => h.ts === h.os).length;
    const losses = history.filter(h => h.ts < h.os).length;

    const statsRow = el('div', { class: 'stat-cards' }, [
        statCard(formatRating(peakRating), `Peak (${peakDate})`),
        statCard(formatRating(lowRating), 'Lowest Rating'),
        statCard(
            teamData.best_rank != null ? `#${teamData.best_rank}` : 'N/A',
            teamData.best_rank_date ? `Best Rank (${teamData.best_rank_date})` : 'Best Rank'
        ),
        statCard(
            teamData.worst_rank != null ? `#${teamData.worst_rank}` : 'N/A',
            teamData.worst_rank_date ? `Worst Rank (${teamData.worst_rank_date})` : 'Worst Rank'
        ),
        statCard(history.length.toString(), 'Matches'),
        statCard(`${wins}W ${draws}D ${losses}L`, 'Record'),
    ]);
    container.appendChild(statsRow);

    // Chart toggle + chart
    const chartCard = el('div', { class: 'card' });
    const toggleRow = el('div', { class: 'chart-toggle' });
    for (const [mode, label] of [['elo', 'Elo Rating'], ['trend', 'Trend'], ['ranking', 'Ranking']]) {
        const btn = el('button', {
            class: `toggle-btn ${mode === 'elo' ? 'active' : ''}`,
            text: label,
            'data-mode': mode,
            onclick: () => switchChart(mode),
        });
        toggleRow.appendChild(btn);
    }
    chartCard.appendChild(toggleRow);
    chartCard.appendChild(el('div', { class: 'chart-container', id: 'team-chart' }));
    container.appendChild(chartCard);

    // Top 5 wins and worst 5 losses
    if (teamData.top_wins?.length) {
        container.appendChild(buildHighlightTable('Top Results (by Elo gained)', teamData.top_wins));
    }
    if (teamData.worst_losses?.length) {
        container.appendChild(buildHighlightTable('Worst Results (by Elo lost)', teamData.worst_losses));
    }

    // Recent matches
    const matchesCard = el('div', { class: 'card' }, [
        el('h2', { text: 'Recent Matches' }),
        buildMatchesTable(history.slice(-20).reverse()),
    ]);
    container.appendChild(matchesCard);

    // Compare button
    container.appendChild(el('a', {
        href: `#/compare/${slug}`,
        class: 'back-link',
        text: 'Compare with other teams \u2192',
    }));

    // Render initial chart
    renderChart('elo');
}

function statCard(value, label) {
    return el('div', { class: 'stat-card' }, [
        el('div', { class: 'stat-value', text: value }),
        el('div', { class: 'stat-label', text: label }),
    ]);
}

function switchChart(mode) {
    currentChartMode = mode;
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    renderChart(mode);
}

function renderChart(mode) {
    const history = cachedHistory;
    const color = cachedColor;
    const teamName = cachedTeamName;
    if (!history || history.length === 0) return;

    const dates = history.map(h => h.date);
    let yData, yTitle, hoverText, invertY = false;

    if (mode === 'elo') {
        yData = history.map(h => h.ra);
        yTitle = 'Elo Rating';
        hoverText = history.map(h => {
            const result = h.ts > h.os ? 'W' : h.ts < h.os ? 'L' : 'D';
            return `${h.date}<br>${result} ${h.ts}-${h.os} vs ${h.opponent}<br>Rating: ${h.ra} (${h.rc >= 0 ? '+' : ''}${h.rc})<br>${h.tournament}`;
        });
    } else if (mode === 'trend') {
        yData = history.map(h => h.rs ?? h.ra);
        yTitle = 'Elo Rating (Smoothed)';
        hoverText = history.map(h => `${h.date}<br>Trend: ${h.rs ?? h.ra}`);
    } else {
        yData = history.filter(h => h.rk != null).map(h => h.rk);
        const rankDates = history.filter(h => h.rk != null).map(h => h.date);
        yTitle = 'Ranking';
        invertY = true;
        hoverText = history.filter(h => h.rk != null).map(h => `${h.date}<br>Rank: #${h.rk}`);
        // Use rankDates for x-axis
        return renderPlotly(rankDates, yData, yTitle, hoverText, color, teamName, invertY);
    }

    renderPlotly(dates, yData, yTitle, hoverText, color, teamName, invertY);
}

function renderPlotly(dates, yData, yTitle, hoverText, color, teamName, invertY) {
    const trace = {
        x: dates,
        y: yData,
        type: 'scatter',
        mode: 'lines',
        line: { color: color === '#ffffff' ? '#94a3b8' : color, width: 2 },
        name: teamName,
        hovertext: hoverText,
        hoverinfo: 'text',
    };

    const layout = {
        ...getChartLayout(),
        showlegend: false,
        shapes: invertY ? [] : [baselineShape()],
        xaxis: {
            ...getChartLayout().xaxis,
            rangeslider: {},
            range: ['1990-01-01', dates[dates.length - 1]],
        },
        yaxis: {
            ...getChartLayout().yaxis,
            title: { text: yTitle, font: { size: 12 } },
            autorange: invertY ? 'reversed' : true,
        },
    };

    Plotly.newPlot('team-chart', [trace], layout, CHART_CONFIG);
}

function buildHighlightTable(title, records) {
    const card = el('div', { class: 'card' }, [el('h2', { text: title })]);
    const table = el('table', { class: 'matches-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    for (const h of ['Date', 'Opponent', 'Score', 'Tournament', 'Elo Change']) {
        headerRow.appendChild(el('th', { text: h }));
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el('tbody');
    for (const m of records) {
        const result = m.ts > m.os ? 'W' : m.ts < m.os ? 'L' : 'D';
        const tr = el('tr');
        tr.appendChild(el('td', { text: m.date }));
        tr.appendChild(el('td', { text: m.opponent }));
        tr.appendChild(el('td', { text: `${result} ${m.ts}-${m.os}` }));
        tr.appendChild(el('td', { text: m.tournament }));
        tr.appendChild(el('td', {
            class: changeClass(m.rc),
            text: formatChange(m.rc),
        }));
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    card.appendChild(table);
    return card;
}

function buildMatchesTable(matches) {
    const table = el('table', { class: 'matches-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    for (const h of ['Date', 'Opponent', 'Score', 'Tournament', 'Change', 'Rating']) {
        headerRow.appendChild(el('th', { text: h }));
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el('tbody');
    for (const m of matches) {
        const result = m.ts > m.os ? 'W' : m.ts < m.os ? 'L' : 'D';
        const tr = el('tr');
        tr.appendChild(el('td', { text: m.date }));
        tr.appendChild(el('td', { text: m.opponent }));
        tr.appendChild(el('td', { text: `${result} ${m.ts}-${m.os}` }));
        tr.appendChild(el('td', { text: m.tournament }));
        tr.appendChild(el('td', {
            class: changeClass(m.rc),
            text: formatChange(m.rc),
        }));
        tr.appendChild(el('td', { text: formatRating(m.ra) }));
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
}
