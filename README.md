# Football Elo Ratings

Elo ratings for men's and women's international football (soccer) teams, with an interactive website and 2026 World Cup predictions.

**Live site: [e-san-miguel.github.io/football_elo](https://e-san-miguel.github.io/football_elo/)**

## Features

### Rankings & Team Profiles
- Elo ratings for **220+ men's** and **170+ women's** national teams
- Searchable, sortable rankings table with country flags
- Team detail pages with interactive Plotly.js charts (Elo, smoothed trend, ranking history)
- Best/worst rank, peak/lowest rating, W/D/L record
- Top 5 wins and worst 5 losses by Elo points
- World Cup history per team with opponent Elo and rankings
- World Cup winner stars next to team names
- Light/dark theme toggle

### Compare & History
- Compare up to 5 teams on one interactive chart
- Historical rankings at any point in time (monthly snapshots from 1900/1990)
- Quick-jump buttons for every World Cup

### 2026 World Cup Predictions
- Full tournament simulation (10,000 Monte Carlo iterations)
- Round-by-round advancement probabilities (R32 through Winner)
- Group stage match probabilities with W/D/L bars
- Interactive bracket builder — predict every match or simulate a random tournament
- All 12 groups with official schedule, dates, and venues

## Methodology

Uses the [World Football Elo Rating](https://www.eloratings.net/about) formula:

**Rn = Ro + K x G x (W - We)**

| Parameter | Description |
|-----------|-------------|
| K factor | Tournament importance: World Cup (60), continental championships (50), qualifiers (40), other tournaments (30), friendlies (20) |
| G factor | Goal difference multiplier: 0-1 goals = 1.0, 2 goals = 1.5, 3+ goals (N) = (11+N)/8 |
| We | Expected result: `1 / (10^(-dr/400) + 1)`, with +50 home advantage |
| W | Actual result: win = 1, draw = 0.5, loss = 0 (shootouts count as draws) |

World Cup predictions use an **Elo-calibrated Poisson score model**: expected goals per team are `λ = 1.28 × exp(0.00215 × dr)`, with goals sampled from independent Poisson distributions. Parameters calibrated from 98,000+ historical match records.

See the [full methodology](https://e-san-miguel.github.io/football_elo/#/methodology) on the website, or the [LaTeX appendix](docs/methodology_appendix.tex) for formal documentation.

## Data Sources

Match data by Mart Jurisoo (CC0 public domain):
- **Men's:** [martj42/international_results](https://github.com/martj42/international_results) — 49,000+ matches from 1872
- **Women's:** [martj42/womens-international-results](https://github.com/martj42/womens-international-results) — 11,000+ matches from 1956

## Usage

```bash
# Install
pip install -e .

# Export JSON data for the website (both men's and women's)
python -m football_elo export-web

# Export only one gender
python -m football_elo export-web --gender men
python -m football_elo export-web --gender women

# Show rankings in terminal
python -m football_elo rankings --top 30

# Audit tournament K-factor mapping
python -m football_elo audit
```

## Tech Stack

- **Backend:** Python (pandas, matplotlib) — Elo computation, Monte Carlo simulation, JSON export
- **Frontend:** Vanilla JS, CSS, Plotly.js — no build tools, served as static files from `docs/`
- **Hosting:** GitHub Pages (from `docs/` folder)
- **Automation:** GitHub Actions runs weekly to update ratings with new match data

## Project Structure

```
football_elo/
├── src/football_elo/          # Python package
│   ├── elo.py                 # Core Elo math
│   ├── pipeline.py            # EloSystem class
│   ├── tournaments.py         # K-factor mapping
│   ├── data.py                # Data download/loading
│   ├── web_export.py          # JSON export for website
│   ├── worldcup.py            # 2026 WC simulation
│   └── __main__.py            # CLI
├── docs/                      # Website (GitHub Pages)
│   ├── index.html
│   ├── css/styles.css
│   ├── js/                    # SPA modules
│   └── data/                  # Generated JSON
├── tests/                     # Unit tests
└── .github/workflows/         # Weekly auto-update
```

## License

MIT License. See [LICENSE](LICENSE).
