/**
 * 2026 World Cup predictions view — tabbed layout.
 */

import { getTeamFlags } from './data.js';
import { el, flagImg } from './utils.js';
import { renderBracketBuilder } from './bracket.js';

const BASE = document.querySelector('base')?.href
    || window.location.pathname.replace(/\/[^/]*$/, '/');

let cachedWcData = null;
let cachedFlags = null;
let currentTab = 'overview';
// Rankings-table sort state. 'default' = p_winner with a full tiebreaker cascade.
let rankingsSort = { key: 'default', asc: false };

export async function render(container) {
    container.innerHTML = '<div class="loading">Loading World Cup data...</div>';

    const [wcData, flags] = await Promise.all([
        fetch(`${BASE}data/men/worldcup2026.json`).then(r => r.json()),
        getTeamFlags(),
    ]);
    cachedWcData = wcData;
    cachedFlags = flags;

    container.innerHTML = '';

    // Header
    const hero = el('div', { class: 'hero' }, [
        el('h1', { text: '2026 World Cup Predictions' }),
        el('p', { class: 'hero-subtitle', text: 'Based on current Elo ratings \u00b7 10,000 simulations' }),
    ]);
    container.appendChild(hero);

    // Tab bar
    const tabs = el('div', { class: 'wc-tabs' });
    for (const [id, label] of [['overview', 'Overview'], ['groups', 'Groups'], ['bracket', 'Build Your Bracket']]) {
        tabs.appendChild(el('button', {
            class: `wc-tab ${id === currentTab ? 'active' : ''}`,
            text: label,
            'data-tab': id,
            onclick: () => switchTab(id, container),
        }));
    }
    container.appendChild(tabs);

    // Tab content container
    container.appendChild(el('div', { id: 'wc-tab-content' }));

    renderTabContent(currentTab);
}

function switchTab(tab, container) {
    currentTab = tab;
    document.querySelectorAll('.wc-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    renderTabContent(tab);
}

function renderTabContent(tab) {
    const content = document.getElementById('wc-tab-content');
    if (!content) return;
    content.innerHTML = '';

    if (tab === 'overview') {
        content.appendChild(buildRankingsCard(cachedWcData, cachedFlags));
    } else if (tab === 'groups') {
        content.appendChild(el('p', {
            style: 'color:var(--text-tertiary);margin-bottom:20px;font-size:0.9rem',
            text: 'Click a group to see detailed predictions and match-by-match probabilities.',
        }));
        const grid = el('div', { class: 'wc-grid' });
        for (const groupName of Object.keys(cachedWcData.groups).sort()) {
            grid.appendChild(buildGroupCard(groupName, cachedWcData.groups[groupName], cachedFlags));
        }
        content.appendChild(grid);
    } else if (tab === 'bracket') {
        renderBracketBuilder(content, cachedWcData, cachedFlags);
    }
}

const RANKINGS_COLUMNS = [
    { key: 'rank', label: '#', sortable: false },
    { key: 'team', label: 'Team', asc: true, get: (t) => t.team.toLowerCase() },
    { key: 'group', label: 'Grp', asc: true, get: (t) => t.group },
    { key: 'elo_base', label: 'Elo', asc: false, tip: 'Base Elo rating',
      get: (t) => t.elo_base ?? t.rating },
    { key: 'squad_index', label: 'Squad', asc: false,
      tip: 'Squad-strength index (50–100, rescaled across the 48 teams)',
      get: (t) => t.squad_index ?? -Infinity },
    { key: 'combined_index', label: 'Total', asc: false,
      tip: 'Combined Elo + squad index (50–100)',
      get: (t) => t.combined_index },
    { key: 'p_r32', label: 'R32', asc: false, get: (t) => t.p_r32 ?? 0 },
    { key: 'p_r16', label: 'R16', asc: false, get: (t) => t.p_r16 ?? 0 },
    { key: 'p_qf', label: 'QF', asc: false, get: (t) => t.p_qf ?? 0 },
    { key: 'p_sf', label: 'SF', asc: false, get: (t) => t.p_sf ?? 0 },
    { key: 'p_final', label: 'Final', asc: false, get: (t) => t.p_final ?? 0 },
    { key: 'p_winner', label: 'Win', asc: false, get: (t) => t.p_winner ?? 0 },
];

function sortRankings(allTeams) {
    if (rankingsSort.key === 'default') {
        return [...allTeams].sort((a, b) =>
            (b.p_winner ?? 0) - (a.p_winner ?? 0)
            || (b.p_final ?? 0) - (a.p_final ?? 0)
            || (b.p_sf ?? 0) - (a.p_sf ?? 0)
            || (b.p_qf ?? 0) - (a.p_qf ?? 0)
            || (b.p_r16 ?? 0) - (a.p_r16 ?? 0)
            || (b.p_r32 ?? 0) - (a.p_r32 ?? 0)
        );
    }
    const col = RANKINGS_COLUMNS.find(c => c.key === rankingsSort.key);
    if (!col) return [...allTeams];
    const dir = rankingsSort.asc ? 1 : -1;
    return [...allTeams].sort((a, b) => {
        const va = col.get(a);
        const vb = col.get(b);
        if (va < vb) return -1 * dir;
        if (va > vb) return 1 * dir;
        return 0;
    });
}

function buildRankingsCard(wcData, flags) {
    const card = el('div', { class: 'card' });
    card.appendChild(el('h2', { text: 'World Cup Team Rankings' }));

    const allTeams = [];
    for (const [gName, group] of Object.entries(wcData.groups)) {
        for (const t of group.teams) {
            allTeams.push({ ...t, group: gName });
        }
    }
    const sorted = sortRankings(allTeams);

    // Precompute min/max for Elo tinting across the 48 teams
    const elos = allTeams.map(t => t.elo_base ?? t.rating);
    const minElo = Math.min(...elos);
    const maxElo = Math.max(...elos);

    const wrap = el('div', { class: 'rankings-table-wrap', id: 'wc-rankings-wrap' });
    wrap.appendChild(buildRankingsTable(sorted, flags, { minElo, maxElo }));
    card.appendChild(wrap);
    return card;
}

function rerenderRankingsTable() {
    if (!cachedWcData) return;
    const wrap = document.getElementById('wc-rankings-wrap');
    if (!wrap) return;
    const allTeams = [];
    for (const [gName, group] of Object.entries(cachedWcData.groups)) {
        for (const t of group.teams) allTeams.push({ ...t, group: gName });
    }
    const elos = allTeams.map(t => t.elo_base ?? t.rating);
    wrap.innerHTML = '';
    wrap.appendChild(buildRankingsTable(
        sortRankings(allTeams), cachedFlags,
        { minElo: Math.min(...elos), maxElo: Math.max(...elos) }
    ));
}

function buildRankingsTable(sorted, flags, ctx) {
    const table = el('table', { class: 'rankings-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    for (const col of RANKINGS_COLUMNS) {
        const cls = ['rank', 'team', 'group'].includes(col.key) ? '' : 'text-right';
        const isActive = rankingsSort.key === col.key;
        const arrow = isActive ? (rankingsSort.asc ? ' \u25B2' : ' \u25BC') : '';
        const attrs = {
            class: `${cls} ${isActive ? 'sort-active' : ''}`.trim(),
            html: `${col.label}<span class="sort-arrow">${arrow}</span>`,
        };
        if (col.tip) attrs.title = col.tip;
        if (col.sortable !== false) {
            attrs.style = 'cursor:pointer';
            attrs.onclick = () => {
                if (rankingsSort.key === col.key) {
                    rankingsSort.asc = !rankingsSort.asc;
                } else {
                    rankingsSort = { key: col.key, asc: col.asc };
                }
                rerenderRankingsTable();
            };
        }
        headerRow.appendChild(el('th', attrs));
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el('tbody');
    sorted.forEach((t, idx) => {
        const tr = el('tr', {
            style: 'cursor:pointer',
            onclick: () => { window.location.hash = `#/team/${t.slug}`; },
        });

        const rankClass = idx < 3 ? 'rank-cell top3' : 'rank-cell';
        tr.appendChild(el('td', { class: rankClass, text: (idx + 1).toString() }));

        const teamTd = el('td', { class: 'team-cell' });
        const flag = flagImg(flags[t.slug], t.team, 'sm');
        if (flag) { teamTd.appendChild(flag); teamTd.appendChild(document.createTextNode(' ')); }
        teamTd.appendChild(document.createTextNode(t.team));
        tr.appendChild(teamTd);

        tr.appendChild(el('td', { text: t.group, style: 'color:var(--text-tertiary)' }));

        const eloBase = t.elo_base ?? t.rating;
        tr.appendChild(eloCell(eloBase, ctx.minElo, ctx.maxElo));
        tr.appendChild(indexCell(t.squad_index));
        tr.appendChild(indexCell(t.combined_index, true));

        for (const key of ['p_r32', 'p_r16', 'p_qf', 'p_sf', 'p_final', 'p_winner']) {
            const pct = t[key] ?? 0;
            tr.appendChild(pctCell(pct, key === 'p_winner'));
        }

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
}

function eloCell(elo, minElo, maxElo) {
    const intensity = maxElo > minElo
        ? Math.max(0, Math.min(1, (elo - minElo) / (maxElo - minElo)))
        : 0.5;
    const bg = `rgba(93, 143, 255, ${intensity * 0.28})`;
    return el('td', {
        class: 'wc-prob-cell text-right',
        text: Math.round(elo).toString(),
        style: `background:${bg}`,
    });
}

function buildGroupCard(groupName, group, flags) {
    const card = el('div', { class: 'wc-group-card', id: `group-${groupName}` });

    const header = el('div', {
        class: 'wc-group-header',
        style: 'cursor:pointer',
        onclick: () => toggleGroup(groupName),
    });
    header.appendChild(el('span', { text: `Group ${groupName}` }));
    const summary = el('span', { class: 'wc-group-summary' });
    for (const t of group.teams) {
        const flag = flagImg(flags[t.slug], t.team, 'sm');
        if (flag) { flag.title = t.team; summary.appendChild(flag); }
    }
    header.appendChild(summary);
    card.appendChild(header);

    const detail = el('div', { class: 'wc-group-detail', id: `detail-${groupName}`, style: 'display:none' });

    const table = el('table', { class: 'wc-group-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    for (const h of ['', 'Team', 'Elo', '1st', '2nd', '3rd', '4th', 'R32', 'R16', 'QF']) {
        headerRow.appendChild(el('th', { text: h }));
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el('tbody');
    for (const t of group.teams) {
        const tr = el('tr', {
            style: 'cursor:pointer',
            onclick: (e) => { e.stopPropagation(); window.location.hash = `#/team/${t.slug}`; },
        });
        const flagTd = el('td', { class: 'wc-flag-cell' });
        const flag = flagImg(flags[t.slug], t.team, 'sm');
        if (flag) flagTd.appendChild(flag);
        tr.appendChild(flagTd);
        tr.appendChild(el('td', { class: 'wc-team-name', text: t.team }));
        tr.appendChild(el('td', { class: 'wc-rating', text: Math.round(t.rating).toString() }));
        tr.appendChild(probCell(t.p_1st));
        tr.appendChild(probCell(t.p_2nd));
        tr.appendChild(probCell(t.p_3rd));
        tr.appendChild(probCell(t.p_4th, true));
        tr.appendChild(pctCell(t.p_r32 ?? 0));
        tr.appendChild(pctCell(t.p_r16 ?? 0));
        tr.appendChild(pctCell(t.p_qf ?? 0));
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    detail.appendChild(table);

    detail.appendChild(el('div', { class: 'wc-matches-title', text: 'Match Predictions', style: 'margin-top:16px' }));

    for (const m of group.matches) {
        if (m.date) {
            detail.appendChild(el('div', {
                class: 'wc-match-date',
                text: `${m.date}${m.venue ? ' \u2014 ' + m.venue : ''}`,
            }));
        }
        const matchRow = el('div', { class: 'wc-match-row' });
        const homeDiv = el('div', { class: 'wc-match-team wc-match-home' });
        const homeFlag = flagImg(flags[slugify(m.home)], m.home, 'sm');
        if (homeFlag) homeDiv.appendChild(homeFlag);
        homeDiv.appendChild(document.createTextNode(` ${m.home}`));
        if (!m.is_neutral) homeDiv.appendChild(el('span', { class: 'wc-home-badge', text: 'H' }));
        matchRow.appendChild(homeDiv);

        const barContainer = el('div', { class: 'wc-prob-bar' });
        if (m.p_home >= 8) barContainer.appendChild(el('div', { class: 'wc-prob-segment wc-prob-home', style: `width:${m.p_home}%`, text: `${m.p_home}%` }));
        else barContainer.appendChild(el('div', { class: 'wc-prob-segment wc-prob-home', style: `width:${m.p_home}%` }));
        if (m.p_draw >= 8) barContainer.appendChild(el('div', { class: 'wc-prob-segment wc-prob-draw', style: `width:${m.p_draw}%`, text: `${m.p_draw}%` }));
        else barContainer.appendChild(el('div', { class: 'wc-prob-segment wc-prob-draw', style: `width:${m.p_draw}%` }));
        if (m.p_away >= 8) barContainer.appendChild(el('div', { class: 'wc-prob-segment wc-prob-away', style: `width:${m.p_away}%`, text: `${m.p_away}%` }));
        else barContainer.appendChild(el('div', { class: 'wc-prob-segment wc-prob-away', style: `width:${m.p_away}%` }));
        matchRow.appendChild(barContainer);

        const awayDiv = el('div', { class: 'wc-match-team wc-match-away' });
        awayDiv.appendChild(document.createTextNode(`${m.away} `));
        const awayFlag = flagImg(flags[slugify(m.away)], m.away, 'sm');
        if (awayFlag) awayDiv.appendChild(awayFlag);
        matchRow.appendChild(awayDiv);

        detail.appendChild(matchRow);
    }

    card.appendChild(detail);
    return card;
}

function toggleGroup(groupName) {
    const detail = document.getElementById(`detail-${groupName}`);
    if (!detail) return;
    const isOpen = detail.style.display !== 'none';
    document.querySelectorAll('.wc-group-detail').forEach(d => { d.style.display = 'none'; });
    document.querySelectorAll('.wc-group-card').forEach(c => { c.classList.remove('wc-expanded'); });
    if (!isOpen) {
        detail.style.display = 'block';
        document.getElementById(`group-${groupName}`)?.classList.add('wc-expanded');
    }
}

function pctCell(pct, highlight = false) {
    const intensity = Math.min(pct / 30, 1);
    const bg = `rgba(6, 214, 160, ${intensity * 0.35})`;
    return el('td', {
        class: 'wc-prob-cell text-right',
        text: pct > 0 ? `${pct}%` : '-',
        style: pct > 0 ? `background:${bg}${highlight ? ';font-weight:700;color:var(--accent)' : ''}` : 'color:var(--text-tertiary)',
    });
}

function indexCell(value, highlight = false) {
    if (value == null) {
        return el('td', { class: 'wc-prob-cell text-right', text: '-', style: 'color:var(--text-tertiary)' });
    }
    // Rescale 50-100 -> 0-1 for color intensity
    const intensity = Math.max(0, Math.min(1, (value - 50) / 50));
    const bg = `rgba(93, 143, 255, ${intensity * 0.28})`;
    return el('td', {
        class: 'wc-prob-cell text-right',
        text: value.toFixed(1),
        style: `background:${bg}${highlight ? ';font-weight:700' : ''}`,
    });
}

function probCell(pct, isElim = false) {
    const intensity = Math.min(pct / 50, 1) * 0.3;
    const color = isElim ? `rgba(239, 68, 68, ${intensity})` : `rgba(6, 214, 160, ${intensity})`;
    return el('td', {
        class: 'wc-prob-cell',
        text: `${pct}%`,
        style: `background:${color}`,
    });
}

function slugify(name) {
    return name.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().trim().replace(/[^\w\s-]/g, '')
        .replace(/[\s_]+/g, '-').replace(/-+/g, '-');
}
