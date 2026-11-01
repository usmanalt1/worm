import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';
import type { SeasonPlayerStats } from '../types/player';
import type { SeasonTeamStats } from '../types/team';

interface Loaded<T> {
    rows: T[];
    loading: boolean;
}

function useSeasonRows<T>(endpoint: string, season: string | null, seasonType: string): Loaded<T> {
    const [state, setState] = useState<Loaded<T>>({ rows: [], loading: true });

    useEffect(() => {
        if (!season) return;
        let cancelled = false;

        apiFetch(`/api/nba/db/${endpoint}?season_name=${season}&season_type=${seasonType}`)
            .then(r => r.json())
            .then((rows: T[]) => {
                if (!cancelled) setState({ rows: Array.isArray(rows) ? rows : [], loading: false });
            })
            .catch(() => { if (!cancelled) setState({ rows: [], loading: false }); });

        return () => { cancelled = true; };
    }, [endpoint, season, seasonType]);

    return state;
}

export function useSeasonPlayerStats(season: string | null, seasonType = 'regular') {
    return useSeasonRows<SeasonPlayerStats>('season_player_stats', season, seasonType);
}

export function useSeasonTeamStats(season: string | null, seasonType = 'regular') {
    return useSeasonRows<SeasonTeamStats>('season_team_stats', season, seasonType);
}
