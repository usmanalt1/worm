import { TrendLines, type TrendSeries } from '../ui/TrendLines';
import { StatCard } from '../ui/StatCard';
import { useLeagueTrends } from '../../hooks/useLeagueTrends';
import type { LeagueTrendPoint } from '../../types/analytics';

interface LeagueTrendsProps {
    seasonType: string;
    /** The year the stat cards describe; the lines always span every season. */
    season: string | null;
}

const ONE_DP = (value: number) => value.toFixed(1);
const PERCENT = (value: number) => `${value.toFixed(1)}%`;

const MEASURES = [
    { key: 'points_per_game', label: 'Points per game', format: ONE_DP },
    { key: 'three_point_attempt_share', label: 'Three-point share', format: PERCENT },
    { key: 'pace', label: 'Pace', format: ONE_DP },
] as const;

function changeNote(
    measure: (typeof MEASURES)[number],
    selected: LeagueTrendPoint,
    first: LeagueTrendPoint,
): string {
    const now = selected[measure.key];
    const then = first[measure.key];
    if (now === null || then === null) return `No ${first.season} figure to compare.`;

    const delta = now - then;
    const direction = delta > 0 ? 'up' : delta < 0 ? 'down' : 'level';
    return `${direction} ${measure.format(Math.abs(delta))} since ${first.season}`;
}

export function LeagueTrends({ seasonType, season }: LeagueTrendsProps) {
    const { points, loading } = useLeagueTrends(seasonType);

    if (loading) {
        return <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>Loading…</div>;
    }
    if (points.length === 0) {
        return (
            <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>
                No {seasonType} seasons on record yet.
            </div>
        );
    }

    const seasons = points.map(point => point.season);
    const selected = points.find(point => point.season === season) ?? points[points.length - 1];
    const first = points[0];

    const series: TrendSeries[] = MEASURES.map(measure => ({
        key: measure.key,
        label: measure.label,
        values: points.map(point => point[measure.key]),
        format: measure.format,
    }));

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
                {MEASURES.map((measure, index) => {
                    const value = selected[measure.key];
                    return (
                        <StatCard
                            key={measure.key}
                            label={`${measure.label} · ${selected.season}`}
                            value={value === null ? '—' : measure.format(value)}
                            note={changeNote(measure, selected, first)}
                            tone={index === 0 ? 'brand' : 'default'}
                        />
                    );
                })}
            </div>

            <TrendLines seasons={seasons} series={series} />
        </div>
    );
}
