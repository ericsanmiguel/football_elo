/**
 * Data loading and caching layer.
 * Supports gender switching (men/women) with separate data directories.
 */

const cache = new Map();
let currentGender = localStorage.getItem('gender') || 'men';

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

/** Gender-specific data path */
function gp(file) {
    return `${currentGender}/${file}`;
}

export function getGender() { return currentGender; }

export function setGender(g) {
    if (g === currentGender) return;
    currentGender = g;
    localStorage.setItem('gender', g);
    cache.clear();  // Clear all cached data on gender switch
}

// Gender-specific data
export async function getRankings() { return fetchJSON(gp('rankings.json')); }
export async function getTeamHistory(slug) { return fetchJSON(gp(`history/${slug}.json`)); }
export async function getHistoryTop20() { return fetchJSON(gp('history_top20.json')); }
export async function getTournaments() { return fetchJSON(gp('tournaments.json')); }
export async function getHistoricalRankings() { return fetchJSON(gp('historical_rankings.json')); }

// Shared data (same for men and women)
export async function getTeamColors() { return fetchJSON('team_colors.json'); }
export async function getTeamFlags() { return fetchJSON('team_flags.json'); }
