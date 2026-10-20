import type { Match2026, Match2022, ShapFeature } from '../types';
import { ProbabilityBar } from '../components/ProbabilityBar';
import { ConfidenceBadge } from '../components/ConfidenceBadge';

type AnyMatch = Match2026 | Match2022;

const CONFIDENCE_LEVEL: Record<string, string> = {
  low: 'Low confidence',
  moderate: 'Moderate confidence',
  high: 'High confidence',
};

function formatMatchDate(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

function is2022(m: AnyMatch): m is Match2022 {
  return 'actualOutcome' in m;
}

function outcomeText(outcome: string | null, t1: string, t2: string): string {
  if (outcome === 'team1') return t1;
  if (outcome === 'draw') return 'Draw';
  if (outcome === 'team2') return t2;
  return '—';
}

function StatRow({ label, v1, v2, lowerBetter }: {
  label: string; v1: number | string | null; v2: number | string | null; lowerBetter?: boolean;
}) {
  const n1 = typeof v1 === 'number' ? v1 : null;
  const n2 = typeof v2 === 'number' ? v2 : null;
  const t1Better = n1 !== null && n2 !== null ? (lowerBetter ? n1 < n2 : n1 > n2) : false;
  const t2Better = n1 !== null && n2 !== null ? (lowerBetter ? n2 < n1 : n2 > n1) : false;

  return (
    <div className="flex items-center py-3 border-b border-slate-100 last:border-0">
      <span className={`w-28 text-right text-sm font-semibold ${t1Better ? 'text-blue-700' : 'text-slate-700'}`}>
        {v1 ?? '—'}
      </span>
      <span className="flex-1 text-center text-xs text-slate-400 px-3">{label}</span>
      <span className={`w-28 text-left text-sm font-semibold ${t2Better ? 'text-red-600' : 'text-slate-700'}`}>
        {v2 ?? '—'}
      </span>
    </div>
  );
}

function ShapBar({ feat, maxMagnitude, team1Name, team2Name, neutralFlag }: {
  feat: ShapFeature;
  maxMagnitude: number;
  team1Name: string;
  team2Name: string;
  neutralFlag?: number;
}) {
  const { feature, rawFeature, direction, magnitude } = feat;
  const pct = maxMagnitude > 0 ? (magnitude / maxMagnitude) * 100 : 0;
  const isT1 = direction === 'favors_team1';
  const favoringTeam = isT1 ? team1Name : team2Name;

  let label = feature;
  let favours: string | null = favoringTeam;
  let barColor = isT1 ? 'bg-blue-500' : 'bg-red-400';
  let textColor = isT1 ? 'text-blue-600' : 'text-red-500';

  if (rawFeature === 'neutral') {
    if (neutralFlag === 0) {
      label = 'Home advantage';
    } else {
      label = 'Neutral venue';
      favours = null;
      barColor = 'bg-slate-300';
      textColor = 'text-slate-400';
    }
  } else if (rawFeature === 'competition_tier') {
    label = 'Match stakes';
  }

  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-600">{label}</span>
        {favours !== null ? (
          <span className={`font-medium ${textColor}`}>→ favours {favours}</span>
        ) : (
          <span className="text-slate-400">applies equally</span>
        )}
      </div>
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

interface Props {
  match: AnyMatch;
  onBack: () => void;
}

export function MatchDetailPage({ match, onBack }: Props) {
  const is22 = is2022(match);
  const probs = match.probabilities;
  const stats = match.teamStats;
  const t1 = match.team1.name;
  const t2 = match.team2.name;

  const predStatusConfig = {
    correct:   { bg: 'bg-green-100 border-green-300', text: 'text-green-700', label: '✓ Correctly predicted' },
    incorrect: { bg: 'bg-red-100 border-red-300',     text: 'text-red-700',   label: '✗ Incorrect prediction' },
    draw_miss: { bg: 'bg-amber-100 border-amber-300', text: 'text-amber-700', label: '⚠ Close — predicted wrong outcome' },
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sticky header */}
      <div className="sticky top-0 z-20 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            ← Back
          </button>
          <span className="text-slate-300">|</span>
          <span className="text-sm text-slate-600">
            {match.group || match.round} · {match.date}
          </span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* Match hero */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          {/* Stage badge */}
          <div className="flex justify-between items-center mb-6">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
              {match.group || match.round}
            </span>
            {'venue' in match && match.venue && (
              <span className="text-xs text-slate-400">{match.venue}</span>
            )}
          </div>

          {/* Teams */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col items-center flex-1">
              <span className="text-5xl mb-2">{match.team1.flag}</span>
              <h2 className="text-xl font-bold text-slate-900 text-center">{t1}</h2>
            </div>
            <div className="text-center shrink-0">
              {is22 && match.actualScore ? (
                <div>
                  <p className="text-4xl font-black text-slate-900">
                    {match.actualScore.team1} – {match.actualScore.team2}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">Final Score</p>
                </div>
              ) : (
                <div>
                  <p className="text-2xl font-light text-slate-300">vs</p>
                  <p className="text-xs text-slate-400 mt-1">{match.date}</p>
                </div>
              )}
            </div>
            <div className="flex flex-col items-center flex-1">
              <span className="text-5xl mb-2">{match.team2.flag}</span>
              <h2 className="text-xl font-bold text-slate-900 text-center">{t2}</h2>
            </div>
          </div>

          {/* 2022 result status */}
          {is22 && match.predictionStatus && (
            <div className={`mt-6 flex items-center justify-center gap-2 p-3 rounded-xl border ${predStatusConfig[match.predictionStatus].bg}`}>
              <span className={`text-sm font-semibold ${predStatusConfig[match.predictionStatus].text}`}>
                {predStatusConfig[match.predictionStatus].label}
              </span>
            </div>
          )}
        </div>

        {/* Prediction */}
        {probs ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
              Our Prediction
            </h3>

            <div className="flex justify-between text-sm font-semibold text-slate-700 mb-2">
              <span>{t1}</span>
              <span className="text-slate-400">Draw</span>
              <span>{t2}</span>
            </div>
            <ProbabilityBar probs={probs} team1Name={t1} team2Name={t2} />

            <div className="mt-5 flex items-center gap-3 flex-wrap">
              <div className="flex-1">
                <p className="text-xs text-slate-400 mb-0.5">Predicted Winner</p>
                <p className="text-lg font-bold text-slate-900">
                  {outcomeText(match.predictedOutcome, t1, t2)}
                </p>
              </div>
              {match.confidence && (
                <div className="flex flex-col items-end gap-1">
                  <ConfidenceBadge confidence={match.confidence} />
                  <p className="text-xs text-slate-400">{CONFIDENCE_LEVEL[match.confidence]}</p>
                </div>
              )}
            </div>

            {is22 && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <p className="text-xs text-slate-400 mb-0.5">Actual Result</p>
                <p className="text-lg font-bold text-slate-900">
                  {outcomeText(match.actualOutcome, t1, t2)}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 text-center text-slate-400">
            Prediction will be available once the bracket is set.
          </div>
        )}

        {/* Key factors */}
        {match.shapFeatures && match.shapFeatures.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
              Key Factors
            </h3>
            {match.shapFeatures.map((f, i) => (
              <ShapBar
                key={i}
                feat={f}
                maxMagnitude={Math.max(...match.shapFeatures!.map(sf => sf.magnitude))}
                team1Name={t1}
                team2Name={t2}
                neutralFlag={'neutral' in match ? (match as any).neutral : undefined}
              />
            ))}
          </div>
        )}

        {/* Head to head stats */}
        {stats && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
              Head to Head
            </h3>
            <div className="flex justify-between text-xs font-bold text-slate-500 mb-2 px-2">
              <span>{match.team1.flag} {t1}</span>
              <span>{match.team2.flag} {t2}</span>
            </div>
            <StatRow label="FIFA Ranking" v1={stats.team1.fifaRank} v2={stats.team2.fifaRank} lowerBetter />
            <StatRow label="Elo Rating" v1={stats.team1.eloRating} v2={stats.team2.eloRating} />
            <StatRow label="Form (last 10 pts)" v1={stats.team1.last10Pts} v2={stats.team2.last10Pts} />
            <StatRow label="Recent Goal Diff (5)" v1={stats.team1.last5Gd} v2={stats.team2.last5Gd} />
            <StatRow
              label="Squad Value"
              v1={stats.team1.squadValueM ? `€${stats.team1.squadValueM}M` : null}
              v2={stats.team2.squadValueM ? `€${stats.team2.squadValueM}M` : null}
            />
          </div>
        )}

        {/* Match details */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
            Match Details
          </h3>
          <div className="space-y-2">
            {[
              { label: 'Date', value: formatMatchDate(match.date) },
              ...('time' in match && match.time ? [{ label: 'Kickoff', value: match.time + ' local' }] : []),
              ...('venue' in match && match.venue ? [{ label: 'Venue', value: match.venue }] : []),
              { label: 'Stage', value: match.round || match.group || '—' },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-start py-1.5 border-b border-slate-100 last:border-0">
                <span className="w-20 shrink-0 text-xs text-slate-400 font-medium pt-0.5">{label}</span>
                <span className="text-sm text-slate-700">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* About prediction footnote */}
        <div className="text-xs text-slate-400 text-center pb-4">
          Predictions are generated by a machine learning model trained on international football data from 1990–2021.{' '}
          <button
            onClick={() => (window as any).__navigateAbout?.()}
            className="text-blue-500 hover:underline"
          >
            Learn more about how it works
          </button>
        </div>
      </div>
    </div>
  );
}
