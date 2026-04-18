/**
 * Methodology and About page.
 */

export async function render(container) {
    container.innerHTML = `
    <div class="methodology-content">
        <h1>Methodology</h1>

        <p>These ratings use the <a href="https://www.eloratings.net/about" target="_blank" rel="noopener">World Football Elo Rating</a> methodology, adapted for men's and women's international football. The system is based on the Elo rating system originally developed for chess, with modifications for football-specific factors.</p>

        <h2>The Formula</h2>
        <div class="formula-block">R<sub>new</sub> = R<sub>old</sub> + K &times; G &times; (W &minus; W<sub>e</sub>)</div>

        <p>After each match, a team's rating changes based on the difference between the <strong>actual result</strong> (W) and the <strong>expected result</strong> (W<sub>e</sub>), scaled by the tournament importance (K) and goal difference (G).</p>

        <h2>K Factor — Tournament Importance</h2>
        <p>Different tournaments carry different weight. A World Cup match affects ratings more than a friendly.</p>
        <table class="k-table">
            <thead><tr><th>K</th><th>Tournament Type</th><th>Examples</th></tr></thead>
            <tbody>
                <tr><td>60</td><td>World Cup &amp; Olympics</td><td>World Cup, Olympic Games</td></tr>
                <tr><td>50</td><td>Continental Championships</td><td>UEFA Euro, Copa Am&eacute;rica, AFC Asian Cup, Gold Cup, Confederations Cup</td></tr>
                <tr><td>40</td><td>Qualifiers &amp; Nations Leagues</td><td>World Cup qualification, Euro qualification, UEFA Nations League</td></tr>
                <tr><td>30</td><td>Other Tournaments</td><td>Regional championships, invitational cups, multi-sport games</td></tr>
                <tr><td>20</td><td>Friendlies</td><td>International friendly matches</td></tr>
            </tbody>
        </table>

        <h2>G Factor — Goal Difference</h2>
        <p>Larger victories are rewarded with a multiplier on the rating change:</p>
        <table class="k-table">
            <thead><tr><th>Goals</th><th>G Factor</th></tr></thead>
            <tbody>
                <tr><td>0-1</td><td>1.0</td></tr>
                <tr><td>2</td><td>1.5</td></tr>
                <tr><td>3</td><td>1.75</td></tr>
                <tr><td>3</td><td>1.75</td></tr>
                <tr><td>4</td><td>1.875</td></tr>
                <tr><td>5+</td><td>(11 + N) / 8</td></tr>
            </tbody>
        </table>

        <h2>Expected Result</h2>
        <p>The expected result is calculated using the rating difference between teams:</p>
        <div class="formula-block">W<sub>e</sub> = 1 / (10<sup>&minus;dr/400</sup> + 1)</div>
        <p>Where <code>dr</code> is the rating difference. Equal teams each have a 50% expected result. A 200-point advantage gives roughly a 76% expected result.</p>

        <h2>Home Advantage</h2>
        <p>When a match is not at a neutral venue, <strong>50 points</strong> are added to the home team's rating for the expected result calculation. This corresponds to roughly a 57%&ndash;43% advantage. Matches at neutral venues (such as World Cup group stages) have no home advantage applied.</p>

        <h2>Match Results</h2>
        <p>Win = 1, Draw = 0.5, Loss = 0. Matches decided by penalty shootout are treated as draws (0.5 for both teams) — only the result in regular/extra time counts.</p>

        <h2>Initial Rating</h2>
        <p>All teams start at <strong>1500</strong>. The Elo system is self-correcting — after 20&ndash;30 matches, the initial rating has minimal impact on a team's current rating.</p>

        <h2>Score Prediction Model</h2>
        <p>Match scores are predicted using an <strong>Elo-calibrated Poisson model</strong>. For each team, the expected number of goals is:</p>
        <div class="formula-block">&lambda; = &mu; &times; e<sup>c &times; dr</sup></div>
        <p>Where <code>&mu; = 1.28</code> is the baseline goals per team, <code>c = 0.00215</code> is the Elo scaling factor, and <code>dr</code> is the adjusted rating difference (including the +50 home advantage). Both parameters were calibrated via log-linear regression on 98,000+ team-match records from our historical dataset.</p>
        <p>Each team's goals are sampled independently from a Poisson distribution with their respective &lambda;. Win/draw/loss probabilities are derived analytically from the Poisson model by summing over all possible scorelines.</p>

        <h2>2026 World Cup Predictions</h2>
        <p>The World Cup predictions are generated using a <strong>Monte Carlo simulation</strong> of the entire tournament (10,000 iterations). For each simulation:</p>
        <ol style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li><strong>Group stage:</strong> All 12 groups are simulated simultaneously. Match scores are sampled from the Poisson model, producing realistic scorelines and goal differences.</li>
            <li><strong>3rd-place qualification:</strong> The 8 best 3rd-place teams (by points, then goal difference) advance to the Round of 32.</li>
            <li><strong>Knockout bracket:</strong> Teams are placed into the official FIFA bracket. Knockout matches use Poisson-sampled scores; draws go to a penalty shootout decided by the Elo expected result.</li>
            <li><strong>Home advantage:</strong> Host nations (USA, Mexico, Canada) receive the same +50 rating boost used in the Elo system.</li>
        </ol>
        <p>The probabilities shown (R32, R16, QF, SF, Final, Winner) represent the fraction of simulations in which each team reached that stage.</p>

        <h2>Composite Rating: Squad Strength + Rating Uncertainty</h2>
        <p style="background:var(--bg-tertiary);padding:12px 14px;border-radius:8px;border-left:3px solid var(--accent);font-size:0.92rem">
            <strong>Deployed on the live site</strong> for the 2026 men's World Cup predictions. Parameters <code>&beta; = 0.25</code> and <code>&sigma; = 120</code> were calibrated on 2018 + 2022 men's WCs. Pre-deployment top-3 combined share was 66%; now 56%, matching published consensus models.
        </p>

        <p>National teams play 8&ndash;12 matches per year, so Elo can lag meaningful roster changes. We also observed that treating Elo as the team's <em>true</em> strength &mdash; with zero uncertainty &mdash; over-concentrates probability on the top favorite: a team rated ~200 Elo points above its rivals wins each of 6 matches at ~85%, so the compounded championship probability is ~40%, far above what top-favorite teams historically achieve. Two adjustments fix these issues.</p>

        <h3 style="margin-top:16px">1. Squad Strength (Transfermarkt)</h3>
        <p>We joined World Cup rosters from <a href="https://github.com/jfjelstul/worldcup" target="_blank" rel="noopener">jfjelstul/worldcup</a> with historical Transfermarkt market values from <a href="https://github.com/dcaribou/transfermarkt-datasets" target="_blank" rel="noopener">dcaribou/transfermarkt-datasets</a> to build an age-adjusted squad score per team.</p>

        <h4 style="margin-top:12px">Age Adjustment (two-step)</h4>
        <p>Transfermarkt discounts aging players more aggressively than on-field performance actually declines:</p>
        <ol style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li><strong>Recover peak-equivalent talent:</strong> divide current TM value by the empirical age-discount curve &mdash; a 32-year-old at &euro;60M with peak &euro;100M recovers to &asymp;&euro;94M.</li>
            <li><strong>Apply performance decay:</strong> multiply by a shallower performance-age factor from the soccer-aging literature (peak &asymp; 27, ~2%/yr decline through age 32, then steeper).</li>
        </ol>

        <h4 style="margin-top:12px">Log Transform (diminishing returns)</h4>
        <p>Raw TM values are sharply right-skewed &mdash; a &euro;100M player isn't 10&times; better than a &euro;10M player, and the gap from amateur (~&euro;0) to serious professional (&euro;5&ndash;10M) is much larger than from professional to superstar. We apply a <code>log(1 + value_in_millions)</code> transform per player before averaging. This compresses the 110&times; raw team-mean spread in 2018 to about 10&times; in log space.</p>

        <h4 style="margin-top:12px">Composite Rating</h4>
        <div class="formula-block">R<sub>composite</sub> = R<sub>Elo</sub> + &beta; &middot; z<sub>squad</sub> &middot; &sigma;<sub>Elo</sub></div>
        <p>where <code>z<sub>squad</sub></code> is the log-transformed mean squad score z-normalized across tournament teams, and <code>&sigma;<sub>Elo</sub></code> rescales into Elo-equivalent points. At <code>&beta; = 0.25</code>, a top-tier squad (z &asymp; +1.8) gets a +70 Elo bump.</p>

        <h3 style="margin-top:16px">2. Rating Uncertainty</h3>
        <p>At the start of each tournament simulation, each team's rating is sampled once from a Gaussian centered on its composite rating with <code>&sigma; = 120</code> Elo points, then held fixed for all six matches in that simulation. Over 10,000 simulations this coherently captures the idea that Elo is an estimate, not truth &mdash; a fraction of simulations will have Spain at 2150 (below France) rather than 2284, and in those Spain does not steamroll the bracket.</p>
        <div class="formula-block">R<sub>T</sub><sup>(s)</sup> = R<sub>T</sub><sup>composite</sup> + &epsilon;<sub>T</sub><sup>(s)</sup>, &nbsp; &epsilon; ~ N(0, &sigma;<sup>2</sup>)</div>

        <h3 style="margin-top:16px">Calibration &amp; Findings</h3>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li>Pure-Elo match-level Brier: <strong>0.576</strong> (2018), <strong>0.615</strong> (2022) &mdash; both well below the 0.667 uniform-prediction baseline.</li>
            <li>Joint grid search over (&beta;, &sigma;) finds a broad minimum around &beta; &isin; [0.2, 0.4], &sigma; &isin; [100, 180]. Deployed choice <strong>&beta; = 0.25, &sigma; = 120</strong> sits inside that minimum region. Pooled Brier lift &asymp; 1.2% over pure Elo.</li>
            <li>Match-level Brier is conservative here: the <em>big</em> effect is on compounded tournament probabilities. Pre-deployment Spain was 31%; now 26%, in the 15&ndash;25% range consensus models use for top favorites. Top-3 combined share drops from 66% to 56%.</li>
        </ul>
        <p>Full derivations and calibration tables are in the <a href="https://github.com/e-san-miguel/football_elo/blob/main/docs/methodology_appendix.tex" target="_blank" rel="noopener">LaTeX methodology appendix</a>.</p>

        <h2>Data Sources</h2>
        <p>Match data is provided by Mart J&uuml;risoo (CC0 public domain):</p>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li><strong>Women's:</strong> <a href="https://github.com/martj42/womens-international-results" target="_blank" rel="noopener">womens-international-results</a> &mdash; 11,000+ matches from 1956 to present.</li>
            <li><strong>Men's:</strong> <a href="https://github.com/martj42/international_results" target="_blank" rel="noopener">international_results</a> &mdash; 49,000+ matches from 1872 to present.</li>
        </ul>
        <p>The squad-strength experiment additionally uses <a href="https://github.com/jfjelstul/worldcup" target="_blank" rel="noopener">jfjelstul/worldcup</a> for historical WC rosters and <a href="https://github.com/dcaribou/transfermarkt-datasets" target="_blank" rel="noopener">dcaribou/transfermarkt-datasets</a> for Transfermarkt player valuations.</p>

        <h2>References</h2>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li>Elo, A. E. (1978). <em>The Rating of Chessplayers, Past and Present.</em> Arco Publishing.</li>
            <li>World Football Elo Ratings. <a href="https://www.eloratings.net/about" target="_blank" rel="noopener">eloratings.net</a>. The methodology used here is adapted from this system, which has rated men's national teams since 1997.</li>
            <li>FIFA World Rankings. <a href="https://inside.fifa.com/fifa-world-ranking/men" target="_blank" rel="noopener">Men</a> | <a href="https://inside.fifa.com/fifa-world-ranking/women" target="_blank" rel="noopener">Women</a>. The official FIFA ranking systems have used Elo-based methodologies since 2018 (men) and 2003 (women).</li>
        </ul>

        <h2>About</h2>
        <p>This project was developed by <strong>Eric San Miguel</strong>.</p>
        <p>For questions, suggestions, or corrections, reach out at <a href="mailto:eric.sanmiguel@psu.edu">eric.sanmiguel@psu.edu</a>.</p>
    </div>
    `;
}
