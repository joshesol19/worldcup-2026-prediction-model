import { useMemo } from 'react';
import type { Cache2026, Match2026, GroupStanding } from '../types';
import { computeGroupStandings } from '../utils/bracket';

const ROUND_ORDER = [
  'Round of 32', 'Round of 16', 'Quarter-final',
  'Semi-final', 'Match for third place', 'Final',
];

// Desired display order within each round (by fixture number extracted from matchId).
// R32: pairs are grouped so that winners of consecutive pairs meet in R16, and so on.
const ROUND_DISPLAY_ORDER: Record<string, number[]> = {
  'Round of 32':  [74, 77, 73, 75, 83, 84, 81, 82, 76, 78, 79, 80, 86, 88, 85, 87],
  'Round of 16':  [89, 90, 93, 94, 91, 92, 95, 96],
  'Quarter-final':[97, 98, 99, 100],
};

function bracketNum(matchId: string): number {
  const m = matchId.match(/bracket_(\d+)/);
  return m ? parseInt(m[1], 10) : 0;
}

function sortByDisplayOrder(matches: Match2026[], order: number[]): Match2026[] {
  return [...matches].sort((a, b) => {
    const ai = order.indexOf(bracketNum(a.matchId));
    const bi = order.indexOf(bracketNum(b.matchId));
    if (ai === -1 && bi === -1) return 0;
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}
const ROUND_LABELS: Record<string, string> = {
  'Round of 32':          'Round of 32',
  'Round of 16':          'Round of 16',
  'Quarter-final':        'Quarter-Finals',
  'Semi-final':           'Semi-Finals',
  'Match for third place':'Third Place',
  'Final':                'The Final',
};

interface GroupCardProps { group: string; standings: GroupStanding[] }

function GroupCard({ group, standings }: GroupCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="bg-green-600 px-3 py-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-white">{group}</h3>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-400 border-b border-slate-100">
            <th className="text-left px-3 py-1.5 font-medium w-5">#</th>
            <th className="text-left px-1 py-1.5 font-medium">Team</th>
            <th className="px-2 py-1.5 font-medium text-center">Pts</th>
            <th className="px-2 py-1.5 font-medium text-center">GD</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((t, i) => (
            <tr key={t.name} className={`border-b border-slate-50 last:border-0 ${i < 2 ? 'font-semibold' : 'text-slate-500'}`}>
              <td className="px-3 py-2">
                {i < 2 ? (
                  <span className="w-4 h-4 rounded-full bg-green-100 text-green-700 text-xs flex items-center justify-center font-bold">{i + 1}</span>
                ) : (
                  <span className="text-slate-400">{i + 1}</span>
                )}
              </td>
              <td className="px-1 py-2">
                <span className="mr-1.5">{t.flag}</span>
                <span className={i < 2 ? 'text-slate-800' : 'text-slate-500'}>{t.name}</span>
              </td>
              <td className={`text-center px-2 py-2 font-bold ${i < 2 ? 'text-green-700' : 'text-slate-400'}`}>{t.pts}</td>
              <td className="text-center px-2 py-2 text-slate-400">{t.gd > 0 ? `+${t.gd}` : t.gd}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-100">
        <p className="text-xs text-slate-400">Predicted to advance: top 2</p>
      </div>
    </div>
  );
}

interface BracketMatchCardProps {
  match: Match2026;
  isChampion?: boolean;
  onClick: () => void;
}

function BracketMatchCard({ match, isChampion, onClick }: BracketMatchCardProps) {
  const { team1, team2, probabilities: probs, predictedOutcome, status } = match;

  const winnerName =
    predictedOutcome === 'team1' ? team1.name :
    predictedOutcome === 'team2' ? team2.name :
    probs ? (probs.team1Win >= probs.team2Win ? team1.name : team2.name) :
    null;

  const tbd = (label: string) => (
    <div className="flex items-center gap-2 py-2 px-3 text-slate-400">
      <span className="text-lg">🏳️</span>
      <span className="text-sm italic">{label}</span>
    </div>
  );

  const teamRow = (
    team: { name: string; flag: string },
    prob: number | null,
    isWinner: boolean,
    side: 'top' | 'bottom',
  ) => (
    <div className={`flex items-center gap-2 py-2 px-3 transition-colors ${
      isWinner ? 'bg-green-50 border-l-2 border-green-500' : 'opacity-60'
    } ${side === 'top' ? 'border-b border-slate-100' : ''}`}>
      <span className="text-lg leading-none">{team.flag}</span>
      <span className={`text-sm flex-1 ${isWinner ? 'font-bold text-slate-900' : 'font-medium text-slate-500'}`}>
        {team.name}
      </span>
      {prob !== null && (
        <span className={`text-xs font-semibold ${isWinner ? 'text-green-700' : 'text-slate-400'}`}>
          {Math.round(prob * 100)}%
        </span>
      )}
      {isWinner && <span className="text-green-500 text-xs">✓</span>}
    </div>
  );

  const isPending = status === 'pending';

  return (
    <button
      onClick={isPending ? undefined : onClick}
      className={`w-full text-left bg-white border rounded-xl shadow-sm overflow-hidden transition-shadow ${
        isChampion ? 'border-yellow-400 ring-2 ring-yellow-200' : 'border-slate-200'
      } ${!isPending ? 'hover:shadow-md cursor-pointer' : 'cursor-default'}`}
    >
      {isChampion && (
        <div className="bg-yellow-400 text-center py-1">
          <span className="text-xs font-bold text-yellow-900">🏆 Predicted Champion</span>
        </div>
      )}
      {isPending ? (
        <>
          {tbd(team1.name || 'TBD')}
          {tbd(team2.name || 'TBD')}
        </>
      ) : (
        <>
          {teamRow(team1, probs?.team1Win ?? null, winnerName === team1.name, 'top')}
          {teamRow(team2, probs?.team2Win ?? null, winnerName === team2.name, 'bottom')}
        </>
      )}
    </button>
  );
}

interface Props {
  data2026: Cache2026;
  inline?: boolean;
  onBack: () => void;
  onMatchClick: (matchId: string, year: '2026' | '2022') => void;
}

export function BracketPage({ data2026, inline, onBack, onMatchClick }: Props) {
  const standings = useMemo(
    () => computeGroupStandings(data2026.matches),
    [data2026.matches],
  );

  const bracketMatches = data2026.bracketMatches ?? [];

  const finalMatch = bracketMatches.find(m => m.round === 'Final');
  const champion =
    finalMatch?.predictedOutcome === 'team1' ? finalMatch.team1 :
    finalMatch?.predictedOutcome === 'team2' ? finalMatch.team2 :
    finalMatch?.probabilities
      ? (finalMatch.probabilities.team1Win >= finalMatch.probabilities.team2Win
          ? finalMatch.team1 : finalMatch.team2)
      : null;

  const matchesByRound = new Map<string, Match2026[]>();
  for (const m of bracketMatches) {
    if (!matchesByRound.has(m.round)) matchesByRound.set(m.round, []);
    matchesByRound.get(m.round)!.push(m);
  }

  const sortedGroups = [...standings.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div className={inline ? '' : 'min-h-screen bg-slate-50'}>
      {!inline && (
        <div className="sticky top-0 z-20 bg-white border-b border-slate-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
            <button
              onClick={onBack}
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
            >
              ← Back
            </button>
            <span className="text-slate-300">|</span>
            <span className="text-sm font-semibold text-slate-800">⚽ Predicted Tournament Bracket</span>
            <span className="text-xs text-slate-400 ml-2">Based on current model predictions</span>
          </div>
        </div>
      )}

      <div className={`max-w-7xl mx-auto ${inline ? '' : 'px-4 py-8'} space-y-10`}>
        {champion && (
          <div className="bg-gradient-to-r from-yellow-400 to-amber-400 rounded-2xl p-6 text-center shadow-md">
            <p className="text-sm font-bold text-yellow-900 uppercase tracking-wider mb-2">
              🏆 Predicted World Cup Champion
            </p>
            <div className="flex items-center justify-center gap-3">
              <span className="text-5xl">{champion.flag}</span>
              <h1 className="text-4xl font-black text-yellow-900">{champion.name}</h1>
            </div>
          </div>
        )}

        <section>
          <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
            <span className="w-8 h-8 rounded-full bg-green-600 text-white text-sm flex items-center justify-center font-bold">1</span>
            Group Stage Predictions
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {sortedGroups.map(([group, table]) => (
              <GroupCard key={group} group={group} standings={table} />
            ))}
          </div>
        </section>

        {ROUND_ORDER.map((round, roundIdx) => {
          const raw = matchesByRound.get(round) ?? [];
          const order = ROUND_DISPLAY_ORDER[round];
          const roundMatches = order ? sortByDisplayOrder(raw, order) : raw;
          if (roundMatches.length === 0) return null;
          const isFinal = round === 'Final';
          const is3rd = round === 'Match for third place';

          return (
            <section key={round}>
              <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-green-600 text-white text-sm flex items-center justify-center font-bold">
                  {roundIdx + 2}
                </span>
                {ROUND_LABELS[round]}
              </h2>
              <div className={`grid gap-3 ${
                isFinal || is3rd ? 'grid-cols-1 max-w-sm mx-auto' :
                round === 'Semi-final' ? 'grid-cols-1 sm:grid-cols-2 max-w-2xl' :
                round === 'Quarter-final' ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4' :
                'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
              }`}>
                {roundMatches.map(m => (
                  <BracketMatchCard
                    key={m.matchId}
                    match={m}
                    isChampion={isFinal && m.matchId === finalMatch?.matchId}
                    onClick={() => onMatchClick(m.matchId, '2026')}
                  />
                ))}
              </div>
            </section>
          );
        })}

        <div className="text-xs text-slate-400 text-center pb-6">
          All predictions from our 43-feature ML model.{' '}
          <button
            onClick={() => (window as any).__navigateAbout?.()}
            className="text-blue-500 hover:underline"
          >
            Learn more
          </button>
        </div>
      </div>
    </div>
  );
}
