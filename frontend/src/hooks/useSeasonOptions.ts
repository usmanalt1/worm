import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';
import type { SeasonOption } from '../types/player';

/** Seasons with recorded stats for this stage, newest first, for a season picker. */
export function useSeasonOptions(seasonType = 'regular'): string[] {
    const [seasons, setSeasons] = useState<string[]>([]);

    useEffect(() => {
        let cancelled = false;

        apiFetch(`/api/nba/db/list_all_seasons?has_stats=true&season_type=${seasonType}`)
            .then(r => r.json())
            .then((rows: SeasonOption[]) => {
                if (cancelled || !Array.isArray(rows)) return;
                const names = rows.map(row => String(row.season_name));
                setSeasons([...names].sort((a, b) => b.localeCompare(a)));
            })
            .catch(() => { /* callers fall back to an empty picker */ });

        return () => { cancelled = true; };
    }, [seasonType]);

    return seasons;
}
