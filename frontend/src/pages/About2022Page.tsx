import type { Cache2022 } from '../types';

interface Props {
  data: Cache2022;
  onBack: () => void;
}

function StatBox({ value, label, color }: { value: string | number; label: string; color: string }) {
  return (
    <div className={`bg-white rounded-xl border p-5 text-center shadow-sm ${color}`}>
      <p className={`text-4xl font-black ${color.includes('green') ? 'text-green-600' : color.includes('red') ? 'text-red-500' : color.includes('amber') ? 'text-amber-500' : 'text-slate-900'}`}>
        {value}
      </p>
      <p className="text-xs text-slate-500 mt-1 font-medium">{label}</p>
    </div>
  );
}

function BarRow({ label, correct, total }: { label: string; correct: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((correct / total) * 100);
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="w-36 shrink-0 text-sm text-slate-600">{label}</span>
      <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-24 shrink-0 text-xs text-slate-500 text-right">
        {correct}/{total} — {pct}%
      </span>
    </div>
  );
}

export function About2022Page({ data, onBack }: Props) {
  const { summary } = data;
  const pct = Math.round((summary.correct / summary.total) * 100);

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
          <span className="text-sm font-semibold text-slate-800">2022 World Cup — Model Performance</span>
        </div>
      </div>

      <article className="max-w-2xl mx-auto px-4 py-10 space-y-10">
        <header>
          <h1 className="text-3xl font-black text-slate-900 mb-3">How did the model do in 2022?</h1>
          <p className="text-slate-500 text-base leading-relaxed">
            The 2022 World Cup in Qatar was the model's first real test — it was deliberately held
            out of training so we'd get an honest read on performance.
          </p>
        </header>

        {/* Summary stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatBox value={`${pct}%`} label="Overall accuracy" color="border-slate-200" />
          <StatBox value={summary.correct} label="Correct" color="border-green-200" />
          <StatBox value={summary.incorrect} label="Incorrect" color="border-red-200" />
          <StatBox value={summary.drawMiss} label="Close calls" color="border-amber-200" />
        </div>

        {/* Context */}
        <section className="space-y-4 text-slate-600 text-sm leading-relaxed">
          <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2">What does 55% actually mean?</h2>
          <p>
            A random guess on a three-way outcome (home win / draw / away win) would be correct
            about <strong>33%</strong> of the time. Always picking the favourite regardless of
            probability gets you to roughly 45–48%. At <strong>{pct}%</strong>, the model is
            meaningfully outperforming both baselines.
          </p>
          <p>
            Academic researchers using similar statistical approaches — Elo ratings, squad
            strength, form — typically land between <strong>53–58%</strong> on World Cup data.
            The theoretical ceiling for three-way football prediction is generally considered
            to be around <strong>60–62%</strong>; the sport is inherently random. Our result
            sits comfortably in the expected range.
          </p>
          <div className="bg-slate-100 rounded-xl px-4 py-3 text-slate-700">
            <strong>Bottom line:</strong> The model isn't magic, but it's a well-calibrated
            signal. Think of it like a weather forecast — it won't be right every time, but
            it gives you a better-than-chance read on who's favoured.
          </div>
        </section>

        {/* Accuracy by stage */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2">Accuracy by stage</h2>
          <p className="text-sm text-slate-500">
            Performance varied quite a bit across rounds — partly by design (knockout matches
            tend to feature stronger teams), partly due to the small sample size in later rounds.
          </p>
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-5 py-4">
            <BarRow label="Group Stage"       correct={26} total={48} />
            <BarRow label="Round of 16"       correct={6}  total={8}  />
            <BarRow label="Quarter-finals"    correct={1}  total={4}  />
            <BarRow label="Semi-finals"       correct={2}  total={2}  />
            <BarRow label="3rd Place / Final" correct={0}  total={2}  />
          </div>
          <p className="text-xs text-slate-400">
            Small sample sizes in knockout rounds mean single match results swing percentages wildly.
            The semi-final 100% and final 0% are two matches each — don't read too much into them.
          </p>
        </section>

        {/* Close calls */}
        <section className="space-y-4 text-slate-600 text-sm leading-relaxed">
          <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2">What are "close calls"?</h2>
          <p>
            A close call (⚠) is a match where the model predicted a draw but one team won — or
            vice versa. These are the softest misses: the model knew the match was competitive,
            it just misjudged the exact outcome by one step. There were <strong>{summary.drawMiss}</strong> of
            these at the 2022 World Cup.
          </p>
          <p>
            Draws are the hardest outcome to predict in football. They occur in about 23–25% of
            international matches, but no model predicts them well — the incentives and game
            dynamics that produce a 0–0 or 1–1 are often impossible to anticipate from statistics
            alone. If the model were perfect on all close calls, overall accuracy would jump to
            roughly <strong>{Math.round(((summary.correct + summary.drawMiss) / summary.total) * 100)}%</strong>.
          </p>
        </section>

        {/* Notable calls */}
        <section className="space-y-4 text-slate-600 text-sm leading-relaxed">
          <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2">Notable calls</h2>
          <ul className="space-y-3">
            {[
              { flag: '✓', label: 'Got right', cls: 'text-green-700', items: [
                'Argentina to beat Australia (R16)',
                'France to beat Morocco (SF)',
                'Brazil to beat South Korea 4–1 (R16)',
                'Portugal to beat Switzerland 6–1 (R16)',
              ]},
              { flag: '✗', label: 'Got wrong', cls: 'text-red-600', items: [
                'Morocco to beat Portugal in the QF — one of the biggest upsets of the tournament',
                '3rd place: predicted Croatia, Morocco won',
                'Final: predicted France, Argentina won on penalties',
              ]},
            ].map(({ flag, label, cls, items }) => (
              <div key={label}>
                <p className={`font-semibold mb-1.5 ${cls}`}>{flag} {label}</p>
                <ul className="list-disc list-inside space-y-1 text-slate-500">
                  {items.map(item => <li key={item}>{item}</li>)}
                </ul>
              </div>
            ))}
          </ul>
        </section>

        <div className="border-t border-slate-200 pt-6 text-xs text-slate-400 text-center">
          All predictions were generated before the tournament began using data available up to early November 2022.
        </div>
      </article>
    </div>
  );
}
