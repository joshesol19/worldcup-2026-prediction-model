import type {
  Match2026, GroupStanding,
} from '../types';

const FLAGS: Record<string, string> = {
  Mexico: '🇲🇽', 'South Africa': '🇿🇦', 'South Korea': '🇰🇷',
  'Czech Republic': '🇨🇿', Canada: '🇨🇦', 'Bosnia & Herzegovina': '🇧🇦',
  'Bosnia and Herzegovina': '🇧🇦', Qatar: '🇶🇦', Switzerland: '🇨🇭',
  'United States': '🇺🇸', USA: '🇺🇸', Panama: '🇵🇦',
  Argentina: '🇦🇷', Ecuador: '🇪🇨', Colombia: '🇨🇴', Uruguay: '🇺🇾',
  Brazil: '🇧🇷', Paraguay: '🇵🇾', Germany: '🇩🇪', France: '🇫🇷',
  Spain: '🇪🇸', Portugal: '🇵🇹', England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', Netherlands: '🇳🇱',
  Belgium: '🇧🇪', Italy: '🇮🇹', Croatia: '🇭🇷', Denmark: '🇩🇰',
  Austria: '🇦🇹', Scotland: '🏴󠁧󠁢󠁳󠁣󠁴󠁿', Serbia: '🇷🇸', Poland: '🇵🇱',
  Turkey: '🇹🇷', Norway: '🇳🇴', Sweden: '🇸🇪', Morocco: '🇲🇦',
  Senegal: '🇸🇳', Tunisia: '🇹🇳', Ghana: '🇬🇭', Nigeria: '🇳🇬',
  Egypt: '🇪🇬', Algeria: '🇩🇿', 'Ivory Coast': '🇨🇮', Japan: '🇯🇵',
  Australia: '🇦🇺', Iran: '🇮🇷', 'Saudi Arabia': '🇸🇦', Uzbekistan: '🇺🇿',
  Jordan: '🇯🇴', Iraq: '🇮🇶', 'New Zealand': '🇳🇿', 'DR Congo': '🇨🇩',
  'Cape Verde': '🇨🇻', 'Curaçao': '🇨🇼', Haiti: '🇭🇹',
};

export function getFlag(name: string): string {
  return FLAGS[name] ?? '🏳️';
}

// ── Group standings computation ─────────────────────────────────────────────

interface Standing {
  name: string;
  pts: number;
  gd: number;
  gf: number;
  played: number;
  elo: number | null;
}

export function computeGroupStandings(
  matches: Match2026[],
): Map<string, GroupStanding[]> {
  const groups = new Map<string, Map<string, Standing>>();

  for (const m of matches) {
    if (!m.group || m.status !== 'predicted' || !m.probabilities) continue;

    const g = m.group;
    if (!groups.has(g)) groups.set(g, new Map());
    const table = groups.get(g)!;

    const t1 = m.team1.name;
    const t2 = m.team2.name;
    if (!table.has(t1))
      table.set(t1, { name: t1, pts: 0, gd: 0, gf: 0, played: 0, elo: m.teamStats?.team1.eloRating ?? null });
    if (!table.has(t2))
      table.set(t2, { name: t2, pts: 0, gd: 0, gf: 0, played: 0, elo: m.teamStats?.team2.eloRating ?? null });

    const s1 = table.get(t1)!;
    const s2 = table.get(t2)!;
    s1.played++;
    s2.played++;

    const { team1Win: p1, draw: pd, team2Win: p2 } = m.probabilities;
    if (p1 >= pd && p1 >= p2) {
      s1.pts += 3; s1.gd += 1; s2.gd -= 1; s1.gf += 1;
    } else if (pd >= p1 && pd >= p2) {
      s1.pts += 1; s2.pts += 1;
    } else {
      s2.pts += 3; s2.gd += 1; s1.gd -= 1; s2.gf += 1;
    }
  }

  const result = new Map<string, GroupStanding[]>();
  for (const [group, table] of groups) {
    const sorted = [...table.values()].sort((a, b) =>
      b.pts !== a.pts ? b.pts - a.pts : b.gd !== a.gd ? b.gd - a.gd : b.gf - a.gf
    );
    result.set(group, sorted.map(s => ({
      name: s.name,
      flag: getFlag(s.name),
      pts: s.pts,
      gd: s.gd,
      played: s.played,
      elo: s.elo,
    })));
  }
  return result;
}

// ── Team Elo lookup ──────────────────────────────────────────────────────────

export function buildTeamEloMap(matches: Match2026[]): Map<string, number | null> {
  const map = new Map<string, number | null>();
  for (const m of matches) {
    if (m.teamStats) {
      if (!map.has(m.team1.name)) map.set(m.team1.name, m.teamStats.team1.eloRating);
      if (!map.has(m.team2.name)) map.set(m.team2.name, m.teamStats.team2.eloRating);
    }
  }
  return map;
}

