import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';
import { ADVANCED_ONLY_KEYS } from '../lib/metrics';
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

async function fetchRows(entity: Entity, season: string, seasonType: string, signal: AbortSignal): Promise<AnalyticsRow[]> {
    const { basic, advanced } = ENDPOINTS[entity];
    const query = `season_name=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`;

    const [basicRows, advancedRows] = await Promise.all([
        apiFetch(`/api/nba/db/${basic}?${query}`, { signal }).then(r => r.json()),
        apiFetch(`/api/nba/db/${advanced}?${query}`, { signal }).then(r => r.json()),
    ]);

    if (!Array.isArray(basicRows)) return [];

    const byId = new Map<number, AdvancedRow>(
        (Array.isArray(advancedRows) ? advancedRows : []).map(
            (row: AdvancedRow) => [advancedId(row), row],
        ),
    );

    return entity === 'player'
        ? basicRows.map((row: SeasonPlayerStats) => fillGaps(playerBase(row), byId.get(row.player_id)))
        : basicRows.map((row: SeasonTeamStats) => fillGaps(teamBase(row), byId.get(row.team_id)));
}

/**
 * Every metric in the registry for one entity-season, from the two endpoints merged.
 * `loading` is derived from the request key, so a stale season's rows never read as settled.
 */
export function useAnalyticsRows(entity: Entity, season: string | null, seasonType: string) {
    const key = `${entity}|${season}|${seasonType}`;
    const [loaded, setLoaded] = useState<Loaded | null>(null);

    useEffect(() => {
        if (!season) return;

        let cancelled = false;
        const controller = new AbortController();

        fetchRows(entity, season, seasonType, controller.signal)
            .then(rows => { if (!cancelled) setLoaded({ key, rows, error: null }); })
            .catch((error: Error) => {
                if (cancelled || error.name === 'AbortError') return;
                setLoaded({ key, rows: [], error: error.message || 'Could not load stats.' });
            });

        return () => { cancelled = true; controller.abort(); };
    }, [key, entity, season, seasonType]);

    const settled = loaded?.key === key;
    return {
        rows: settled ? loaded.rows : [],
        loading: season !== null && !settled,
        error: settled ? loaded.error : null,
    };
}
