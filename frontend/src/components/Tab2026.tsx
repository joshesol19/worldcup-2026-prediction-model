import { useMemo, useState } from 'react';
import type { Cache2026, FixtureData, Match2026 } from '../types';
import { UpcomingMatchRow } from './UpcomingMatchRow';
import { SkeletonRow } from './SkeletonCard';

const TODAY = '2026-05-02';
const GROUP_LETTERS = ['A','B','C','D','E','F','G','H','I','J','K','L'];

interface Props {
  data: Cache2026 | null;
  fixtures: FixtureData | null;
  loading: boolean;
  onMatchClick: (matchId: string, year: '2026' | '2022') => void;
}

export function Tab2026({ data, fixtures: _fixtures, loading, onMatchClick }: Props) {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const groupMatches = useMemo(() => {
    const map = new Map<string, Match2026[]>();
    for (const g of GROUP_LETTERS) map.set(g, []);
    for (const m of (data?.matches ?? [])) {
      if (m.group) {
        const letter = m.group.replace('Group ', '');
        map.get(letter)?.push(m);
      }
    }
    return map;
  }, [data?.matches]);

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
      </div>
    );
  }

  if (!data) return null;

  const groupTeams = (g: string) => {
    const seen = new Map<string, { name: string; flag: string }>();
    for (const m of groupMatches.get(g) ?? []) {
      if (!seen.has(m.team1.name)) seen.set(m.team1.name, m.team1);
      if (!seen.has(m.team2.name)) seen.set(m.team2.name, m.team2);
    }
    return [...seen.values()];
  };

  const upcoming = data.matches
    .filter(m => m.stage === 'group' && m.date >= TODAY)
    .sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time));

  const displayMatches = showAll ? upcoming : upcoming.slice(0, 5);
  const predictedCount = data.matches.filter(m => m.status === 'predicted').length;

  return (
    <div className="space-y-8">
      {/* Group Stage */}
      <section>
        <h2 className="text-base font-bold text-slate-800 mb-3">Group Stage</h2>

        <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2 mb-3">
          {GROUP_LETTERS.map(g => {
            const teams = groupTeams(g);
            const isSelected = selectedGroup === g;
            return (
              <button
                key={g}
                onClick={() => setSelectedGroup(prev => prev === g ? null : g)}
                className={`text-left bg-white border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all ${
                  isSelected ? 'border-green-500 ring-2 ring-green-200' : 'border-slate-200'
                }`}
              >
                <div className={`px-2.5 py-1.5 ${isSelected ? 'bg-green-600' : 'bg-slate-700'} transition-colors`}>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">Group {g}</h3>
                </div>
                <div className="p-2 space-y-1">
                  {teams.map(t => (
                    <div key={t.name} className="flex items-center gap-1 text-xs text-slate-700">
                      <span className="text-sm leading-none">{t.flag}</span>
                      <span className="truncate">{t.name}</span>
                    </div>
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        {/* Expanded group matches */}
        {selectedGroup && (
          <div className="bg-white border border-green-200 rounded-xl shadow-sm overflow-hidden">
            <div className="bg-green-600 px-4 py-2.5 flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Group {selectedGroup} — All Matches</h3>
              <button
                onClick={() => setSelectedGroup(null)}
                className="text-green-200 hover:text-white text-sm leading-none"
              >
                ✕
              </button>
            </div>
            <div className="p-3 space-y-2">
              {(groupMatches.get(selectedGroup) ?? [])
                .sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time))
                .map(m => (
                  <UpcomingMatchRow
                    key={m.matchId}
                    match={m}
                    onClick={() => onMatchClick(m.matchId, '2026')}
                  />
                ))}
            </div>
          </div>
        )}
      </section>

      {/* Group stage matches */}
      <section className="space-y-4">
        <div className="flex items-baseline justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-800">Group Stage Matches</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              {upcoming.length} matches remaining · {predictedCount} with predictions
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {displayMatches.length === 0 ? (
            <div className="text-center py-12 text-slate-400">No group stage matches found.</div>
          ) : (
            displayMatches.map(m => (
              <UpcomingMatchRow
                key={m.matchId}
                match={m}
                onClick={() => onMatchClick(m.matchId, '2026')}
              />
            ))
          )}
        </div>

        {upcoming.length > 5 && (
          <div className="text-center">
            <button
              onClick={() => setShowAll(v => !v)}
              className="inline-flex items-center gap-2 border border-slate-300 hover:border-slate-400 bg-white text-slate-700 text-sm font-medium px-5 py-2.5 rounded-xl transition-colors"
            >
              {showAll ? 'Show fewer matches ↑' : `Show all ${upcoming.length} group stage matches ↓`}
            </button>
          </div>
        )}
      </section>

    </div>
  );
}
