import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';
import { ADVANCED_ONLY_KEYS, DERIVED_KEYS, hasDerived, type DerivedKey, type MetricKey } from '../lib/metrics';
import type { AdvancedOnlyKey, AnalyticsRow } from '../types/analytics';
import type { SeasonPlayerStats } from '../types/player';
import type { SeasonTeamStats } from '../types/team';
import type { SeasonAdvancedPlayerStats, SeasonAdvancedTeamStats } from '../types/stats';

type Entity = 'player' | 'team';
type AdvancedRow = SeasonAdvancedPlayerStats | SeasonAdvancedTeamStats;

function advancedId(row: AdvancedRow): number {
    return 'player_id' in row ? row.player_id : row.team_id;
}

interface Loaded {
    key: string;
    rows: AnalyticsRow[];
    error: string | null;
}

const ENDPOINTS: Record<Entity, { basic: string; advanced: string }> = {
    player: { basic: 'season_player_stats', advanced: 'season_advanced_player_stats' },
    team: { basic: 'season_team_stats', advanced: 'season_advanced_team_stats' },
};

function playerBase(row: SeasonPlayerStats): AnalyticsRow {
    // season_player_stats groups by player and season, so it carries no team at all;
    // the abbreviation on the advanced row is the only one available.
    return { ...row, id: row.player_id, name: row.player_name, team: null, position: row.position };
}

function teamBase(row: SeasonTeamStats): AnalyticsRow {
    return { ...row, id: row.team_id, name: row.team_name, team: row.team_id, position: null };
}

/** Advanced fills gaps only: a value the box-score row already has is kept. */
function fillGaps(base: AnalyticsRow, advanced: AdvancedRow | undefined): AnalyticsRow {
    if (!advanced) return base;

    const gaps: Partial<Record<AdvancedOnlyKey, number | null>> = {};
    for (const key of ADVANCED_ONLY_KEYS) {
        if (base[key] === null || base[key] === undefined) gaps[key] = advanced[key];
    }

    // Players carry no team on the box-score side, so the abbreviation is all there is.
    const team = base.team ?? ('team_abbreviation' in advanced ? advanced.team_abbreviation : null);

    return { ...base, ...gaps, team };
}

type DerivedRow = Record<string, unknown>;

const DERIVED: Record<Entity, { path: string; idKey: string }> = {
    player: { path: 'player_volatility', idKey: 'player_id' },
    team: { path: 'team_context', idKey: 'team_id' },
};

/** Derived metrics have their own endpoint per entity, keyed on that entity's id. */
async function fetchDerived(entity: Entity, season: string, seasonType: string, signal: AbortSignal): Promise<Map<number, DerivedRow>> {
    const { path, idKey } = DERIVED[entity];
    const query = `season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`;
    const body = await apiFetch(`/api/nba/analytics/${path}?${query}`, { signal }).then(r => r.json());
    const records: DerivedRow[] = body?.success && Array.isArray(body.records) ? body.records : [];
    return new Map(records.flatMap(row => (typeof row[idKey] === 'number' ? [[row[idKey] as number, row]] : [])));
}

function attachDerived(base: AnalyticsRow, extra: DerivedRow | undefined): AnalyticsRow {
    if (!extra) return base;

    const values: Partial<Record<DerivedKey, number | null>> = {};
    for (const key of DERIVED_KEYS) {
        if (key in extra) values[key] = typeof extra[key] === 'number' ? (extra[key] as number) : null;
    }
    const gamesRated = typeof extra.games_rated === 'number' ? extra.games_rated : null;

    return { ...base, ...values, games_rated: gamesRated };
}

async function fetchRows(
    entity: Entity,
    season: string,
    seasonType: string,
    withDerived: boolean,
    signal: AbortSignal,
): Promise<AnalyticsRow[]> {
    const { basic, advanced } = ENDPOINTS[entity];
    const query = `season_name=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`;

    const [basicRows, advancedRows, derived] = await Promise.all([
        apiFetch(`/api/nba/db/${basic}?${query}`, { signal }).then(r => r.json()),
        apiFetch(`/api/nba/db/${advanced}?${query}`, { signal }).then(r => r.json()),
        withDerived
            ? fetchDerived(entity, season, seasonType, signal)
            : Promise.resolve(new Map<number, DerivedRow>()),
    ]);

    if (!Array.isArray(basicRows)) return [];

    const byId = new Map<number, AdvancedRow>(
        (Array.isArray(advancedRows) ? advancedRows : []).map(
            (row: AdvancedRow) => [advancedId(row), row],
        ),
    );

    if (entity === 'team') {
        return basicRows.map((row: SeasonTeamStats) =>
            attachDerived(fillGaps(teamBase(row), byId.get(row.team_id)), derived.get(row.team_id)));
    }

    return basicRows.map((row: SeasonPlayerStats) =>
        attachDerived(fillGaps(playerBase(row), byId.get(row.player_id)), derived.get(row.player_id)));
}

/**
 * Every metric in the registry for one entity-season, from the two endpoints merged.
 * `loading` is derived from the request key, so a stale season's rows never read as settled.
 */
export function useAnalyticsRows(
    entity: Entity,
    season: string | null,
    seasonType: string,
    metrics: readonly MetricKey[] = [],
) {
    // Only fetch the extra endpoint when a derived metric is actually on screen.
    const withDerived = hasDerived(metrics);
    const key = `${entity}|${season}|${seasonType}|${withDerived}`;
    const [loaded, setLoaded] = useState<Loaded | null>(null);

    useEffect(() => {
        if (!season) return;

        let cancelled = false;
        const controller = new AbortController();

        fetchRows(entity, season, seasonType, withDerived, controller.signal)
            .then(rows => { if (!cancelled) setLoaded({ key, rows, error: null }); })
            .catch((error: Error) => {
                if (cancelled || error.name === 'AbortError') return;
                setLoaded({ key, rows: [], error: error.message || 'Could not load stats.' });
            });

        return () => { cancelled = true; controller.abort(); };
    }, [key, entity, season, seasonType, withDerived]);

    const settled = loaded?.key === key;
    return {
        rows: settled ? loaded.rows : [],
        loading: season !== null && !settled,
        error: settled ? loaded.error : null,
    };
}
