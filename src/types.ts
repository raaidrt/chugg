export type Side = 'w' | 'b';

export interface OpeningLine {
  id: string;
  familyId: string;
  family: string;
  name: string;
  eco: string;
  moves: string[];
  popularity: number;
  description: string;
}

export interface DrillResult {
  lineId: string;
  side: Side;
  mistakes: number;
  hints: number;
  completedAt: number;
}

export interface LineProgress {
  lineId: string;
  side: Side;
  completions: number;
  cleanCompletions: number;
  lastCompletedAt: number;
  lastMistakes: number;
  lastHints: number;
}

export interface Preferences {
  side: Side;
  familyId: string;
}
