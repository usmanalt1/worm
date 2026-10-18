import type { AdvancedAverages, BoxScoreAverages } from './stats';

// The two interfaces disagree on the nullability of these, and the box-score row is the
// one that wins the merge, so the advanced side drops them.
export type AdvancedOnly = Omit<AdvancedAverages, 'games_played' | 'average_minutes'>;
export type AdvancedOnlyKey = keyof AdvancedOnly;

export type AnalyticsScope = 'player' | 'team' | 'season';
export type AnalyticsView = 'table' | 'scatter';

/** One entity-season, box score merged with advanced. Advanced may be absent. */
export interface AnalyticsRow extends BoxScoreAverages, Partial<AdvancedOnly> {
    id: number;
    name: string;
    /** Colour key: an abbreviation for players, a team id for teams. */
    team: string | number | null;
    position: string | null;
}

export interface LeagueTrendPoint {
    season: string;
    points_per_game: number | null;
    three_point_attempt_share: number | null;
    pace: number | null;
}
