export interface TeamInfo {
  name: string;
  flag: string;
}

export interface Probabilities {
  team1Win: number;
  draw: number;
  team2Win: number;
}

export interface ShapFeature {
  feature: string;
  rawFeature: string;
  direction: 'favors_team1' | 'favors_team2';
  magnitude: number;
}

export interface TeamStats {
  eloRating: number | null;
  fifaRank: number | null;
  last10Pts: number | null;
  last5Gd: number | null;
  squadValueM: number | null;
}

export interface TeamStatsPair {
  team1: TeamStats;
  team2: TeamStats;
}

export interface Score {
  team1: number | null;
  team2: number | null;
}

export type PredictionStatus = 'correct' | 'incorrect' | 'draw_miss';
export type OutcomeLabel = 'team1' | 'draw' | 'team2';
export type MatchStatus = 'predicted' | 'pending' | 'no_data';
export type Confidence = 'low' | 'moderate' | 'high';

export interface Match2026 {
  matchId: string;
  date: string;
  time: string;
  venue: string;
  group: string;
  round: string;
  stage: string;
  team1: TeamInfo;
  team2: TeamInfo;
  status: MatchStatus;
  probabilities: Probabilities | null;
  predictedOutcome: OutcomeLabel | null;
  confidence: Confidence | null;
  shapFeatures: ShapFeature[];
  teamStats: TeamStatsPair | null;
  neutral?: number;
}

export interface Match2022 {
  matchId: string;
  date: string;
  group: string;
  round: string;
  stage: string;
  team1: TeamInfo;
  team2: TeamInfo;
  probabilities: Probabilities | null;
  predictedOutcome: OutcomeLabel | null;
  actualOutcome: OutcomeLabel | null;
  actualScore: Score | null;
  predictionStatus: PredictionStatus | null;
  confidence: Confidence | null;
  shapFeatures: ShapFeature[];
  teamStats: TeamStatsPair | null;
}

export interface Summary2022 {
  correct: number;
  incorrect: number;
  drawMiss: number;
  total: number;
}

export interface Cache2026 {
  generatedAt: string;
  matchCount: number;
  modelAccuracy: number;
  matches: Match2026[];
  bracketMatches: Match2026[];
}

export interface Cache2022 {
  generatedAt: string;
  matchCount: number;
  modelAccuracy: number;
  computedAccuracy: number;
  summary: Summary2022;
  matches: Match2022[];
}

// Raw fixture format from openfootball JSON
export interface FixtureMatch {
  num?: number;
  round: string;
  date: string;
  time?: string;
  team1: string;
  team2: string;
  group?: string;
  ground?: string;
}

export interface FixtureData {
  name: string;
  matches: FixtureMatch[];
}

// Bracket types
export interface GroupStanding {
  name: string;
  flag: string;
  pts: number;
  gd: number;
  played: number;
  elo: number | null;
}

export interface BracketTeam {
  name: string;
  flag: string;
  elo: number | null;
}

export interface BracketMatch {
  num: number;
  round: string;
  date: string;
  team1: BracketTeam | null;
  team2: BracketTeam | null;
  p1: number | null;
  p2: number | null;
  winner: BracketTeam | null;
}
