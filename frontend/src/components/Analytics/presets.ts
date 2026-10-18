/**
 * A preset is a named URL state, not a mode: clicking one writes these params and
 * nudging any control from there leaves a custom view on the same render path.
 */
export interface Preset {
    id: string;
    title: string;
    blurb: string;
    params: Record<string, string>;
}

export const PRESETS: Preset[] = [
    {
        id: 'four_factors',
        title: 'Four Factors',
        blurb: 'Shooting, turnovers, boards and free throws — what each team is worst at.',
        params: {
            scope: 'team',
            view: 'factors',
            metrics: 'effective_field_goal_percentage,turnover_percentage,offensive_rebound_percentage',
        },
    },
    {
        id: 'volatility',
        title: 'Boom or bust',
        blurb: 'Whose output you can set a watch by, and whose you cannot.',
        params: {
            scope: 'player',
            view: 'table',
            metrics: 'volatility,average_points,usage_percentage,average_minutes',
        },
    },
    {
        id: 'quadrant',
        title: 'Team quadrant',
        blurb: 'Offence against defence. Up and right is a contender.',
        params: {
            scope: 'team',
            view: 'scatter',
            x: 'offensive_rating',
            y: 'defensive_rating',
            metrics: 'wins,losses,offensive_rating,defensive_rating,net_rating',
        },
    },
    {
        id: 'schedule',
        title: 'Who had it easy',
        blurb: 'Elo against strength of schedule, and the margin it was worth.',
        params: {
            scope: 'team',
            view: 'scatter',
            x: 'opponent_elo',
            y: 'team_elo',
            metrics: 'team_elo,opponent_elo,adj_margin,average_plus_minus,wins',
        },
    },
    {
        id: 'efficiency',
        title: 'Player efficiency',
        blurb: 'Who carries a heavy load without wasting it.',
        params: {
            scope: 'player',
            view: 'scatter',
            x: 'usage_percentage',
            y: 'true_shooting_percentage',
            metrics: 'average_points,usage_percentage,true_shooting_percentage,average_minutes',
        },
    },
    {
        id: 'trends',
        title: 'League trends',
        blurb: 'Pace, scoring and the three-point share, season by season.',
        params: { scope: 'season', view: 'table' },
    },
];
