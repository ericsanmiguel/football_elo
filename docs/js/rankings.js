/**
 * Rankings table view — the home page.
 */

import { getRankings, getTeamFlags, getGender } from './data.js';
import { el, formatRating, formatChange, changeClass, flagImg } from './utils.js';

let currentSort = { key: 'rank', asc: true };
let allTeams = [];
let filteredTeams = [];
let flags = {};

export async function render(container) {
    const [data, flagsData] = await Promise.all([getRankings(), getTeamFlags()]);
    flags = flagsData;
    allTeams = data.teams;
    filteredTeams = [...allTeams];

    container.innerHTML = '';

    // Hero
    const hero = el('div', { class: 'hero' }, [
        el('h1', { text: `${getGender() === 'men' ? "Men's" : "Women's"} International Football Elo Ratings` }),
        el('p', { class: 'hero-subtitle', text: `Rankings as of ${data.last_updated}` }),
    ]);
    container.appendChild(hero);

    // Stat cards
    const top = allTeams[0];
    const stats = el('div', { class: 'stat-cards' }, [
        statCard(top.team, '#1 Rated'),
        statCard(formatRating(top.rating), 'Top Rating'),
        statCard(allTeams.length.toString(), 'Teams Ranked'),
        statCard('11,000+', 'Matches'),
    ]);
    container.appendChild(stats);

    // Filter bar
    const filterBar = el('div', { class: 'filter-bar' }, [
        el('input', {
            class: 'search-input',
            type: 'text',
            placeholder: 'Search teams...',
            oninput: (e) => onSearch(e.target.value),
        }),
        createTopNSelect(),
    ]);
    container.appendChild(filterBar);

    // Table
    const tableWrap = el('div', { class: 'rankings-table-wrap' });
    tableWrap.appendChild(buildTable(filteredTeams));
    container.appendChild(tableWrap);

    // Footer update
    const footerEl = document.getElementById('footer-updated');
    if (footerEl) footerEl.textContent = `Last updated: ${data.last_updated}`;
}

function statCard(value, label) {
    return el('div', { class: 'stat-card' }, [
        el('div', { class: 'stat-value', text: value }),
        el('div', { class: 'stat-label', text: label }),
    ]);
}

function createTopNSelect() {
    const select = el('select', { class: 'filter-select', onchange: (e) => onTopN(e.target.value) });
    for (const n of [20, 50, 100, 'All']) {
        const opt = el('option', { value: n.toString(), text: `Top ${n}` });
        if (n === 50) opt.selected = true;
        select.appendChild(opt);
    }
    return select;
}

let topN = 50;
let searchQuery = '';

function onSearch(query) {
    searchQuery = query.toLowerCase();
    applyFilters();
}

function onTopN(val) {
    topN = val === 'All' ? Infinity : parseInt(val);
    applyFilters();
}

function applyFilters() {
    filteredTeams = allTeams.filter(t =>
        t.team.toLowerCase().includes(searchQuery)
    ).slice(0, topN);
    rerenderTable();
}

function rerenderTable() {
    const wrap = document.querySelector('.rankings-table-wrap');
    if (!wrap) return;
    wrap.innerHTML = '';
    wrap.appendChild(buildTable(filteredTeams));
}

function buildTable(teams) {
    const sorted = sortTeams(teams);

    const table = el('table', { class: 'rankings-table' });

    // Header
    const thead = el('thead');
    const headerRow = el('tr');
    const columns = [
        { key: 'rank', label: '#', class: '' },
        { key: 'team', label: 'Team', class: '' },
        { key: 'rating', label: 'Rating', class: 'text-right' },
        { key: 'rating_change', label: 'Change', class: 'text-right' },
        { key: 'peak_rating', label: 'Peak', class: 'text-right' },
        { key: 'matches_played', label: 'Matches', class: 'text-right' },
    ];

    for (const col of columns) {
        const isActive = currentSort.key === col.key;
        const arrow = isActive ? (currentSort.asc ? ' \u25B2' : ' \u25BC') : '';
        const th = el('th', {
            class: `${col.class} ${isActive ? 'sort-active' : ''}`,
            html: `${col.label}<span class="sort-arrow">${arrow}</span>`,
            onclick: () => {
                if (currentSort.key === col.key) {
                    currentSort.asc = !currentSort.asc;
                } else {
                    currentSort = { key: col.key, asc: col.key === 'rank' || col.key === 'team' };
                }
                rerenderTable();
            },
        });
        headerRow.appendChild(th);
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = el('tbody');
    for (const t of sorted) {
        const tr = el('tr', {
            onclick: () => { window.location.hash = `#/team/${t.slug}`; },
        });

        const rankClass = t.rank <= 3 ? 'rank-cell top3' : 'rank-cell';
        tr.appendChild(el('td', { class: rankClass, text: t.rank.toString() }));
        const teamTd = el('td', { class: 'team-cell' });
        const flag = flagImg(flags[t.slug], t.team, 'sm');
        if (flag) { teamTd.appendChild(flag); teamTd.appendChild(document.createTextNode(' ')); }
        teamTd.appendChild(document.createTextNode(t.team));
        tr.appendChild(teamTd);
        tr.appendChild(el('td', { class: 'rating-cell text-right', text: formatRating(t.rating) }));

        const chg = el('td', {
            class: `change-cell text-right ${changeClass(t.rating_change)}`,
            text: formatChange(t.rating_change),
        });
        tr.appendChild(chg);

        tr.appendChild(el('td', { class: 'text-right', text: formatRating(t.peak_rating) }));
        tr.appendChild(el('td', { class: 'text-right', text: t.matches_played.toString() }));

        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
}

function sortTeams(teams) {
    const { key, asc } = currentSort;
    return [...teams].sort((a, b) => {
        let va = a[key], vb = b[key];
        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        if (va < vb) return asc ? -1 : 1;
        if (va > vb) return asc ? 1 : -1;
        return 0;
    });
}
