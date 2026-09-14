import { useMemo, useState } from 'react';
import type { Cache2026 } from '../types';

interface RankedTeam {
  name: string;
  flag: string;
  fifaRank: number | null;
  eloRating: number | null;
  squadValueM: number | null;
  last10Pts: number | null;
}

interface Props {
  data: Cache2026 | null;
  loading: boolean;
}

const DEFAULT_VISIBLE = 25;

export function FifaRankingsTab({ data, loading }: Props) {
  const [showAll, setShowAll] = useState(false);

  const teams = useMemo<RankedTeam[]>(() => {
    if (!data) return [];
    const seen = new Map<string, RankedTeam>();

    for (const m of data.matches) {
      if (!m.teamStats) continue;
      const pairs: [{ name: string; flag: string }, typeof m.teamStats.team1][] = [
        [m.team1, m.teamStats.team1],
        [m.team2, m.teamStats.team2],
      ];
      for (const [team, stats] of pairs) {
        if (!seen.has(team.name)) {
          seen.set(team.name, {
            name: team.name,
            flag: team.flag,
            fifaRank: stats.fifaRank,
            eloRating: stats.eloRating,
            squadValueM: stats.squadValueM,
            last10Pts: stats.last10Pts,
          });
        }
      }
    }

    const ranked = [...seen.values()].filter(t => t.fifaRank !== null);
    const unranked = [...seen.values()].filter(t => t.fifaRank === null);

    ranked.sort((a, b) => (a.fifaRank ?? 999) - (b.fifaRank ?? 999));
    unranked.sort((a, b) => a.name.localeCompare(b.name));

    return [...ranked, ...unranked];
  }, [data]);

  const visible = showAll ? teams : teams.slice(0, DEFAULT_VISIBLE);

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-12 bg-slate-200 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data || teams.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-800">FIFA Rankings</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {teams.filter(t => t.fifaRank !== null).length} ranked teams · April 2026 snapshot
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-[3rem_1fr_5rem_5rem_6rem] sm:grid-cols-[3rem_1fr_5rem_5rem_6rem_5rem] gap-0 px-4 py-2.5 border-b border-slate-100">
          <span className="text-xs font-semibold text-slate-400 text-center">#</span>
          <span className="text-xs font-semibold text-slate-400">Team</span>
          <span className="text-xs font-semibold text-slate-400 text-right">Rank</span>
          <span className="text-xs font-semibold text-slate-400 text-right">Elo</span>
          <span className="text-xs font-semibold text-slate-400 text-right">Squad (€M)</span>
          <span className="hidden sm:block text-xs font-semibold text-slate-400 text-right">Form (L10)</span>
        </div>

        {/* Rows */}
        <div className="divide-y divide-slate-100">
          {visible.map((team, i) => {
            const globalRank = team.fifaRank;
            const rowNum = i + 1;
            const isTop3 = rowNum <= 3;
            const isTop10 = rowNum <= 10;

            return (
              <div
                key={team.name}
                className="grid grid-cols-[3rem_1fr_5rem_5rem_6rem] sm:grid-cols-[3rem_1fr_5rem_5rem_6rem_5rem] gap-0 px-4 py-3 items-center hover:bg-slate-50 transition-colors"
              >
                {/* Row number */}
                <div className="flex items-center justify-center">
                  {isTop3 ? (
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      rowNum === 1 ? 'bg-amber-100 text-amber-700' :
                      rowNum === 2 ? 'bg-slate-200 text-slate-600' :
                      'bg-orange-100 text-orange-700'
                    }`}>{rowNum}</span>
                  ) : (
                    <span className={`text-sm font-semibold ${isTop10 ? 'text-slate-600' : 'text-slate-400'}`}>
                      {rowNum}
                    </span>
                  )}
                </div>

                {/* Team */}
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-lg leading-none shrink-0">{team.flag}</span>
                  <span className={`text-sm font-semibold truncate ${isTop10 ? 'text-slate-800' : 'text-slate-700'}`}>
                    {team.name}
                  </span>
                </div>

                {/* Global FIFA rank */}
                <div className="text-right">
                  {globalRank !== null ? (
                    <span className={`text-sm font-bold tabular-nums ${
                      globalRank <= 10 ? 'text-green-700' :
                      globalRank <= 25 ? 'text-slate-700' : 'text-slate-500'
                    }`}>#{globalRank}</span>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </div>

                {/* Elo */}
                <div className="text-right">
                  <span className="text-sm tabular-nums text-slate-600">
                    {team.eloRating !== null ? Math.round(team.eloRating) : '—'}
                  </span>
                </div>

                {/* Squad value */}
                <div className="text-right">
                  <span className="text-sm tabular-nums text-slate-600">
                    {team.squadValueM !== null
                      ? team.squadValueM >= 1000
                        ? `€${(team.squadValueM / 1000).toFixed(1)}B`
                        : `€${Math.round(team.squadValueM)}M`
                      : '—'}
                  </span>
                </div>

                {/* Form */}
                <div className="hidden sm:block text-right">
                  {team.last10Pts !== null ? (
                    <span className={`text-sm font-semibold tabular-nums ${
                      team.last10Pts >= 20 ? 'text-green-700' :
                      team.last10Pts >= 14 ? 'text-slate-700' : 'text-slate-500'
                    }`}>{team.last10Pts}<span className="text-xs font-normal text-slate-400">/30</span></span>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {teams.length > DEFAULT_VISIBLE && (
        <div className="text-center">
          <button
            onClick={() => setShowAll(v => !v)}
            className="inline-flex items-center gap-2 border border-slate-300 hover:border-slate-400 bg-white text-slate-700 text-sm font-medium px-5 py-2.5 rounded-xl transition-colors"
          >
            {showAll
              ? `Show top ${DEFAULT_VISIBLE} ↑`
              : `Show all ${teams.length} qualified teams ↓`}
          </button>
        </div>
      )}
    </div>
  );
}
