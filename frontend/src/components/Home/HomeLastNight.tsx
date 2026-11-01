import { useMemo } from 'react';
import { SectionHeader } from '../ui/SectionHeader';
import { StatCard } from '../ui/StatCard';
import { HomePredictionRail } from './HomePredictionRail';
import type { ModelStats } from '../../utils/modelStats';

interface HomeLastNightProps {
    index: string;
    strategy: string | null;
    stats: ModelStats;
    loading: boolean;
    /** Which games the record is over; through October, the preseason. */
    seasonType?: string | null;
}

function dayLabel(date: string): string {
    return new Date(date).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

export function HomeLastNight({ index, strategy, stats, loading, seasonType }: HomeLastNightProps) {
    const night = useMemo(() => {
        if (stats.graded.length === 0) return null;

        const latest = stats.graded.reduce(
            (newest, row) => (row.game_date > newest ? row.game_date : newest),
            stats.graded[0].game_date,
        );
        const day = latest.slice(0, 10);
        const games = stats.graded.filter((row) => row.game_date.slice(0, 10) === day);
        const hits = games.filter((row) => row.hit).length;

        return {
            day,
            games,
            hits,
            misses: games.length - hits,
            accuracy: hits / games.length,
            claimed: games.reduce((total, row) => total + row.confidence, 0) / games.length,
        };
    }, [stats.graded]);

    const modelName = strategy?.replace(/_/g, ' ') ?? 'the model';

    return (
        <section style={{ marginBottom: 'var(--section-gap)' }}>
            <SectionHeader
                index={index}
                title="Last Night"
                subtitle={`Every call ${modelName} made on the last day it was graded on`}
                meta={
                    night && (
                        <span className="kicker" style={{ color: 'var(--paper-faint)' }}>
                            {dayLabel(night.day)}{seasonType ? ` · ${seasonType}` : ''}
                        </span>
                    )
                }
            />

            {loading && (
                <div style={{ fontSize: 13, color: 'var(--paper-faint)', padding: '8px 0' }}>
                    Grading last night…
                </div>
            )}

            {!loading && !night && (
                <div style={{ fontSize: 13, color: 'var(--paper-faint)', padding: '8px 0' }}>
                    Nothing graded yet — no game it has called has a final score in the
                    warehouse. The first one lands the morning after it is played.
                </div>
            )}

            {!loading && night && (
                <>
                    <div
                        style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
                            gap: 14,
                            marginBottom: 20,
                        }}
                    >
                        <StatCard
                            hero
                            tone="brand"
                            label="Last night"
                            value={`${(night.accuracy * 100).toFixed(0)}%`}
                            note={`${night.hits} hit · ${night.misses} miss`}
                        />
                        <StatCard
                            hero
                            label="Games called"
                            value={String(night.games.length)}
                            note={dayLabel(night.day)}
                        />
                        <StatCard
                            hero
                            label="Confidence it claimed"
                            value={`${(night.claimed * 100).toFixed(0)}%`}
                            note={night.claimed > night.accuracy ? 'Talked it up' : 'Undersold itself'}
                        />
                        <StatCard
                            hero
                            label="Season to date"
                            value={`${(stats.accuracy * 100).toFixed(1)}%`}
                            note={`${stats.games} games graded`}
                        />
                    </div>

                    <HomePredictionRail predictions={night.games} empty="No calls on this date." />
                </>
            )}
        </section>
    );
}
