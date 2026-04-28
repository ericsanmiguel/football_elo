# Football Elo Ratings

Elo ratings for men's and women's international football (soccer) teams, with an interactive website and 2026 World Cup predictions.

**Live site: [ericsanmiguel.github.io/football_elo](https://ericsanmiguel.github.io/football_elo/)**

## Features

### Rankings & Team Profiles
- Elo ratings for **220+ men's** and **170+ women's** national teams
- Searchable, sortable rankings table with country flags and top-N filtering
- Team detail pages with three-mode interactive Plotly chart (Elo rating, smoothed trend, ranking history) and range slider
- Stat cards: peak / lowest rating, best / worst rank, matches played, W/D/L record, World Cup record
- Top 5 wins and worst 5 losses by Elo points
- Per-edition World Cup history with opponent Elo and rank snapshots
- World Cup winner stars next to team names
- Light/dark theme toggle (persisted to browser)
- Featured 2026 World Cup banner on the rankings page (men's only)

### Compare & History
- Compare up to 5 teams on a single overlay chart
- Historical rankings at any point in time (monthly snapshots back to 1900 for men, 1990 for women)
- Quick-jump buttons for every World Cup
- Optional side-by-side comparison to current rankings

### Match Predictor
- Pick any two teams and a venue (home / neutral / away)
- Win/draw/loss probabilities, expected goals, and top 6 scorelines
- Uses the same calibrated Poisson score model as the World Cup simulator

### 2026 World Cup Predictions (men's only)
- Full tournament simulation (10,000 Monte Carlo iterations)
- **Overview tab** — all 48 teams with Elo, Squad Index, Combined Index, and round-by-round advancement probabilities (R32 → Winner)
- **Groups tab** — 12 groups with per-team standings probabilities (1st / 2nd / 3rd / 4th) and per-match W/D/L bars
- **Build Your Bracket** — predict every group-stage score (auto-computes standings and 3rd-place qualification), pick knockout winners, or hit *Simulate Tournament* to fill from a Monte Carlo draw; state persists in `localStorage`

## Methodology

Uses the [World Football Elo Rating](https://www.eloratings.net/about) formula:

**Rn = Ro + K × G × (W - We)**

| Parameter | Description |
|-----------|-------------|
| K factor | Tournament importance: World Cup (60), continental championships (50), qualifiers (40), other tournaments (30), friendlies (20) |
| G factor | Goal difference multiplier: 0–1 goals = 1.0, 2 goals = 1.5, 3+ goals (N) = (11+N)/8 |
| We | Expected result: `1 / (10^(-dr/400) + 1)`, with +50 home advantage |
| W | Actual result: win = 1, draw = 0.5, loss = 0 (shootouts count as draws) |

World Cup predictions use an **Elo-calibrated Poisson score model**: expected goals per team are `λ = 1.2414 × exp(0.002174 × dr − 5.246e-7 × dr²)`, with goals sampled from independent Poisson distributions. The quadratic term tempers expected goals at extreme rating gaps. Parameters are calibrated by Poisson GLM on 64,202 team-match records from men's internationals since 1990.

For the 2026 simulation, base Elo is blended with a **squad-strength index** built from age-corrected Transfermarkt market values: `R_composite = R_Elo + β × z_squad × σ_Elo`, with `β = 0.25` calibrated on 2018+2022 men's World Cup hindcasts. Each Monte Carlo draw also samples team ratings from `N(μ, σ²)` with `σ = 120` Elo points to reflect rating uncertainty.

See the [full methodology](https://ericsanmiguel.github.io/football_elo/#/methodology) on the website, or the [LaTeX appendix](docs/methodology_appendix.tex) for formal documentation.

## Data Sources

Match data by Mart Jurisoo (CC0 public domain):
- **Men's:** [martj42/international_results](https://github.com/martj42/international_results) — 49,000+ matches from 1872
- **Women's:** [martj42/womens-international-results](https://github.com/martj42/womens-international-results) — 11,000+ matches from 1956

Squad data:
- **Squads:** `data/squads/{2018,2022,2026}.csv` — Transfermarkt rosters and market values at each tournament's kickoff date

## Usage

```bash
# Install
pip install -e .

# Full pipeline (download → compute Elo → write rankings, history, charts)
python -m football_elo run

# Download match data only (no computation)
python -m football_elo download

# Print top-N rankings to stdout
python -m football_elo rankings --top 30

# Audit tournament → K-factor mapping
python -m football_elo audit

# Export JSON data for the website (both genders, or one)
python -m football_elo export-web
python -m football_elo export-web --gender men
python -m football_elo export-web --gender women
```

## Tech Stack

- **Backend:** Python (pandas, matplotlib, statsmodels) — Elo computation, Poisson calibration, Monte Carlo simulation, JSON export
- **Frontend:** Vanilla JS, CSS, Plotly.js — no build tools, served as static files from `docs/`
- **Hosting:** GitHub Pages (from `docs/` folder)
- **Automation:** GitHub Actions runs every Monday at 06:00 UTC to refresh men's and women's ratings

## Project Structure

```
football_elo/
├── src/football_elo/          # Python package
│   ├── elo.py                 # Core Elo math
│   ├── pipeline.py            # EloSystem class
│   ├── tournaments.py         # K-factor mapping
│   ├── data.py                # Data download/loading
│   ├── output.py              # CSV/markdown/PNG output
│   ├── web_export.py          # JSON export for website
│   ├── worldcup.py            # 2026 WC simulation
│   ├── player_strength.py     # Age-corrected Transfermarkt values
│   ├── squad_strength.py      # Squad aggregation and z-normalization
│   ├── calibrate_poisson.py   # Poisson GLM calibration of the score model
│   ├── backtest.py            # WC hindcast harness (Brier/log-loss; β/σ grid search)
│   └── __main__.py            # CLI
├── data/squads/               # Tournament squad rosters (tracked in git)
├── docs/                      # Website (GitHub Pages)
│   ├── index.html
│   ├── css/styles.css
│   ├── js/                    # SPA modules
│   ├── data/                  # Generated JSON
│   └── methodology_appendix.tex
├── tests/                     # Unit tests
└── .github/workflows/         # Weekly auto-update
```

## License

MIT License. See [LICENSE](LICENSE).
