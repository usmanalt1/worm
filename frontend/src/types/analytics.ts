import type { AdvancedAverages, BoxScoreAverages } from './stats';

// The two interfaces disagree on the nullability of these, and the box-score row is the
// one that wins the merge, so the advanced side drops them.
export type AdvancedOnly = Omit<AdvancedAverages, 'games_played' | 'average_minutes'>;
export type AdvancedOnlyKey = keyof AdvancedOnly;

export type AnalyticsScope = 'player' | 'team' | 'season';
export type AnalyticsView = 'table' | 'scatter' | 'factors';

/** Metrics with their own endpoint, present only when one is selected. */
export interface DerivedMetrics {
    volatility: number | null;
    team_elo: number | null;
    opponent_elo: number | null;
    adj_margin: number | null;
    /** Games behind the derived metric, which can be fewer than games_played. */
    games_rated: number | null;
}

/** One entity-season, box score merged with advanced. Advanced may be absent. */
export interface AnalyticsRow extends BoxScoreAverages, Partial<AdvancedOnly>, Partial<DerivedMetrics> {
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
