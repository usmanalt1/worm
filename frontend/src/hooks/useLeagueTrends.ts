import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';
import type { LeagueTrendPoint } from '../types/analytics';

interface Loaded {
    key: string;
    points: LeagueTrendPoint[];
}

interface TrendsResponse {
    success: boolean;
    error?: string | null;
    records?: LeagueTrendPoint[] | null;
}

/** League scoring, three-point share and pace by season, oldest first. */
export function useLeagueTrends(seasonType = 'regular') {
    const [loaded, setLoaded] = useState<Loaded | null>(null);

    useEffect(() => {
        let cancelled = false;

        apiFetch(`/api/nba/analytics/league_trends?season_type=${seasonType}`)
            .then(r => r.json())
            .then((data: TrendsResponse) => {
                if (cancelled) return;
                setLoaded({ key: seasonType, points: data.success ? data.records ?? [] : [] });
            })
            .catch(() => { if (!cancelled) setLoaded({ key: seasonType, points: [] }); });

        return () => { cancelled = true; };
    }, [seasonType]);

    const settled = loaded?.key === seasonType;
    return { points: settled ? loaded.points : [], loading: !settled };
}
