import type { Match2022 } from '../types';

interface Props {
  match: Match2022;
  onClick: () => void;
}

const STATUS = {
  correct:   { cls: 'bg-green-50 border-green-300 hover:border-green-400', badge: 'bg-green-100 text-green-700', label: '✓ Correct' },
  incorrect: { cls: 'bg-red-50 border-red-300 hover:border-red-400',       badge: 'bg-red-100 text-red-700',   label: '✗ Incorrect' },
  draw_miss: { cls: 'bg-amber-50 border-amber-300 hover:border-amber-400', badge: 'bg-amber-100 text-amber-700',label: '⚠ Close call' },
};

function outcomeLabel(o: string | null, t1: string, t2: string) {
  if (o === 'team1') return t1;
  if (o === 'draw') return 'Draw';
  if (o === 'team2') return t2;
  return '—';
}

export function MatchRow2022({ match, onClick }: Props) {
  const s = STATUS[match.predictionStatus ?? 'incorrect'];

  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white border rounded-xl px-4 py-3 flex items-center gap-3 transition-all group ${s.cls}`}
    >
      {/* Date */}
      <div className="w-24 shrink-0">
        <p className="text-xs font-semibold text-slate-700">{match.date}</p>
        <p className="text-xs text-slate-400">{match.round}</p>
      </div>

      {/* Teams + score */}
      <div className="flex-1 flex items-center gap-2 min-w-0">
        <span className="text-lg leading-none">{match.team1.flag}</span>
        <span className="text-sm font-semibold text-slate-800 truncate">{match.team1.name}</span>
        {match.actualScore ? (
          <span className="text-sm font-bold text-slate-700 shrink-0 mx-1">
            {match.actualScore.team1} – {match.actualScore.team2}
          </span>
        ) : (
          <span className="text-xs text-slate-400 shrink-0 mx-1">vs</span>
        )}
        <span className="text-lg leading-none">{match.team2.flag}</span>
        <span className="text-sm font-semibold text-slate-800 truncate">{match.team2.name}</span>
      </div>

      {/* Predicted */}
      <div className="hidden sm:flex flex-col items-end shrink-0 text-xs text-slate-400 gap-0.5">
        <span>Predicted: <span className="text-slate-600 font-medium">{outcomeLabel(match.predictedOutcome, match.team1.name, match.team2.name)}</span></span>
        <span>Actual: <span className="text-slate-600 font-medium">{outcomeLabel(match.actualOutcome, match.team1.name, match.team2.name)}</span></span>
      </div>

      {/* Status badge */}
      <span className={`shrink-0 text-xs font-semibold px-2.5 py-0.5 rounded-full ${s.badge}`}>
        {s.label}
      </span>

      <span className="text-slate-300 group-hover:text-slate-500 transition-colors shrink-0 ml-1">›</span>
    </button>
  );
}
