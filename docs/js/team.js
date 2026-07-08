/**
 * Team detail view — rating history chart, stats, recent matches,
 * chart toggle (Elo/Trend/Ranking), top wins, worst losses.
 */

import { getRankings, getTeamHistory, getTeamColors, getTeamFlags, getGender } from './data.js';
import { CHART_CONFIG, DEFAULT_COLOR, baselineShape, getChartLayout, attachAutoscaleY } from './charts.js';
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

    // Header with flag + stars
    const header = el('div', { class: 'team-header' });
    const flag = flagImg(flagCode, teamInfo.team, 'lg');
    if (flag) header.appendChild(flag);
    header.appendChild(el('h1', { text: teamInfo.team }));
    if (teamData.wc_stars > 0) {
        header.appendChild(el('span', {
            class: 'wc-stars',
            text: '\u2605'.repeat(teamData.wc_stars),
            title: `World Cup wins: ${teamData.wc_wins?.join(', ')}`,
        }));
    }
    header.appendChild(el('span', { class: 'team-rank-badge', text: `#${teamInfo.rank}` }));
    container.appendChild(header);

    // World Cup wins subtitle
    if (teamData.wc_wins?.length > 0) {
        container.appendChild(el('div', {
            class: 'wc-wins-subtitle',
            text: `World Cup champion: ${teamData.wc_wins.join(', ')}`,
        }));
    }

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
            bestRankLabel(teamData)
        ),
        statCard(
            teamData.worst_rank != null ? `#${teamData.worst_rank}` : 'N/A',
            worstRankLabel(teamData)
        ),
        statCard(history.length.toString(), 'Matches'),
        statCard(`${wins}W ${draws}D ${losses}L`, 'Record'),
        ...(teamData.wc_record ? [statCard(
            `${teamData.wc_record.w}W ${teamData.wc_record.d}D ${teamData.wc_record.l}L`,
            'World Cup Record'
        )] : []),
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

    // World Cup History
    const wcSection = buildWorldCupHistory(history, flags);
    if (wcSection) container.appendChild(wcSection);

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

function rankDateLabel(first, last, prefix) {
    if (!first) return prefix;
    if (first === last) return `${prefix}<br>${first}`;
    return `${prefix}<br>First: ${first}<br>Last: ${last}`;
}

function bestRankLabel(data) {
    return rankDateLabel(data.best_rank_first, data.best_rank_last, 'Best Rank');
}

function worstRankLabel(data) {
    return rankDateLabel(data.worst_rank_first, data.worst_rank_last, 'Worst Rank');
}

function statCard(value, label) {
    return el('div', { class: 'stat-card' }, [
        el('div', { class: 'stat-value', text: value }),
        el('div', { class: 'stat-label', html: label }),
    ]);
}

function switchChart(mode) {
    currentChartMode = mode;
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    renderChart(mode);
}

/**
 * Centered rolling mean over a time window (equal weight per point). Mirrors
 * the 365-day smoothing used for the Elo "Trend" so the smoothed rank line has
 * the same character. Dates must be ascending (history is chronological).
 */
function movingAverageByDays(dates, values, windowDays = 365) {
    const ts = dates.map(d => new Date(d).getTime());
    const half = (windowDays * 86400000) / 2;
    const out = new Array(values.length);
    let lo = 0, hi = 0;
    for (let i = 0; i < values.length; i++) {
        while (lo < ts.length && ts[lo] < ts[i] - half) lo++;
        while (hi < ts.length && ts[hi] <= ts[i] + half) hi++;
        let sum = 0, n = 0;
        for (let j = lo; j < hi; j++) { sum += values[j]; n++; }
        out[i] = n ? sum / n : values[i];
    }
    return out;
}

function renderChart(mode) {
    const history = cachedHistory;
    const color = cachedColor;
    const teamName = cachedTeamName;
    if (!history || history.length === 0) return;

    const lineColor = color === '#ffffff' ? '#94a3b8' : color;

    if (mode === 'ranking') {
        // Raw rank (faint, steppy) + a smoothed trend line on top.
        const pts = history.filter(h => h.rk != null);
        const rDates = pts.map(h => h.date);
        const rRaw = pts.map(h => h.rk);
        const rSmooth = movingAverageByDays(rDates, rRaw, 365);
        const rawTrace = {
            x: rDates, y: rRaw, type: 'scatter', mode: 'lines',
            line: { color: lineColor, width: 1, shape: 'hv' }, opacity: 0.3,
            name: 'Rank',
            hovertext: pts.map(h => `${h.date}<br>Rank: #${h.rk}`), hoverinfo: 'text',
        };
        const smoothTrace = {
            x: rDates, y: rSmooth, type: 'scatter', mode: 'lines',
            line: { color: lineColor, width: 2.5 },
            name: 'Trend',
            hovertext: rSmooth.map((v, i) => `${rDates[i]}<br>Smoothed rank: ${v.toFixed(1)}`),
            hoverinfo: 'text',
        };
        renderPlotly([rawTrace, smoothTrace], [{ x: rDates, y: rRaw }], 'Ranking', true, true);
        return;
    }

    const dates = history.map(h => h.date);
    let yData, yTitle, hoverText;
    if (mode === 'trend') {
        yData = history.map(h => h.rs ?? h.ra);
        yTitle = 'Elo Rating (Smoothed)';
        hoverText = history.map(h => `${h.date}<br>Trend: ${h.rs ?? h.ra}`);
    } else {
        yData = history.map(h => h.ra);
        yTitle = 'Elo Rating';
        hoverText = history.map(h => {
            const result = h.ts > h.os ? 'W' : h.ts < h.os ? 'L' : 'D';
            return `${h.date}<br>${result} ${h.ts}-${h.os} vs ${h.opponent}<br>Rating: ${h.ra} (${h.rc >= 0 ? '+' : ''}${h.rc})<br>${h.tournament}`;
        });
    }

    const trace = {
        x: dates, y: yData, type: 'scatter', mode: 'lines',
        line: { color: lineColor, width: 2 },
        name: teamName, hovertext: hoverText, hoverinfo: 'text',
    };
    renderPlotly([trace], [{ x: dates, y: yData }], yTitle, false, false);
}

function renderPlotly(traces, scaleSeries, yTitle, invertY, showLegend) {
    const base = getChartLayout();
    const lastDates = scaleSeries.map(s => s.x[s.x.length - 1]).filter(Boolean).sort();
    const lastDate = lastDates[lastDates.length - 1];

    const layout = {
        ...base,
        showlegend: !!showLegend,
        shapes: invertY ? [] : [baselineShape()],
        xaxis: {
            ...base.xaxis,
            rangeslider: {},
            range: [getGender() === 'men' ? '1900-01-01' : '1990-01-01', lastDate],
        },
        yaxis: {
            ...base.yaxis,
            title: { text: yTitle, font: { size: 12 } },
            autorange: invertY ? 'reversed' : true,
        },
    };

    Plotly.newPlot('team-chart', traces, layout, CHART_CONFIG)
        .then(gd => attachAutoscaleY(gd, scaleSeries, invertY));
}

function buildWorldCupHistory(history, flags) {
    const wcMatches = history.filter(h => h.tournament === 'FIFA World Cup');
    if (wcMatches.length === 0) return null;

    // Group by year (each year = one WC edition)
    const editions = {};
    for (const m of wcMatches) {
        const year = m.date.slice(0, 4);
        if (!editions[year]) editions[year] = [];
        editions[year].push(m);
    }
    const years = Object.keys(editions).sort().reverse();

    const card = el('div', { class: 'card' });
    card.appendChild(el('h2', { text: 'World Cup History' }));

    // Edition buttons
    const btnRow = el('div', { class: 'chart-toggle', style: 'flex-wrap:wrap' });
    for (const year of years) {
        btnRow.appendChild(el('button', {
            class: 'toggle-btn',
            text: year,
            'data-year': year,
            onclick: () => {
                // Toggle active button
                btnRow.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                const clicked = btnRow.querySelector(`[data-year="${year}"]`);
                if (clicked) clicked.classList.add('active');
                // Show table
                const tableDiv = document.getElementById('wc-edition-table');
                if (tableDiv) {
                    tableDiv.innerHTML = '';
                    tableDiv.appendChild(buildWCEditionTable(editions[year], flags));
                }
            },
        }));
    }
    card.appendChild(btnRow);

    // Table container
    card.appendChild(el('div', { id: 'wc-edition-table', style: 'margin-top:16px' }));

    return card;
}

function buildWCEditionTable(matches, flags) {
    const table = el('table', { class: 'matches-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    for (const h of ['Date', 'Opponent', '', 'Score', 'Elo', 'Rank', 'Opp Elo', 'Opp Rank', 'Change']) {
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

        const flagTd = el('td');
        const f = flagImg(flags[slugify(m.opponent)], m.opponent, 'sm');
        if (f) flagTd.appendChild(f);
        tr.appendChild(flagTd);

        tr.appendChild(el('td', { text: `${result} ${m.ts}-${m.os}` }));
        tr.appendChild(el('td', { text: formatRating(m.rb) }));
        tr.appendChild(el('td', { text: m.rk != null ? `#${m.rk}` : '-' }));
        tr.appendChild(el('td', { text: m.orb != null ? formatRating(m.orb) : '-' }));
        tr.appendChild(el('td', { text: m.ork != null ? `#${m.ork}` : '-' }));
        tr.appendChild(el('td', {
            class: changeClass(m.rc),
            text: formatChange(m.rc),
        }));
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
}

function slugify(name) {
    return name.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().trim().replace(/[^\w\s-]/g, '')
        .replace(/[\s_]+/g, '-').replace(/-+/g, '-');
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
