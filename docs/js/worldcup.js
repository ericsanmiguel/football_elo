/**
 * 2026 World Cup predictions view.
 */

import { getTeamFlags } from './data.js';
import { el, flagImg } from './utils.js';

const BASE = document.querySelector('base')?.href
    || window.location.pathname.replace(/\/[^/]*$/, '/');

export async function render(container) {
    container.innerHTML = '<div class="loading">Loading World Cup data...</div>';

    const [wcData, flags] = await Promise.all([
        fetch(`${BASE}data/men/worldcup2026.json`).then(r => r.json()),
        getTeamFlags(),
    ]);

    container.innerHTML = '';

    // Header
    const hero = el('div', { class: 'hero' }, [
        el('h1', { text: '2026 World Cup Predictions' }),
        el('p', { class: 'hero-subtitle', text: 'Group stage probabilities based on current Elo ratings \u00b7 50,000 simulations' }),
    ]);
    container.appendChild(hero);

    // All 48 teams ranked
    container.appendChild(buildRankingsCard(wcData, flags));

    // Groups section title
    container.appendChild(el('h2', {
        style: 'font-family:var(--font-display);font-weight:700;font-size:1.5rem;text-transform:uppercase;margin:32px 0 16px;color:var(--text-secondary)',
        text: 'Group Stage',
    }));
    container.appendChild(el('p', {
        style: 'color:var(--text-tertiary);margin-bottom:24px;font-size:0.9rem',
        text: 'Click a group to see detailed predictions and match-by-match probabilities.',
    }));

    // Groups grid — compact cards
    const grid = el('div', { class: 'wc-grid' });
    for (const groupName of Object.keys(wcData.groups).sort()) {
        grid.appendChild(buildGroupCard(groupName, wcData.groups[groupName], flags));
    }
    container.appendChild(grid);
}

function buildRankingsCard(wcData, flags) {
    const card = el('div', { class: 'card' });
    card.appendChild(el('h2', { text: 'World Cup Team Rankings' }));

    // Collect all teams with their group
    const allTeams = [];
    for (const [gName, group] of Object.entries(wcData.groups)) {
        for (const t of group.teams) {
            allTeams.push({ ...t, group: gName });
        }
    }
    allTeams.sort((a, b) =>
        (b.p_winner ?? 0) - (a.p_winner ?? 0)
        || (b.p_final ?? 0) - (a.p_final ?? 0)
        || (b.p_sf ?? 0) - (a.p_sf ?? 0)
        || (b.p_qf ?? 0) - (a.p_qf ?? 0)
        || (b.p_r16 ?? 0) - (a.p_r16 ?? 0)
        || (b.p_r32 ?? 0) - (a.p_r32 ?? 0)
    );

    const table = el('table', { class: 'rankings-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    for (const h of ['#', 'Team', 'Grp', 'Elo', 'R32', 'R16', 'QF', 'SF', 'Final', 'Win']) {
        const cls = ['#', 'Team', 'Grp'].includes(h) ? '' : 'text-right';
        headerRow.appendChild(el('th', { text: h, class: cls }));
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el('tbody');
    allTeams.forEach((t, idx) => {
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
        tr.appendChild(el('td', { class: 'rating-cell text-right', text: Math.round(t.rating).toString() }));

        for (const key of ['p_r32', 'p_r16', 'p_qf', 'p_sf', 'p_final', 'p_winner']) {
            const pct = t[key] ?? 0;
            tr.appendChild(pctCell(pct, key === 'p_winner'));
        }

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    const wrap = el('div', { class: 'rankings-table-wrap' });
    wrap.appendChild(table);
    card.appendChild(wrap);
    return card;
}

function buildGroupCard(groupName, group, flags) {
    const card = el('div', { class: 'wc-group-card', id: `group-${groupName}` });

    // Header (always visible)
    const header = el('div', {
        class: 'wc-group-header',
        style: 'cursor:pointer',
        onclick: () => toggleGroup(groupName),
    });
    header.appendChild(el('span', { text: `Group ${groupName}` }));

    // Compact team summary in header
    const summary = el('span', { class: 'wc-group-summary' });
    for (const t of group.teams) {
        const flag = flagImg(flags[t.slug], t.team, 'sm');
        if (flag) {
            flag.title = t.team;
            summary.appendChild(flag);
        }
    }
    header.appendChild(summary);
    card.appendChild(header);

    // Expandable detail section
    const detail = el('div', { class: 'wc-group-detail', id: `detail-${groupName}`, style: 'display:none' });

    // Team probabilities table
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

    // Match predictions
    detail.appendChild(el('div', { class: 'wc-matches-title', text: 'Match Predictions', style: 'margin-top:16px' }));

    for (const m of group.matches) {
        // Date and venue header
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
        if (m.p_home >= 8) barContainer.appendChild(el('div', {
            class: 'wc-prob-segment wc-prob-home',
            style: `width:${m.p_home}%`,
            text: `${m.p_home}%`,
        }));
        else barContainer.appendChild(el('div', {
            class: 'wc-prob-segment wc-prob-home',
            style: `width:${m.p_home}%`,
        }));
        if (m.p_draw >= 8) barContainer.appendChild(el('div', {
            class: 'wc-prob-segment wc-prob-draw',
            style: `width:${m.p_draw}%`,
            text: `${m.p_draw}%`,
        }));
        else barContainer.appendChild(el('div', {
            class: 'wc-prob-segment wc-prob-draw',
            style: `width:${m.p_draw}%`,
        }));
        if (m.p_away >= 8) barContainer.appendChild(el('div', {
            class: 'wc-prob-segment wc-prob-away',
            style: `width:${m.p_away}%`,
            text: `${m.p_away}%`,
        }));
        else barContainer.appendChild(el('div', {
            class: 'wc-prob-segment wc-prob-away',
            style: `width:${m.p_away}%`,
        }));
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
    // Close all others
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

function probCell(pct, isElim = false) {
    const intensity = isElim
        ? Math.min(pct / 50, 1) * 0.3
        : Math.min(pct / 50, 1) * 0.3;
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
