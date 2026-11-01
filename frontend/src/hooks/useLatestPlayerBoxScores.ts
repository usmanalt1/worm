import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

export interface PlayerOption {
    player_id: number;
    player_name: string;
    team_abbreviation: string;
    matchip: string;
    points: number;
    rebounds: number;
    assists: number;
}

export function useLatestPlayerBoxScores() {
    const [players, setPlayers] = useState<PlayerOption[]>([]);

    useEffect(() => {
        let cancelled = false;

        apiFetch(`/api/nba/db/get_latest_top_players`)
            .then(r => r.json())
            .then((player_box_scores: PlayerOption[]) => {
                if (cancelled || !Array.isArray(player_box_scores) || player_box_scores.length === 0) return;
                setPlayers(player_box_scores);
            })
            .catch(() => { /* callers render their empty state */ });

        return () => { cancelled = true; };
    }, []);

    return players;
}
