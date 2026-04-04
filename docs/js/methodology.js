/**
 * Methodology and About page.
 */

export async function render(container) {
    container.innerHTML = `
    <div class="methodology-content">
        <h1>Methodology</h1>

        <p>These ratings use the <a href="https://www.eloratings.net/about" target="_blank" rel="noopener">World Football Elo Rating</a> methodology, adapted for women's international football. The system is based on the Elo rating system originally developed for chess, with modifications for football-specific factors.</p>

        <h2>The Formula</h2>
        <div class="formula-block">R<sub>new</sub> = R<sub>old</sub> + K &times; G &times; (W &minus; W<sub>e</sub>)</div>

        <p>After each match, a team's rating changes based on the difference between the <strong>actual result</strong> (W) and the <strong>expected result</strong> (W<sub>e</sub>), scaled by the tournament importance (K) and goal difference (G).</p>

        <h2>K Factor — Tournament Importance</h2>
        <p>Different tournaments carry different weight. A World Cup match affects ratings more than a friendly.</p>
        <table class="k-table">
            <thead><tr><th>K</th><th>Tournament Type</th><th>Examples</th></tr></thead>
            <tbody>
                <tr><td>60</td><td>World Cup &amp; Olympics</td><td>FIFA Women's World Cup, Olympic Games</td></tr>
                <tr><td>50</td><td>Continental Championships</td><td>UEFA Euro, Copa Am&eacute;rica, AFC Asian Cup</td></tr>
                <tr><td>40</td><td>Qualifiers</td><td>World Cup qualification, Euro qualification</td></tr>
                <tr><td>30</td><td>Other Tournaments</td><td>Algarve Cup, SheBelieves Cup, Arnold Clark Cup</td></tr>
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
                <tr><td>4</td><td>1.875</td></tr>
                <tr><td>5+</td><td>(11 + N) / 8</td></tr>
            </tbody>
        </table>

        <h2>Expected Result</h2>
        <p>The expected result is calculated using the rating difference between teams:</p>
        <div class="formula-block">W<sub>e</sub> = 1 / (10<sup>&minus;dr/400</sup> + 1)</div>
        <p>Where <code>dr</code> is the rating difference. Equal teams each have a 50% expected result. A 200-point advantage gives roughly a 76% expected result.</p>

        <h2>Home Advantage</h2>
        <p>When a match is not at a neutral venue, <strong>100 points</strong> are added to the home team's rating for the expected result calculation. This corresponds to roughly a 64%&ndash;36% advantage. Matches at neutral venues (such as World Cup finals) have no home advantage applied.</p>

        <h2>Match Results</h2>
        <p>Win = 1, Draw = 0.5, Loss = 0. Matches decided by penalty shootout are treated as draws (0.5 for both teams) — only the result in regular/extra time counts.</p>

        <h2>Initial Rating</h2>
        <p>All teams start at <strong>1500</strong>. The Elo system is self-correcting — after 20&ndash;30 matches, the initial rating has minimal impact on a team's current rating.</p>

        <h2>Data Sources</h2>
        <p>Match data is provided by Mart J&uuml;risoo (CC0 public domain):</p>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li><strong>Women's:</strong> <a href="https://github.com/martj42/womens-international-results" target="_blank" rel="noopener">womens-international-results</a> &mdash; 11,000+ matches from 1956 to present.</li>
            <li><strong>Men's:</strong> <a href="https://github.com/martj42/international_results" target="_blank" rel="noopener">international_results</a> &mdash; 49,000+ matches from 1872 to present.</li>
        </ul>

        <h2>References</h2>
        <ul style="color:var(--text-secondary);line-height:2;padding-left:20px">
            <li>Elo, A. E. (1978). <em>The Rating of Chessplayers, Past and Present.</em> Arco Publishing.</li>
            <li>World Football Elo Ratings. <a href="https://www.eloratings.net/about" target="_blank" rel="noopener">eloratings.net</a>. The methodology used here is adapted from this system, which has rated men's national teams since 1997.</li>
            <li>FIFA World Rankings. <a href="https://inside.fifa.com/fifa-world-ranking/men" target="_blank" rel="noopener">Men</a> | <a href="https://inside.fifa.com/fifa-world-ranking/women" target="_blank" rel="noopener">Women</a>. The official FIFA ranking systems have used Elo-based methodologies since 2018 (men) and 2003 (women).</li>
        </ul>

        <h2>About</h2>
        <p>This project was developed by <strong>Eric San Miguel</strong>. The source code is available on <a href="https://github.com/e-san-miguel/football_elo" target="_blank" rel="noopener">GitHub</a>.</p>
        <p>For questions, suggestions, or corrections, reach out at <a href="mailto:eric.sanmiguel@psu.edu">eric.sanmiguel@psu.edu</a>.</p>
    </div>
    `;
}
