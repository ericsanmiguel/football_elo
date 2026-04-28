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
        <div class="formula-block">&lambda; = &mu; &times; e<sup>c &times; dr + c<sub>2</sub> &times; dr<sup>2</sup></sup></div>
        <p>Where <code>&mu; = 1.24</code> is the baseline goals per team, <code>c = 2.17 &times; 10<sup>&minus;3</sup></code> is the linear Elo scaling factor, <code>c<sub>2</sub> = &minus;5.25 &times; 10<sup>&minus;7</sup></code> is the quadratic term (negative, encoding sublinearity at extreme rating gaps), and <code>dr</code> is the adjusted rating difference including the +50 home advantage. Parameters were estimated by Poisson GLM on 64,202 team-match records from men's international results since 1990.</p>
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

        <h2>Composite Rating for World Cup Predictions</h2>
        <p>World Cup predictions augment base Elo with two additional terms. A squad-strength adjustment derived from Transfermarkt market values compensates for the lag in international Elo, since national teams play only 8&ndash;12 matches per year. Gaussian rating uncertainty is then added in the tournament Monte Carlo to account for imprecision in each team's estimated rating.</p>

        <h3>Squad Score</h3>
        <p>For each team's World Cup squad, player market values are transformed in three steps before aggregation:</p>
        <ol style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li><strong>Age adjustment.</strong> Each player's current Transfermarkt value is divided by an empirical age-discount curve to yield a peak-equivalent value, then multiplied by a shallower performance-age factor (peak at age 27, roughly 2%/yr decline through age 32, steeper thereafter).</li>
            <li><strong>Log transform.</strong> Age-adjusted values enter the aggregation as <code>log(1 + v)</code> with <code>v</code> in millions of euros, reflecting diminishing marginal returns at the player level.</li>
            <li><strong>Aggregation.</strong> The squad score is the mean log-value across matched players, then z-normalized across the tournament's participating teams.</li>
        </ol>

        <h3>Composite Rating</h3>
        <div class="formula-block">R<sub>composite</sub> = R<sub>Elo</sub> + &beta; &middot; z<sub>squad</sub> &middot; &sigma;<sub>Elo</sub></div>
        <p>Here <code>&sigma;<sub>Elo</sub></code> is the standard deviation of Elo across the tournament's teams, rescaling the squad term into Elo-equivalent points. The blend weight <code>&beta;</code> interpolates between pure Elo (<code>&beta; = 0</code>) and a squad-only rating.</p>

        <h3>Rating Uncertainty</h3>
        <p>Each tournament simulation samples every team's rating once from a Gaussian centered on its composite rating, then holds it fixed across all six matches in that simulation:</p>
        <div class="formula-block">R<sub>T</sub><sup>(s)</sup> = R<sub>T</sub><sup>composite</sup> + &epsilon;<sub>T</sub><sup>(s)</sup>, &nbsp; &epsilon; ~ N(0, &sigma;<sup>2</sup>)</div>
        <p>Fixing the draw within a simulation keeps each team's effective strength consistent across its matches. Match probabilities on the Groups tab use the same structure, marginalized over 400 rating samples per match.</p>

        <h3>Calibration</h3>
        <p>The parameters <code>&beta;</code> and <code>&sigma;</code> are set by grid search to minimize pooled multiclass Brier score across the 2018 and 2022 men's World Cup match outcomes. The deployed values are <strong>&beta; = 0.25</strong> and <strong>&sigma; = 120</strong> Elo points.</p>

        <h2>Data Sources</h2>
        <p>Match data is provided by Mart J&uuml;risoo (CC0 public domain):</p>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li><strong>Women's:</strong> <a href="https://github.com/martj42/womens-international-results" target="_blank" rel="noopener">womens-international-results</a> &mdash; 11,000+ matches from 1956 to present.</li>
            <li><strong>Men's:</strong> <a href="https://github.com/martj42/international_results" target="_blank" rel="noopener">international_results</a> &mdash; 49,000+ matches from 1872 to present.</li>
        </ul>
        <p>World Cup squad data for the composite rating comes from <a href="https://github.com/jfjelstul/worldcup" target="_blank" rel="noopener">jfjelstul/worldcup</a> (historical rosters) and <a href="https://github.com/dcaribou/transfermarkt-datasets" target="_blank" rel="noopener">dcaribou/transfermarkt-datasets</a> (Transfermarkt player valuations and dates of birth).</p>

        <h2>References</h2>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li>Elo, A. E. (1978). <em>The Rating of Chessplayers, Past and Present.</em> Arco Publishing.</li>
            <li>World Football Elo Ratings. <a href="https://www.eloratings.net/about" target="_blank" rel="noopener">eloratings.net</a>. The methodology used here is adapted from this system, which has rated men's national teams since 1997.</li>
            <li>FIFA World Rankings. <a href="https://inside.fifa.com/fifa-world-ranking/men" target="_blank" rel="noopener">Men</a> | <a href="https://inside.fifa.com/fifa-world-ranking/women" target="_blank" rel="noopener">Women</a>. The official FIFA ranking systems have used Elo-based methodologies since 2018 (men) and 2003 (women).</li>
        </ul>

        <h2>About</h2>
        <p>This project was developed by <a href="https://ericsanmiguel.github.io/"><strong>Eric San Miguel</strong></a>.</p>
        <p>For questions, suggestions, or corrections, reach out at <a href="mailto:eric.sanmiguel@psu.edu">eric.sanmiguel@psu.edu</a>.</p>
    </div>
    `;
}
