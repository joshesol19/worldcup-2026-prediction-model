interface Props { onBack: () => void }

export function AboutPage({ onBack }: Props) {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="sticky top-0 z-20 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            ← Back
          </button>
          <span className="text-slate-300">|</span>
          <span className="text-sm font-semibold text-slate-800">About the Predictions</span>
        </div>
      </div>

      <article className="max-w-2xl mx-auto px-4 py-10 space-y-8">
        <header>
          <h1 className="text-3xl font-black text-slate-900 mb-3">How do the predictions work?</h1>
          <p className="text-slate-500 text-base leading-relaxed">
            A plain-English explainer of the model behind this site — what it knows, how it decides,
            and what its limits are.
          </p>
        </header>

        <Section title="The short version">
          <p>
            We trained a computer model on 32,000+ international football matches played between
            1990 and 2021. The model learned which factors — team strength, recent form, squad talent —
            tend to predict whether the home team wins, the game ends in a draw, or the away team wins.
            At the 2022 World Cup (which was not used in training), the model correctly predicted the
            outcome of <strong>35 out of 64 matches</strong>.
          </p>
        </Section>

        <Section title="What the model looks at">
          <ul className="space-y-2 list-none">
            {[
              ['🏆', 'Elo rating', 'A running score of team quality, updated after every match. Better teams have higher Elos. Teams improve their score by beating strong opponents.'],
              ['📊', 'FIFA ranking', 'The official world ranking published monthly by FIFA.'],
              ['🔥', 'Recent form', 'Points won and goal difference in the last 5 and 10 matches, with competitive games weighted more heavily than friendlies.'],
              ['💰', 'Squad market value', 'The combined transfer value of each squad, sourced from Transfermarkt. A rough stand-in for overall player quality.'],
              ['⚽', 'Stage & venue', 'Whether it\'s a group game or knockout round, and whether the game is at a neutral venue.'],
            ].map(([icon, name, desc]) => (
              <li key={name as string} className="flex gap-3">
                <span className="text-2xl leading-none mt-0.5">{icon}</span>
                <div>
                  <p className="font-semibold text-slate-800">{name as string}</p>
                  <p className="text-sm text-slate-500">{desc as string}</p>
                </div>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Which factors matter most?">
          <p>
            The bars below show the actual feature importances from the Random Forest model —
            the one that produces every win/draw/loss probability on this site. They come
            directly from the model's internal <em>feature_importances_</em> scores, which
            measure how much each input reduces prediction error on average.
          </p>
          <div className="mt-4 space-y-3">
            {[
              { label: 'Elo rating',            pct: 100, desc: '22% of total importance — elo_diff alone is the single biggest feature at 13%' },
              { label: 'Positional squad values',pct: 72,  desc: '~16% combined — goalkeeper, defender, midfielder, attacker market values' },
              { label: 'Recent form',            pct: 63,  desc: '~14% combined — goal difference, points, Elo momentum across last 5–10 matches' },
              { label: 'Tactical matchups',      pct: 32,  desc: '~7% — defence value vs. opponent attack, and attack vs. opponent defence' },
              { label: 'FIFA ranking',           pct: 32,  desc: '~7% combined — home and away rank ordinals' },
              { label: 'Strength of schedule',   pct: 26,  desc: '~6% — average Elo of opponents faced in last 10 games' },
              { label: 'Total squad value',      pct: 23,  desc: '~5% — combined Transfermarkt squad value' },
              { label: 'Venue / match stakes',   pct: 5,   desc: '<1% each — neutral ground and group vs. knockout round' },
            ].map(({ label, pct, desc }) => (
              <div key={label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold text-slate-700">{label}</span>
                </div>
                <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500 rounded-full" style={{ width: `${pct}%` }} />
                </div>
                <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-5 bg-slate-100 rounded-xl px-4 py-3 text-sm text-slate-600">
            <strong className="text-slate-800">Two models, two perspectives.</strong> The prediction
            model (Random Forest) is Elo-dominant — Elo summarises a team's entire competitive
            history in one number, so it naturally rises to the top. The "Key Factors" shown on
            each match card come from a separate{' '}
            <em>explanatory</em> Logistic Regression, which tells a different story: squad value
            dominates there because it has more variance across international teams than Elo does
            after standardisation. Neither is wrong — they're measuring importance in different ways.
          </div>
          <div className="mt-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
            <strong>Why it varies by match:</strong> The bars above are averages over 32,000 training
            matches. For any specific matchup, what dominates depends on how different the two teams
            are. When Spain faces a clearly weaker side, the Elo gap swings the prediction almost on
            its own. When two evenly-rated teams meet — similar Elo, similar ranking — form and squad
            depth become the tie-breakers. Each match card's "Key Factors" shows what drove{' '}
            <em>that</em> specific prediction.
          </div>
        </Section>

        <Section title="How accurate is it?">
          <p>
            Football is famously hard to predict — upsets happen all the time. At the 2022 World Cup,
            the model correctly called 35 of 64 matches (about 55%). Academic researchers using similar
            methods typically hit 53–58%. There is no model in existence that consistently beats 60%
            on three-way football prediction.
          </p>
          <p className="mt-3">
            That said, the predictions are still useful — they give you a sense of which team is{' '}
            <em>more likely</em> to win, not a guarantee. Think of them like weather forecasts.
          </p>
          <div className="mt-4 bg-slate-100 rounded-xl p-4 text-sm text-slate-600">
            <strong className="text-slate-800">Confidence labels:</strong>
            <ul className="mt-2 space-y-1">
              <li><span className="font-semibold text-green-700">Clear favourite</span> — one team has &gt;55% predicted chance</li>
              <li><span className="font-semibold text-blue-700">Slight edge</span> — one team has 45–55% predicted chance</li>
              <li><span className="font-semibold text-amber-700">Anyone's game</span> — all three outcomes are in play</li>
            </ul>
          </div>
        </Section>

        <Section title="The bracket predictions">
          <p>
            The same 43-feature model is used for every match — group stage and knockout alike. The only
            thing that changes between stages is <em>match stakes</em>: group matches and knockout matches
            get different values for this feature, which the model learned to interpret during training.
            Each bracket match card is clickable — tap it to see the full probability breakdown and key
            factors for that matchup.
          </p>
        </Section>

        <Section title="What it can't see">
          <ul className="list-disc list-inside space-y-1 text-slate-600">
            <li>Injuries or squad call-ups announced close to the tournament</li>
            <li>Tactical matchups, playing styles, or specific player form</li>
            <li>Weather, referee tendencies, or crowd effects</li>
            <li>Any matches played after April 2026 (data cut-off)</li>
          </ul>
          <p className="mt-3 text-sm text-slate-500">
            Injury overrides and squad updates are planned for a future version of this site.
          </p>
        </Section>

        <Section title="Data sources">
          <ul className="list-disc list-inside space-y-1 text-slate-600 text-sm">
            <li>Match results: Mart Jürisoo international football dataset (Kaggle) — 49,500+ matches</li>
            <li>FIFA rankings: scraped from the official FIFA website, 346 snapshots 1992–2026</li>
            <li>Squad values: Transfermarkt via Kaggle (davidcariboo/player-scores)</li>
            <li>2026 fixtures: openfootball/worldcup open dataset</li>
          </ul>
        </Section>

        <div className="border-t border-slate-200 pt-6 text-xs text-slate-400">
          Built by Joshua Solano · 2026 FIFA World Cup prediction project
        </div>
      </article>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-lg font-bold text-slate-800 mb-3 pb-2 border-b border-slate-200">{title}</h2>
      <div className="text-slate-600 leading-relaxed space-y-2 text-sm sm:text-base">{children}</div>
    </section>
  );
}
