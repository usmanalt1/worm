import type { AdvancedAverages, BoxScoreAverages } from '../types/stats';
import type { AdvancedOnlyKey } from '../types/analytics';

export type MetricKey = keyof BoxScoreAverages | keyof AdvancedAverages;
export type MetricKind = 'plain' | 'percent' | 'signed' | 'count';
export type MetricGroup = 'box' | 'advanced';
export type MetricEntity = 'player' | 'both';

export interface MetricSpec {
    key: MetricKey;
    title: string;
    description: string;
    group: MetricGroup;
    entity: MetricEntity;
    kind: MetricKind;
    /** Drives rank direction, leaderboard bars and scatter axis inversion. */
    higherIsBetter: boolean;
}

// games_played and average_minutes come from both endpoints, so they appear once here
// and in both ordered lists below.
export const METRICS: MetricSpec[] = [
    { key: 'games_played', title: 'GP', kind: 'count', group: 'box', entity: 'both', higherIsBetter: true, description: 'Games played' },
    { key: 'average_minutes', title: 'MIN', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Minutes per game' },
    { key: 'average_points', title: 'PTS', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Points per game' },
    { key: 'average_field_goals_made', title: 'FGM', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Field goals made per game' },
    { key: 'average_field_goals_attempted', title: 'FGA', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Field goals attempted per game' },
    { key: 'field_goal_pct', title: 'FG%', kind: 'percent', group: 'box', entity: 'both', higherIsBetter: true, description: 'Field goal percentage, from season totals' },
    { key: 'average_three_pointers_made', title: '3PM', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Three pointers made per game' },
    { key: 'average_three_pointers_attempted', title: '3PA', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Three pointers attempted per game' },
    { key: 'three_point_pct', title: '3P%', kind: 'percent', group: 'box', entity: 'both', higherIsBetter: true, description: 'Three point percentage, from season totals' },
    { key: 'average_free_throws_made', title: 'FTM', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Free throws made per game' },
    { key: 'average_free_throws_attempted', title: 'FTA', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Free throws attempted per game' },
    { key: 'free_throw_pct', title: 'FT%', kind: 'percent', group: 'box', entity: 'both', higherIsBetter: true, description: 'Free throw percentage, from season totals' },
    { key: 'average_offensive_rebounds', title: 'OREB', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Offensive rebounds per game' },
    { key: 'average_defensive_rebounds', title: 'DREB', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Defensive rebounds per game' },
    { key: 'average_rebounds', title: 'REB', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Total rebounds per game' },
    { key: 'average_assists', title: 'AST', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Assists per game' },
    { key: 'average_steals', title: 'STL', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Steals per game' },
    { key: 'average_blocks', title: 'BLK', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: true, description: 'Blocks per game' },
    { key: 'average_turnovers', title: 'TOV', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: false, description: 'Turnovers per game' },
    { key: 'average_fouls', title: 'PF', kind: 'plain', group: 'box', entity: 'both', higherIsBetter: false, description: 'Personal fouls per game' },
    { key: 'average_plus_minus', title: '+/-', kind: 'signed', group: 'box', entity: 'both', higherIsBetter: true, description: 'Plus/minus: average scoring margin while on court' },

    { key: 'wins', title: 'W', kind: 'count', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Wins' },
    { key: 'losses', title: 'L', kind: 'count', group: 'advanced', entity: 'both', higherIsBetter: false, description: 'Losses' },
    { key: 'offensive_rating', title: 'ORTG', kind: 'plain', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Offensive rating: points scored per 100 possessions' },
    { key: 'defensive_rating', title: 'DRTG', kind: 'plain', group: 'advanced', entity: 'both', higherIsBetter: false, description: 'Defensive rating: points allowed per 100 possessions' },
    { key: 'net_rating', title: 'NETRTG', kind: 'signed', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Net rating: offensive minus defensive rating' },
    { key: 'true_shooting_percentage', title: 'TS%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'True shooting %: efficiency counting free throws and threes' },
    { key: 'effective_field_goal_percentage', title: 'EFG%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Effective field goal %: field goal % weighting threes' },
    { key: 'usage_percentage', title: 'USG%', kind: 'percent', group: 'advanced', entity: 'player', higherIsBetter: true, description: 'Usage %: share of team possessions used' },
    { key: 'assist_percentage', title: 'AST%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Assist %: share of teammate field goals assisted' },
    { key: 'assist_ratio', title: 'AST RT', kind: 'plain', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Assist ratio: assists per 100 possessions used' },
    { key: 'assist_to_turnover', title: 'AST/TO', kind: 'plain', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Assists per turnover' },
    { key: 'turnover_percentage', title: 'TOV%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: false, description: 'Turnover %: turnovers per 100 possessions' },
    { key: 'offensive_rebound_percentage', title: 'OREB%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Offensive rebound %: share of available offensive rebounds' },
    { key: 'defensive_rebound_percentage', title: 'DREB%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Defensive rebound %: share of available defensive rebounds' },
    { key: 'rebound_percentage', title: 'REB%', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Rebound %: share of all available rebounds' },
    { key: 'pace', title: 'PACE', kind: 'plain', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Pace: possessions per 48 minutes' },
    { key: 'possessions', title: 'POSS', kind: 'plain', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Possessions per game' },
    { key: 'pie', title: 'PIE', kind: 'percent', group: 'advanced', entity: 'both', higherIsBetter: true, description: 'Player impact estimate: share of game events contributed' },
];

const BY_KEY = new Map<string, MetricSpec>(METRICS.map(spec => [spec.key, spec]));

export function metricSpec(key: string): MetricSpec | undefined {
    return BY_KEY.get(key);
}

/** Standard box-score reading order, for the basic tables. */
export const BOX_SCORE_KEYS: MetricKey[] = METRICS
    .filter(spec => spec.group === 'box')
    .map(spec => spec.key);

/** Record and minutes, then the ratings, then efficiency and usage shares. */
export const ADVANCED_KEYS: MetricKey[] = [
    'games_played',
    'wins',
    'losses',
    'average_minutes',
    ...METRICS.filter(spec => spec.group === 'advanced' && spec.key !== 'wins' && spec.key !== 'losses').map(spec => spec.key),
];

/**
 * The keys the advanced endpoint is the only source of, for the row merge. Every
 * `advanced` entry is one by construction, which `filter` cannot prove.
 */
export const ADVANCED_ONLY_KEYS = METRICS
    .filter(spec => spec.group === 'advanced')
    .map(spec => spec.key) as AdvancedOnlyKey[];

export function metricsForEntity(entity: 'player' | 'team'): MetricSpec[] {
    return entity === 'player' ? METRICS : METRICS.filter(spec => spec.entity === 'both');
}

/**
 * Keys from a URL, deduped and filtered to ones that exist, so a hand-edited address
 * falls back instead of rendering a broken table.
 */
export function parseMetricKeys(raw: string | null | undefined, fallback: MetricKey[]): MetricKey[] {
    const keys = (raw ?? '')
        .split(',')
        .map(part => part.trim())
        .filter(part => BY_KEY.has(part)) as MetricKey[];

    return keys.length > 0 ? [...new Set(keys)] : fallback;
}
