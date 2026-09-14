import { useState, useMemo } from 'react';
import type { Cache2022, Match2022 } from '../types';
import { SkeletonRow } from './SkeletonCard';

interface Props {
  data: Cache2022 | null;
  loading: boolean;
  onMatchClick: (matchId: string, year: '2026' | '2022') => void;
  onAboutClick: () => void;
}

const STATUS = {
  correct:   { badge: 'bg-green-100 text-green-700', dot: 'bg-green-500',  label: '✓' },
  incorrect: { badge: 'bg-red-100 text-red-700',     dot: 'bg-red-500',    label: '✗' },
  draw_miss: { badge: 'bg-amber-100 text-amber-700', dot: 'bg-amber-400',  label: '⚠' },
};

const GROUP_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

const KO_ROUNDS = ['Round of 16', 'Quarter-final', 'Semi-final', 'Match for third place', 'Final'];
const KO_LABELS: Record<string, string> = {
  'Round of 16':           'Round of 16',
  'Quarter-final':         'Quarter-Finals',
  'Semi-final':            'Semi-Finals',
  'Match for third place': 'Third Place',
  'Final':                 'The Final',
};

function outcomeLabel(o: string | null, t1: string, t2: string) {
  if (o === 'team1') return t1;
  if (o === 'draw') return 'Draw';
  if (o === 'team2') return t2;
  return '—';
}

function GroupMatchRow({ match, onClick }: { match: Match2022; onClick: () => void }) {
  const s = STATUS[match.predictionStatus ?? 'incorrect'];
  const { team1, team2, actualScore } = match;
  return (
    <button
      onClick={onClick}
      className="w-full text-left hover:bg-slate-50 transition-colors px-4 py-3 border-b border-slate-100 last:border-0"
    >
      <div className="flex items-center gap-3">
        <span className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
        <span className="text-base leading-none shrink-0">{team1.flag}</span>
        <span className="text-sm font-semibold text-slate-800 flex-1 text-right truncate">{team1.name}</span>
        <span className="text-sm font-bold text-slate-700 shrink-0 tabular-nums">
          {actualScore ? `${actualScore.team1} – ${actualScore.team2}` : 'vs'}
        </span>
        <span className="text-sm font-semibold text-slate-800 flex-1 truncate">{team2.name}</span>
        <span className="text-base leading-none shrink-0">{team2.flag}</span>
        <div className="shrink-0 flex items-center gap-2">
          <span className="hidden sm:block text-xs text-slate-400">
            Pred: <span className="text-slate-600">{outcomeLabel(match.predictedOutcome, team1.name, team2.name)}</span>
          </span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${s.badge}`}>{s.label}</span>
        </div>
        <span className="text-slate-300 text-sm">›</span>
      </div>
    </button>
  );
}

function KOMatchCard({ match, isChampion, onClick }: { match: Match2022; isChampion?: boolean; onClick: () => void }) {
  const { team1, team2, actualScore, actualOutcome, predictedOutcome, predictionStatus } = match;
  const s = STATUS[predictionStatus ?? 'incorrect'];

  const winner =
    actualOutcome === 'team1' ? team1.name :
    actualOutcome === 'team2' ? team2.name :
    null;

  const isPens = actualOutcome === 'draw' && actualScore !== null
    && actualScore.team1 !== null && actualScore.team2 !== null
    && actualScore.team1 === actualScore.team2;

  const teamRow = (
    team: { name: string; flag: string },
    scoreVal: number | null | undefined,
    isWinner: boolean,
    side: 'top' | 'bottom',
  ) => (
    <div className={`flex items-center gap-2 py-2 px-3 ${side === 'top' ? 'border-b border-slate-100' : ''} ${isWinner ? 'bg-green-50' : ''}`}>
      <span className="text-lg leading-none">{team.flag}</span>
      <span className={`text-sm flex-1 min-w-0 truncate ${isWinner ? 'font-bold text-slate-900' : 'font-medium text-slate-500'}`}>
        {team.name}
      </span>
      {scoreVal !== null && scoreVal !== undefined && (
        <span className={`text-sm font-bold tabular-nums ${isWinner ? 'text-green-700' : 'text-slate-400'}`}>{scoreVal}</span>
      )}
    </div>
  );

  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white border rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow ${
        isChampion ? 'border-yellow-400 ring-2 ring-yellow-200' : 'border-slate-200'
      }`}
    >
      {isChampion && (
        <div className="bg-yellow-400 text-center py-1">
          <span className="text-xs font-bold text-yellow-900">🏆 Champion</span>
        </div>
      )}
      {teamRow(team1, actualScore?.team1, winner === team1.name, 'top')}
      {teamRow(team2, actualScore?.team2, winner === team2.name, 'bottom')}
      <div className="px-3 py-1.5 border-t border-slate-100 bg-slate-50 flex items-center justify-between gap-2">
        <span className="text-xs text-slate-400 truncate">
          Pred: <span className="text-slate-600">{outcomeLabel(predictedOutcome, team1.name, team2.name)}</span>
          {isPens && <span className="ml-1 text-slate-400">(pens)</span>}
        </span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${s.badge}`}>{s.label}</span>
      </div>
    </button>
  );
}

export function Tab2022({ data, loading, onMatchClick, onAboutClick }: Props) {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  const groupMatches = useMemo(() => {
    const map = new Map<string, Match2022[]>();
    for (const g of GROUP_LETTERS) map.set(g, []);
    for (const m of (data?.matches ?? [])) {
      if (m.round === 'Group Stage' && m.group) {
        const letter = m.group.replace('Group ', '');
        map.get(letter)?.push(m);
      }
    }
    return map;
  }, [data?.matches]);

  const koMatches = useMemo(() => {
    const map = new Map<string, Match2022[]>();
    for (const r of KO_ROUNDS) map.set(r, []);
    for (const m of (data?.matches ?? [])) {
      if (m.round !== 'Group Stage' && map.has(m.round)) {
        map.get(m.round)!.push(m);
      }
    }
    return map;
  }, [data?.matches]);

  if (loading) {
    return <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}</div>;
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

  const finalMatch = koMatches.get('Final')?.[0];

  return (
    <div className="space-y-8">
      {/* Group Stage */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-slate-800">Group Stage</h2>
          <button
            onClick={onAboutClick}
            className="text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            About 2022 predictions
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
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
                <div className={`px-3 py-2 ${isSelected ? 'bg-green-600' : 'bg-slate-700'} transition-colors`}>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">Group {g}</h3>
                </div>
                <div className="p-2.5 space-y-1.5">
                  {teams.map(t => (
                    <div key={t.name} className="flex items-center gap-1.5 text-xs text-slate-700">
                      <span>{t.flag}</span>
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
            {(groupMatches.get(selectedGroup) ?? []).map(m => (
              <GroupMatchRow key={m.matchId} match={m} onClick={() => onMatchClick(m.matchId, '2022')} />
            ))}
          </div>
        )}
      </section>

      {/* Knockout bracket — what actually happened */}
      <section>
        <h2 className="text-base font-bold text-slate-800 mb-4">What Actually Happened</h2>
        <div className="space-y-6">
          {KO_ROUNDS.map(round => {
            const matches = koMatches.get(round) ?? [];
            if (matches.length === 0) return null;
            const isFinal = round === 'Final';
            const is3rd = round === 'Match for third place';

            return (
              <div key={round}>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  {KO_LABELS[round]}
                </h3>
                <div className={`grid gap-3 ${
                  isFinal || is3rd         ? 'grid-cols-1 max-w-xs' :
                  round === 'Semi-final'   ? 'grid-cols-1 sm:grid-cols-2 max-w-2xl' :
                                             'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
                }`}>
                  {matches.map(m => (
                    <KOMatchCard
                      key={m.matchId}
                      match={m}
                      isChampion={isFinal && m.matchId === finalMatch?.matchId}
                      onClick={() => onMatchClick(m.matchId, '2022')}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
