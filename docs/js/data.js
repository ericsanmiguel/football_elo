/**
 * Data loading and caching layer.
 * All JSON files are fetched relative to the site root.
 */

const cache = new Map();

// Detect base path (works on GitHub Pages and local)
const BASE = document.querySelector('base')?.href
    || window.location.pathname.replace(/\/[^/]*$/, '/');

async function fetchJSON(path) {
    if (cache.has(path)) return cache.get(path);
    const resp = await fetch(`${BASE}data/${path}`);
    if (!resp.ok) throw new Error(`Failed to fetch ${path}: ${resp.status}`);
    const data = await resp.json();
    cache.set(path, data);
    return data;
}

export async function getRankings() {
    return fetchJSON('rankings.json');
}

export async function getTeamColors() {
    return fetchJSON('team_colors.json');
}

export async function getTeamHistory(slug) {
    return fetchJSON(`history/${slug}.json`);
}

export async function getHistoryTop20() {
    return fetchJSON('history_top20.json');
}

export async function getTournaments() {
    return fetchJSON('tournaments.json');
}

export async function getTeamFlags() {
    return fetchJSON('team_flags.json');
}
