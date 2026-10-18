import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { metricSpec, metricsForEntity, parseMetricKeys, type MetricKey } from '../../lib/metrics';
import { useSeasonOptions } from '../../hooks/useSeasonOptions';
import { STAGES, type Stage } from '../ViewData/stages';
import type { AnalyticsScope, AnalyticsView } from '../../types/analytics';

/**
 * A one-game cameo would win every rate board, so each stage carries its own floor.
 * Kept visible in the UI because nobody clears 20 games in October.
 */
export const MIN_GAMES: Record<Stage, number> = { Regular: 20, Playoffs: 5, Preseason: 3 };

const SCOPES: AnalyticsScope[] = ['player', 'team', 'season'];
const VIEWS: AnalyticsView[] = ['table', 'scatter'];

const DEFAULT_METRICS: Record<'player' | 'team', MetricKey[]> = {
    player: ['average_points', 'average_rebounds', 'average_assists', 'true_shooting_percentage', 'usage_percentage'],
    team: ['wins', 'losses', 'offensive_rating', 'defensive_rating', 'net_rating'],
};

const DEFAULT_AXES: Record<'player' | 'team', { x: MetricKey; y: MetricKey }> = {
    player: { x: 'usage_percentage', y: 'true_shooting_percentage' },
    team: { x: 'offensive_rating', y: 'defensive_rating' },
};

export interface AnalyticsQuery {
    scope: AnalyticsScope;
    /** 'player' or 'team'; season scope reads as 'team' since it aggregates team rows. */
    entity: 'player' | 'team';
    season: string | null;
    stage: Stage;
    seasonType: string;
    minGames: number;
    view: AnalyticsView;
    metrics: MetricKey[];
    x: MetricKey;
    y: MetricKey;
    preset: string | null;
}

type Patch = Record<string, string | null>;

function oneOf<T extends string>(raw: string | null, allowed: T[], fallback: T): T {
    return allowed.includes(raw as T) ? (raw as T) : fallback;
}

function axis(raw: string | null, entity: 'player' | 'team', fallback: MetricKey): MetricKey {
    const spec = raw ? metricSpec(raw) : undefined;
    if (!spec) return fallback;
    return spec.entity === 'player' && entity === 'team' ? fallback : spec.key;
}

/**
 * The page's whole state, parsed from the URL and validated, so a hand-edited address
 * falls back rather than crashing. Every setter writes back to the URL.
 *
 * Owns the season list too: the options depend on the stage, and the stage comes from
 * the same URL the season is validated against.
 */
export function useAnalyticsQuery() {
    const [params, setParams] = useSearchParams();
    const stage = oneOf(params.get('stage'), STAGES, 'Regular');
    const seasons = useSeasonOptions(stage.toLowerCase());

    const patch = useCallback((changes: Patch, replace = false) => {
        setParams(prev => {
            const next = new URLSearchParams(prev);
            for (const [key, value] of Object.entries(changes)) {
                if (value === null) next.delete(key);
                else next.set(key, value);
            }
            return next;
        }, { replace });
    }, [setParams]);

    const query = useMemo<AnalyticsQuery>(() => {
        const scope = oneOf(params.get('scope'), SCOPES, 'player');
        const entity: 'player' | 'team' = scope === 'player' ? 'player' : 'team';

        const allowed = new Set(metricsForEntity(entity).map(spec => spec.key));
        const requested = parseMetricKeys(params.get('metrics'), DEFAULT_METRICS[entity]);
        const metrics = requested.filter(key => allowed.has(key));

        const rawFloor = Number(params.get('min_games'));
        const requestedSeason = params.get('season');

        return {
            scope,
            entity,
            // An unknown season falls back to the newest rather than an empty table.
            season: requestedSeason && seasons.includes(requestedSeason)
                ? requestedSeason
                : seasons[0] ?? null,
            stage,
            seasonType: stage.toLowerCase(),
            minGames: Number.isFinite(rawFloor) && rawFloor >= 0 ? Math.floor(rawFloor) : MIN_GAMES[stage],
            view: oneOf(params.get('view'), VIEWS, 'table'),
            metrics: metrics.length > 0 ? metrics : DEFAULT_METRICS[entity],
            x: axis(params.get('x'), entity, DEFAULT_AXES[entity].x),
            y: axis(params.get('y'), entity, DEFAULT_AXES[entity].y),
            preset: params.get('preset'),
        };
    }, [params, seasons, stage]);

    // Redefining what is plotted drops the preset badge; changing which slice keeps it.
    const setScope = useCallback((scope: AnalyticsScope) => {
        patch({ scope, metrics: null, x: null, y: null, preset: null });
    }, [patch]);

    const setView = useCallback((view: AnalyticsView) => patch({ view, preset: null }), [patch]);
    const setMetrics = useCallback((keys: MetricKey[]) => {
        patch({ metrics: keys.join(','), preset: null }, true);
    }, [patch]);
    const setAxes = useCallback((x: MetricKey, y: MetricKey) => patch({ x, y, preset: null }), [patch]);

    const setSeason = useCallback((season: string | null) => patch({ season }), [patch]);
    const setStage = useCallback((stage: Stage) => {
        // The floor is stage-specific, so a hand-set one does not follow you across stages.
        patch({ stage, min_games: null });
    }, [patch]);
    const setMinGames = useCallback((value: number) => {
        patch({ min_games: String(Math.max(0, Math.floor(value))) }, true);
    }, [patch]);

    const applyPreset = useCallback((changes: Patch & { preset: string }) => patch(changes), [patch]);

    return { query, seasons, setScope, setView, setMetrics, setAxes, setSeason, setStage, setMinGames, applyPreset };
}
