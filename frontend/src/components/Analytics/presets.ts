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
