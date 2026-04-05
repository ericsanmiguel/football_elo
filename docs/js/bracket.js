/**
 * World Cup Bracket Builder — user predicts scores and picks knockout winners.
 */

import { el, flagImg } from './utils.js';

// ===== Constants (ported from worldcup.py) =====

const GROUPS = {
    A: ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    B: ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    C: ["Brazil", "Morocco", "Haiti", "Scotland"],
    D: ["United States", "Paraguay", "Australia", "Turkey"],
    E: ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    F: ["Netherlands", "Japan", "Sweden", "Tunisia"],
    G: ["Belgium", "Egypt", "Iran", "New Zealand"],
    H: ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    I: ["France", "Senegal", "Iraq", "Norway"],
    J: ["Argentina", "Algeria", "Austria", "Jordan"],
    K: ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    L: ["England", "Croatia", "Ghana", "Panama"],
};

const SCHEDULE = {
    A: [[0,1,"Jun 11","Mexico City"],[2,3,"Jun 11","Guadalajara"],[3,1,"Jun 18","Atlanta"],[0,2,"Jun 18","Guadalajara"],[3,0,"Jun 24","Mexico City"],[1,2,"Jun 24","Guadalajara"]],
    B: [[0,1,"Jun 12","Toronto"],[2,3,"Jun 13","Santa Clara"],[3,1,"Jun 18","Inglewood"],[0,2,"Jun 18","Vancouver"],[3,0,"Jun 24","Vancouver"],[1,2,"Jun 24","Seattle"]],
    C: [[0,1,"Jun 13","East Rutherford"],[2,3,"Jun 13","Foxborough"],[3,1,"Jun 19","Foxborough"],[0,2,"Jun 19","Philadelphia"],[3,0,"Jun 24","Miami"],[1,2,"Jun 24","Atlanta"]],
    D: [[0,1,"Jun 12","Inglewood"],[2,3,"Jun 13","Vancouver"],[0,2,"Jun 19","Seattle"],[3,1,"Jun 19","Santa Clara"],[3,0,"Jun 25","Inglewood"],[1,2,"Jun 25","Santa Clara"]],
    E: [[0,1,"Jun 14","Houston"],[2,3,"Jun 14","Philadelphia"],[0,2,"Jun 20","Toronto"],[3,1,"Jun 20","Kansas City"],[3,0,"Jun 25","East Rutherford"],[1,2,"Jun 25","Philadelphia"]],
    F: [[0,1,"Jun 14","Arlington"],[2,3,"Jun 14","Guadalajara"],[0,2,"Jun 20","Houston"],[3,1,"Jun 20","Guadalajara"],[1,2,"Jun 25","Arlington"],[3,0,"Jun 25","Kansas City"]],
    G: [[0,1,"Jun 15","Seattle"],[2,3,"Jun 15","Inglewood"],[0,2,"Jun 21","Inglewood"],[3,1,"Jun 21","Vancouver"],[1,2,"Jun 26","Seattle"],[3,0,"Jun 26","Vancouver"]],
    H: [[0,1,"Jun 15","Atlanta"],[2,3,"Jun 15","Miami"],[0,2,"Jun 21","Atlanta"],[3,1,"Jun 21","Miami"],[1,2,"Jun 26","Houston"],[3,0,"Jun 26","Guadalajara"]],
    I: [[0,1,"Jun 16","East Rutherford"],[2,3,"Jun 16","Foxborough"],[0,2,"Jun 22","Philadelphia"],[3,1,"Jun 22","East Rutherford"],[3,0,"Jun 26","Foxborough"],[1,2,"Jun 26","Toronto"]],
    J: [[0,1,"Jun 16","Kansas City"],[2,3,"Jun 16","Santa Clara"],[0,2,"Jun 22","Arlington"],[3,1,"Jun 22","Santa Clara"],[1,2,"Jun 27","Kansas City"],[3,0,"Jun 27","Arlington"]],
    K: [[0,1,"Jun 17","Houston"],[2,3,"Jun 17","Mexico City"],[0,2,"Jun 23","Houston"],[3,1,"Jun 23","Guadalajara"],[3,0,"Jun 27","Miami"],[1,2,"Jun 27","Atlanta"]],
    L: [[0,1,"Jun 17","Arlington"],[2,3,"Jun 17","Toronto"],[0,2,"Jun 23","Foxborough"],[3,1,"Jun 23","Toronto"],[3,0,"Jun 27","East Rutherford"],[1,2,"Jun 27","Philadelphia"]],
};

const R32_BRACKET = [
    ["2A","2B"],["1E","3"],["1F","2C"],["1C","2F"],
    ["1I","3"],["2E","2I"],["1A","3"],["1L","3"],
    ["1D","3"],["1G","3"],["2K","2L"],["1H","2J"],
    ["1B","3"],["1J","2H"],["1K","3"],["2D","2G"],
];

const THIRD_PLACE_SLOTS = [1, 4, 6, 7, 8, 9, 12, 14];
const THIRD_PLACE_OPPONENTS = ["E", "I", "A", "L", "D", "G", "B", "K"];

const ROUND_NAMES = { r32: "Round of 32", r16: "Round of 16", qf: "Quarterfinals", sf: "Semifinals", final: "Final" };
const ROUND_ORDER = ["r32", "r16", "qf", "sf", "final"];
const STORAGE_KEY = "wc2026-bracket";

// ===== State =====

let state = { scores: {}, knockoutPicks: { r32: [], r16: [], qf: [], sf: [], final: [] } };
let flags = {};
let containerRef = null;
let teamRatings = {};  // team name -> Elo rating from JSON
let cachedWcData = null;  // preserve across re-renders

// ===== Slugify =====

function slugify(name) {
    return name.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().trim().replace(/[^\w\s-]/g, '')
        .replace(/[\s_]+/g, '-').replace(/-+/g, '-');
}

// ===== Persistence =====

function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ scores: state.scores, knockoutPicks: state.knockoutPicks, v: 1 })); } catch {}
}

function loadState() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (saved.v !== 1) return;
        state.scores = saved.scores || {};
        state.knockoutPicks = saved.knockoutPicks || { r32: [], r16: [], qf: [], sf: [], final: [] };
    } catch {}
}

// ===== Simulation =====

function eloExpected(ratingA, ratingB) {
    return 1.0 / (Math.pow(10, -(ratingA - ratingB) / 400) + 1.0);
}

function simMatchProbs(ratingA, ratingB) {
    const we = eloExpected(ratingA, ratingB);
    let pDraw = Math.max(0, 0.38 - 0.38 * Math.pow(we - 0.5, 2) / 0.25);
    pDraw = Math.min(pDraw, 0.38);
    let pA = Math.max(0, we - 0.5 * pDraw);
    let pB = Math.max(0, 1 - we - 0.5 * pDraw);
    const total = pA + pDraw + pB;
    return [pA / total, pDraw / total, pB / total];
}

function simRandomScore(pA, pDraw, pB) {
    const r = Math.random();
    if (r < pA) {
        // Home win — random scoreline like 2-1, 1-0, 3-1
        const homeGoals = 1 + Math.floor(Math.random() * 3);
        const awayGoals = Math.floor(Math.random() * homeGoals);
        return [homeGoals, awayGoals];
    } else if (r < pA + pDraw) {
        const goals = Math.floor(Math.random() * 3);
        return [goals, goals];
    } else {
        const awayGoals = 1 + Math.floor(Math.random() * 3);
        const homeGoals = Math.floor(Math.random() * awayGoals);
        return [homeGoals, awayGoals];
    }
}

function simulateFullTournament() {
    // 1. Simulate all group matches
    state.scores = {};
    state.knockoutPicks = { r32: [], r16: [], qf: [], sf: [], final: [] };

    for (const g of Object.keys(GROUPS)) {
        const teams = GROUPS[g];
        for (const [hi, ai, date, venue] of SCHEDULE[g]) {
            const home = teams[hi], away = teams[ai];
            const rH = teamRatings[home] || 1500;
            const rA = teamRatings[away] || 1500;
            const [pA, pD, pB] = simMatchProbs(rH, rA);
            const [hg, ag] = simRandomScore(pA, pD, pB);
            state.scores[`${g}-${hi}-${ai}`] = { home: hg, away: ag };
        }
    }

    // 2. Build R32 matchups and simulate knockout
    const r32 = buildR32Matchups();
    r32.forEach((m, i) => {
        const rA = teamRatings[m.teamA] || 1500;
        const rB = teamRatings[m.teamB] || 1500;
        state.knockoutPicks.r32[i] = Math.random() < eloExpected(rA, rB) ? m.teamA : m.teamB;
    });

    // R16 through Final
    for (const round of ['r16', 'qf', 'sf', 'final']) {
        const matchups = getKnockoutMatchups(round);
        matchups.forEach((m, i) => {
            const rA = teamRatings[m.teamA] || 1500;
            const rB = teamRatings[m.teamB] || 1500;
            state.knockoutPicks[round][i] = Math.random() < eloExpected(rA, rB) ? m.teamA : m.teamB;
        });
    }

    saveState();
}

async function animatedSimulate() {
    // Show thinking overlay
    const orb = el('div', { class: 'sim-orb-wrap' }, [
        el('div', { class: 'sim-orb-glow' }),
        el('div', { class: 'sim-orb' }),
    ]);
    const overlay = el('div', { class: 'sim-overlay' }, [
        orb,
        el('div', { class: 'sim-thinking-text', text: 'Analyzing matchups...' }),
        el('div', { class: 'sim-sub-text', text: 'Simulating 48-team tournament' }),
    ]);
    document.body.appendChild(overlay);

    // Compute everything instantly
    simulateFullTournament();

    await delay(2000);
    overlay.remove();

    // Re-render with all results
    const builder = document.querySelector('.bracket-builder');
    if (builder) {
        builder.remove();
        renderBracketBuilder(containerRef, cachedWcData, flags);
    }
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ===== Computation =====

function computeGroupStandings(group) {
    const teams = GROUPS[group];
    const schedule = SCHEDULE[group];
    const stats = {};
    teams.forEach(t => { stats[t] = { pts: 0, gd: 0, gf: 0, ga: 0 }; });

    let complete = true;
    for (const [hi, ai] of schedule) {
        const key = `${group}-${hi}-${ai}`;
        const s = state.scores[key];
        if (s == null || s.home == null || s.away == null) { complete = false; continue; }
        const home = teams[hi], away = teams[ai];
        const hg = s.home, ag = s.away;
        stats[home].gf += hg; stats[home].ga += ag; stats[home].gd += hg - ag;
        stats[away].gf += ag; stats[away].ga += hg; stats[away].gd += ag - hg;
        if (hg > ag) stats[home].pts += 3;
        else if (hg < ag) stats[away].pts += 3;
        else { stats[home].pts += 1; stats[away].pts += 1; }
    }

    const sorted = teams.slice().sort((a, b) =>
        (stats[b].pts - stats[a].pts) || (stats[b].gd - stats[a].gd) || (stats[b].gf - stats[a].gf) || a.localeCompare(b)
    );
    return { standings: sorted.map((t, i) => ({ team: t, pos: i + 1, ...stats[t] })), complete };
}

function allGroupsComplete() {
    return Object.keys(GROUPS).every(g => computeGroupStandings(g).complete);
}

function getScoreCount() {
    let count = 0;
    for (const g of Object.keys(GROUPS)) {
        for (const [hi, ai] of SCHEDULE[g]) {
            const s = state.scores[`${g}-${hi}-${ai}`];
            if (s != null && s.home != null && s.away != null) count++;
        }
    }
    return count;
}

function rankThirdPlaceTeams() {
    const thirds = [];
    for (const g of Object.keys(GROUPS)) {
        const { standings, complete } = computeGroupStandings(g);
        if (!complete || standings.length < 3) continue;
        const t = standings[2];
        thirds.push({ ...t, group: g });
    }
    thirds.sort((a, b) => (b.pts - a.pts) || (b.gd - a.gd) || (b.gf - a.gf) || a.group.localeCompare(b.group));
    return { qualifying: thirds.slice(0, 8), eliminated: thirds.slice(8) };
}

function allocateThirdPlace(qualifying) {
    const byGroup = {};
    qualifying.forEach(t => { byGroup[t.group] = t.team; });
    const available = Object.keys(byGroup).sort();
    const assignment = {};
    const used = new Set();

    for (let i = 0; i < THIRD_PLACE_SLOTS.length; i++) {
        const slot = THIRD_PLACE_SLOTS[i];
        const oppGroup = THIRD_PLACE_OPPONENTS[i];
        let assigned = false;
        for (const g of available) {
            if (!used.has(g) && g !== oppGroup) {
                assignment[slot] = byGroup[g];
                used.add(g);
                assigned = true;
                break;
            }
        }
        if (!assigned) {
            for (const g of available) {
                if (!used.has(g)) { assignment[slot] = byGroup[g]; used.add(g); break; }
            }
        }
    }
    return assignment;
}

function buildR32Matchups() {
    const g1 = {}, g2 = {};
    for (const g of Object.keys(GROUPS)) {
        const { standings } = computeGroupStandings(g);
        g1[g] = standings[0].team;
        g2[g] = standings[1].team;
    }
    const { qualifying } = rankThirdPlaceTeams();
    const thirdAssign = allocateThirdPlace(qualifying);

    return R32_BRACKET.map(([srcA, srcB], idx) => {
        const resolve = (src, idx) => {
            if (src.startsWith("1")) return g1[src[1]];
            if (src.startsWith("2")) return g2[src[1]];
            if (src === "3") return thirdAssign[idx] || "TBD";
            return "TBD";
        };
        return { teamA: resolve(srcA, idx), teamB: resolve(srcB, idx) };
    });
}

function getKnockoutMatchups(round) {
    if (round === "r32") {
        return allGroupsComplete() ? buildR32Matchups() : [];
    }
    const prevRound = ROUND_ORDER[ROUND_ORDER.indexOf(round) - 1];
    const prevPicks = state.knockoutPicks[prevRound] || [];
    const matchups = [];
    for (let i = 0; i < prevPicks.length; i += 2) {
        if (prevPicks[i] && prevPicks[i + 1]) {
            matchups.push({ teamA: prevPicks[i], teamB: prevPicks[i + 1] });
        }
    }
    return matchups;
}

function isRoundComplete(round) {
    const matchups = getKnockoutMatchups(round);
    if (matchups.length === 0) return false;
    const picks = state.knockoutPicks[round] || [];
    return matchups.length > 0 && picks.length === matchups.length && picks.every(p => p != null);
}

function clearDownstream(round, matchIndex) {
    const nextIdx = ROUND_ORDER.indexOf(round) + 1;
    if (nextIdx >= ROUND_ORDER.length) return;
    const nextRound = ROUND_ORDER[nextIdx];
    const nextMatchIdx = Math.floor(matchIndex / 2);
    if (state.knockoutPicks[nextRound] && state.knockoutPicks[nextRound][nextMatchIdx]) {
        state.knockoutPicks[nextRound][nextMatchIdx] = null;
        clearDownstream(nextRound, nextMatchIdx);
    }
}

// ===== Rendering =====

export function renderBracketBuilder(container, wcData, flagsData) {
    flags = flagsData;
    containerRef = container;
    loadState();

    // Extract ratings from wcData
    if (wcData) {
        cachedWcData = wcData;
        teamRatings = {};
        for (const group of Object.values(wcData.groups)) {
            for (const t of group.teams) {
                teamRatings[t.team] = t.rating;
            }
        }
    }

    const section = el('div', { class: 'bracket-builder' });

    // Header
    section.appendChild(el('div', { class: 'bracket-section-title', text: 'Build Your Bracket' }));
    section.appendChild(el('p', {
        style: 'text-align:center;color:var(--text-tertiary);margin-bottom:24px;font-size:0.9rem',
        text: 'Predict every match and build your path to the final.',
    }));

    // Action buttons
    const actions = el('div', { style: 'display:flex;gap:12px;justify-content:center;margin-bottom:24px;flex-wrap:wrap' });
    actions.appendChild(el('button', {
        class: 'wc-cta-btn',
        text: 'Simulate Tournament',
        style: 'font-size:0.95rem;padding:12px 28px',
        onclick: () => animatedSimulate(),
    }));
    section.appendChild(actions);

    // Progress bar
    section.appendChild(renderProgress());

    // Group panels
    const groupsGrid = el('div', { class: 'wc-grid' });
    for (const g of Object.keys(GROUPS).sort()) {
        groupsGrid.appendChild(renderGroupPanel(g));
    }
    section.appendChild(groupsGrid);

    // Knockout rounds container
    section.appendChild(el('div', { id: 'bracket-knockout' }));

    container.appendChild(section);

    // Render knockout if groups are complete
    renderKnockoutRounds();
}

function renderProgress() {
    const count = getScoreCount();
    const pct = (count / 72) * 100;
    const bar = el('div', { class: 'bracket-progress', style: 'margin-bottom:24px' }, [
        el('div', { style: 'display:flex;justify-content:space-between;margin-bottom:6px' }, [
            el('span', { style: 'font-size:0.85rem;color:var(--text-secondary)', text: 'Group stage predictions' }),
            el('span', { style: 'font-size:0.85rem;color:var(--accent);font-weight:600', text: `${count}/72` }),
        ]),
        el('div', { class: 'bracket-progress-bar' }, [
            el('div', { class: 'bracket-progress-fill', style: `width:${pct}%` }),
        ]),
    ]);
    bar.id = 'bracket-progress';
    return bar;
}

function updateProgress() {
    const old = document.getElementById('bracket-progress');
    if (old) old.replaceWith(renderProgress());
}

function renderGroupPanel(group) {
    const teams = GROUPS[group];
    const { standings, complete } = computeGroupStandings(group);
    const card = el('div', { class: 'wc-group-card' });

    // Header
    const header = el('div', {
        class: 'wc-group-header',
        style: 'cursor:pointer',
        onclick: () => {
            const detail = document.getElementById(`bracket-group-${group}`);
            if (!detail) return;
            const isOpen = detail.style.display !== 'none';
            document.querySelectorAll('.bracket-group-detail').forEach(d => { d.style.display = 'none'; });
            if (!isOpen) detail.style.display = 'block';
        },
    });
    header.appendChild(el('span', { text: `Group ${group}` }));
    const summary = el('span', { class: 'wc-group-summary' });
    for (const t of teams) {
        const f = flagImg(flags[slugify(t)], t, 'sm');
        if (f) { f.title = t; summary.appendChild(f); }
    }
    header.appendChild(summary);
    if (complete) header.appendChild(el('span', { style: 'color:var(--accent);font-size:0.8rem', text: '\u2713' }));
    card.appendChild(header);

    // Detail
    const detail = el('div', { class: 'bracket-group-detail', id: `bracket-group-${group}`, style: 'display:none' });

    // Match inputs
    for (const [hi, ai, date, venue] of SCHEDULE[group]) {
        const home = teams[hi], away = teams[ai];
        const key = `${group}-${hi}-${ai}`;
        const s = state.scores[key] || {};

        detail.appendChild(el('div', { class: 'wc-match-date', text: `${date} \u2014 ${venue}` }));

        const row = el('div', { class: 'bracket-match-input' });

        // Home team
        const homeDiv = el('div', { class: 'bracket-input-team bracket-input-home' });
        const hf = flagImg(flags[slugify(home)], home, 'sm');
        if (hf) homeDiv.appendChild(hf);
        homeDiv.appendChild(document.createTextNode(` ${home}`));
        row.appendChild(homeDiv);

        // Score inputs
        const homeInput = el('input', {
            class: 'bracket-score-input', type: 'number', min: '0', max: '20',
            value: s.home != null ? s.home.toString() : '',
        });
        const awayInput = el('input', {
            class: 'bracket-score-input', type: 'number', min: '0', max: '20',
            value: s.away != null ? s.away.toString() : '',
        });

        const onScoreChange = () => {
            const hv = homeInput.value !== '' ? parseInt(homeInput.value) : null;
            const av = awayInput.value !== '' ? parseInt(awayInput.value) : null;
            state.scores[key] = { home: hv, away: av };
            saveState();
            updateProgress();
            // Refresh this group's standings
            const standingsEl = document.getElementById(`bracket-standings-${group}`);
            if (standingsEl) standingsEl.replaceWith(renderMiniStandings(group));
            // Update header checkmark
            renderKnockoutRounds();
        };
        homeInput.addEventListener('change', onScoreChange);
        awayInput.addEventListener('change', onScoreChange);

        row.appendChild(homeInput);
        row.appendChild(el('span', { style: 'color:var(--text-tertiary);font-size:0.8rem;font-weight:700', text: '\u2013' }));
        row.appendChild(awayInput);

        // Away team
        const awayDiv = el('div', { class: 'bracket-input-team bracket-input-away' });
        awayDiv.appendChild(document.createTextNode(`${away} `));
        const af = flagImg(flags[slugify(away)], away, 'sm');
        if (af) awayDiv.appendChild(af);
        row.appendChild(awayDiv);

        detail.appendChild(row);
    }

    // Mini standings
    detail.appendChild(renderMiniStandings(group));

    card.appendChild(detail);
    return card;
}

function renderMiniStandings(group) {
    const { standings, complete } = computeGroupStandings(group);
    const div = el('div', { id: `bracket-standings-${group}`, style: 'margin-top:12px;padding-top:8px;border-top:1px solid var(--border)' });

    if (standings.every(t => t.pts === 0 && t.gf === 0)) return div; // no scores yet

    const table = el('table', { class: 'wc-group-table', style: 'font-size:0.78rem' });
    const thead = el('thead');
    const hrow = el('tr');
    for (const h of ['', 'Team', 'Pts', 'GD', 'GF']) hrow.appendChild(el('th', { text: h }));
    thead.appendChild(hrow);
    table.appendChild(thead);

    const { qualifying: qualThirds } = complete ? rankThirdPlaceTeams() : { qualifying: [] };
    const qualThirdTeams = new Set(qualThirds.map(t => t.team));

    const tbody = el('tbody');
    standings.forEach((t, i) => {
        const tr = el('tr');
        let style = '';
        if (i < 2) style = 'color:var(--accent);font-weight:600';
        else if (i === 2 && qualThirdTeams.has(t.team)) style = 'color:var(--accent-secondary)';
        else if (i >= 2) style = 'opacity:0.5';

        tr.appendChild(el('td', { text: (i + 1).toString(), style }));
        const nameTd = el('td', { style: `${style};text-align:left` });
        const f = flagImg(flags[slugify(t.team)], t.team, 'sm');
        if (f) nameTd.appendChild(f);
        nameTd.appendChild(document.createTextNode(` ${t.team}`));
        tr.appendChild(nameTd);
        tr.appendChild(el('td', { text: t.pts.toString(), style }));
        tr.appendChild(el('td', { text: (t.gd >= 0 ? '+' : '') + t.gd, style }));
        tr.appendChild(el('td', { text: t.gf.toString(), style }));
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    div.appendChild(table);
    return div;
}

function renderKnockoutRounds() {
    const container = document.getElementById('bracket-knockout');
    if (!container) return;
    container.innerHTML = '';

    if (!allGroupsComplete()) return;

    // R32 as sequential card
    const r32Matchups = getKnockoutMatchups('r32');
    if (r32Matchups.length > 0) {
        const card = el('div', { class: 'card' });
        card.appendChild(el('h2', { text: 'Round of 32' }));
        const grid = el('div', { class: 'bracket-matchups-grid' });
        const picks = state.knockoutPicks.r32 || [];

        r32Matchups.forEach((m, i) => {
            const matchup = el('div', { class: 'bracket-matchup' });
            const picked = picks[i];
            matchup.appendChild(teamButton(m.teamA, picked === m.teamA, picked === m.teamB, () => pickWinner('r32', i, m.teamA)));
            matchup.appendChild(el('span', { class: 'bracket-vs', text: 'vs' }));
            matchup.appendChild(teamButton(m.teamB, picked === m.teamB, picked === m.teamA, () => pickWinner('r32', i, m.teamB)));
            grid.appendChild(matchup);
        });

        card.appendChild(grid);
        container.appendChild(card);

        if (!isRoundComplete('r32')) {
            container.appendChild(resetButton());
            return;
        }
    }

    // R16 onward as visual bracket
    container.appendChild(renderVisualBracket());
    container.appendChild(resetButton());
}

function pickWinner(round, index, team) {
    if (!state.knockoutPicks[round]) state.knockoutPicks[round] = [];
    const prev = state.knockoutPicks[round][index];
    state.knockoutPicks[round][index] = team;
    if (prev && prev !== team) clearDownstream(round, index);
    saveState();
    renderKnockoutRounds();
}

function renderVisualBracket() {
    const bracket = el('div', { class: 'visual-bracket' });

    // Split into left half (R16 matches 0-3) and right half (R16 matches 4-7)
    const r16 = getKnockoutMatchups('r16');
    const r16Picks = state.knockoutPicks.r16 || [];
    const qf = getKnockoutMatchups('qf');
    const qfPicks = state.knockoutPicks.qf || [];
    const sf = getKnockoutMatchups('sf');
    const sfPicks = state.knockoutPicks.sf || [];
    const fin = getKnockoutMatchups('final');
    const finPicks = state.knockoutPicks.final || [];

    // Left half: R16[0-3] → QF[0-1] → SF[0]
    const leftR16 = renderBracketColumn('r16', r16.slice(0, 4), r16Picks, 0, 'R16');
    const leftQF = renderBracketColumn('qf', qf.slice(0, 2), qfPicks, 0, 'QF');
    const leftSF = renderBracketColumn('sf', sf.slice(0, 1), sfPicks, 0, 'SF');

    // Right half: R16[4-7] → QF[2-3] → SF[1]
    const rightR16 = renderBracketColumn('r16', r16.slice(4, 8), r16Picks, 4, 'R16');
    const rightQF = renderBracketColumn('qf', qf.slice(2, 4), qfPicks, 2, 'QF');
    const rightSF = renderBracketColumn('sf', sf.slice(1, 2), sfPicks, 1, 'SF');

    // Final
    const finalCol = el('div', { class: 'vb-column vb-final-col' });
    finalCol.appendChild(el('div', { class: 'vb-round-label', text: 'Final' }));
    if (fin.length > 0) {
        finalCol.appendChild(renderBracketMatchup('final', fin[0], finPicks, 0));
    } else {
        finalCol.appendChild(el('div', { class: 'vb-placeholder', text: 'TBD vs TBD' }));
    }

    // Champion
    if (finPicks[0]) {
        const champ = el('div', { class: 'bracket-champion', style: 'margin-top:16px;padding:20px' });
        const f = flagImg(flags[slugify(finPicks[0])], finPicks[0], 'lg');
        if (f) champ.appendChild(f);
        champ.appendChild(el('div', { class: 'bracket-champion-name', style: 'font-size:1.8rem', text: finPicks[0] }));
        champ.appendChild(el('div', { style: 'font-family:var(--font-display);font-size:1rem;color:var(--accent-secondary);margin-top:4px', text: 'Champion' }));
        finalCol.appendChild(champ);
    }

    // Assemble: Left | Center | Right
    bracket.appendChild(leftR16);
    bracket.appendChild(leftQF);
    bracket.appendChild(leftSF);
    bracket.appendChild(finalCol);
    bracket.appendChild(rightSF);
    bracket.appendChild(rightQF);
    bracket.appendChild(rightR16);

    return bracket;
}

function renderBracketColumn(round, matchups, allPicks, startIdx, label) {
    const col = el('div', { class: `vb-column vb-col-${label.toLowerCase()}` });
    col.appendChild(el('div', { class: 'vb-round-label', text: label }));

    const matchContainer = el('div', { class: 'vb-matches' });
    matchups.forEach((m, i) => {
        const idx = startIdx + i;
        if (m) {
            matchContainer.appendChild(renderBracketMatchup(round, m, allPicks, idx));
        } else {
            matchContainer.appendChild(el('div', { class: 'vb-matchup vb-placeholder' }, [
                el('div', { class: 'vb-team-slot', text: 'TBD' }),
                el('div', { class: 'vb-team-slot', text: 'TBD' }),
            ]));
        }
    });
    col.appendChild(matchContainer);
    return col;
}

function renderBracketMatchup(round, m, allPicks, idx) {
    const picked = allPicks[idx];
    const matchup = el('div', { class: 'vb-matchup' });

    const btnA = el('div', {
        class: `vb-team-slot${picked === m.teamA ? ' vb-winner' : ''}${picked === m.teamB ? ' vb-loser' : ''}`,
        onclick: () => pickWinner(round, idx, m.teamA),
    });
    const fA = flagImg(flags[slugify(m.teamA)], m.teamA, 'sm');
    if (fA) btnA.appendChild(fA);
    btnA.appendChild(document.createTextNode(` ${m.teamA}`));

    const btnB = el('div', {
        class: `vb-team-slot${picked === m.teamB ? ' vb-winner' : ''}${picked === m.teamA ? ' vb-loser' : ''}`,
        onclick: () => pickWinner(round, idx, m.teamB),
    });
    const fB = flagImg(flags[slugify(m.teamB)], m.teamB, 'sm');
    if (fB) btnB.appendChild(fB);
    btnB.appendChild(document.createTextNode(` ${m.teamB}`));

    matchup.appendChild(btnA);
    matchup.appendChild(btnB);
    return matchup;
}

function resetButton() {
    return el('div', { style: 'text-align:center;margin-top:24px' }, [
        el('button', {
            class: 'toggle-btn',
            text: 'Reset Bracket',
            onclick: () => {
                state = { scores: {}, knockoutPicks: { r32: [], r16: [], qf: [], sf: [], final: [] } };
                localStorage.removeItem(STORAGE_KEY);
                const builder = document.querySelector('.bracket-builder');
                if (builder) {
                    builder.remove();
                    renderBracketBuilder(containerRef, cachedWcData, flags);
                }
            },
        }),
    ]);
}

function teamButton(team, isSelected, isEliminated, onClick) {
    const cls = `bracket-team${isSelected ? ' bracket-team-selected' : ''}${isEliminated ? ' bracket-team-eliminated' : ''}`;
    const btn = el('button', { class: cls, onclick: onClick });
    const f = flagImg(flags[slugify(team)], team, 'sm');
    if (f) btn.appendChild(f);
    btn.appendChild(document.createTextNode(` ${team}`));
    return btn;
}
