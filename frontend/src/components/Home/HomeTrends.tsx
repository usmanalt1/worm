import { useEffect, useState } from "react";
import type { RankedPlayerStats } from '../../types/player';
import { Leaderboard, type LeaderboardRow } from '../ui/Leaderboard';
import { apiFetch } from '../../lib/api';
import { env } from '../../env';

type StatKey = 'rebounds' | 'points' | 'assists';

const STAT_CONFIG: Record<StatKey, { title: string; valueKey: keyof RankedPlayerStats; rankKey: keyof RankedPlayerStats }> = {
    // Rebounds lead the row — it is the board the app is named after.
    rebounds: { title: 'The Glass — Rebounds', valueKey: 'average_rebounds', rankKey: 'rank_average_rebounds' },
    points: { title: 'Points Per Game', valueKey: 'average_points', rankKey: 'rank_average_points' },
    assists: { title: 'Assists Per Game', valueKey: 'average_assists', rankKey: 'rank_average_assists' },
};

interface HomeTrendsProps {
    season?: string | null;
    seasonType?: string;
    minGames?: number;
}

export function HomeTrends({ season, seasonType = 'regular', minGames = 0 }: HomeTrendsProps = {}) {
    const [players, setPlayers] = useState<RankedPlayerStats[]>([]);

    const seasonName = season ?? env.VITE_DEFAULT_SEASON;

    useEffect(() => {
        if (!seasonName) return;
        apiFetch(`/api/nba/analytics/average_stats/season=${seasonName}/season_type=${seasonType}?min_games=${minGames}`)
            .then(r => r.json())
            .then(data => setPlayers(data.records ?? []))
            .catch(() => setPlayers([]));
    }, [seasonName, seasonType, minGames]);

    const buildLeaderboardRows = (stat: StatKey): LeaderboardRow[] => {
        const { valueKey, rankKey } = STAT_CONFIG[stat];
        return [...players]
            .sort((a, b) => (a[rankKey] as number) - (b[rankKey] as number))
            .slice(0, 10)
            .map((player) => ({
                rank: player[rankKey] as number,
                label: player.player_name,
                sublabel: player.team_name,
                value: (player[valueKey] as number).toFixed(1),
                magnitude: player[valueKey] as number,
            }));
    };

    return (
        <div style={{ width: '100%', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
            {(Object.keys(STAT_CONFIG) as StatKey[]).map((stat) => (
                <Leaderboard
                    key={stat}
                    title={STAT_CONFIG[stat].title}
                    titleMeta="per game"
                    accent={stat === 'rebounds'}
                    rows={buildLeaderboardRows(stat)}
                />
            ))}
        </div>
    );
}
