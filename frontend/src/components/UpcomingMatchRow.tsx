import type { Match2026 } from '../types';

interface Props {
  match: Match2026;
  onClick: () => void;
}


export function UpcomingMatchRow({ match, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-xl px-4 py-3 flex items-center gap-3 transition-all group"
    >
      {/* Date + time */}
      <div className="w-28 shrink-0 text-left">
        <p className="text-xs font-semibold text-slate-700">{match.date}</p>
        {match.time && <p className="text-xs text-slate-400">{match.time}</p>}
      </div>

      {/* Teams */}
      <div className="flex-1 flex items-center gap-2 min-w-0">
        <span className="text-lg leading-none">{match.team1.flag}</span>
        <span className="text-sm font-semibold text-slate-800 truncate">{match.team1.name}</span>
        <span className="text-xs text-slate-400 shrink-0 mx-1">vs</span>
        <span className="text-lg leading-none">{match.team2.flag}</span>
        <span className="text-sm font-semibold text-slate-800 truncate">{match.team2.name}</span>
      </div>

      {/* Group label */}
      <span className="hidden sm:inline-block shrink-0 text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
        {match.group || match.round}
      </span>

      {/* Predicted outcome */}
      {/* {!isPending && outcome ? (
        <span className="shrink-0 text-xs font-semibold text-green-700 bg-green-50 border border-green-200 px-2.5 py-0.5 rounded-full">
          {outcome}
        </span>
      ) : (
        <span className="shrink-0 text-xs text-slate-400">TBD</span>
      )} */}

      {/* Arrow */}
      <span className="text-slate-300 group-hover:text-slate-500 transition-colors shrink-0 ml-1">›</span>
    </button>
  );
}
