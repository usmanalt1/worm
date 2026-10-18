import { useMemo } from 'react';
import { Panel } from '../ui/Panel';
import { TeamChip } from '../ui/TeamChip';
import { FactorBars, type Factor } from '../ui/FactorBars';
import { percentile } from '../../lib/colour';
import type { AnalyticsRow } from '../../types/analytics';

interface FourFactorsProps {
    rows: AnalyticsRow[];
    loading: boolean;
    empty: string;
}

interface FactorSpec {
    key: string;
    label: string;
    /** Share of what decides games, per the 2023 re-derivation of Oliver's weights. */
    weight: number;
    lowerIsBetter: boolean;
    read: (row: AnalyticsRow) => number | null;
}

function ftRate(row: AnalyticsRow): number | null {
    const fta = row.average_free_throws_attempted;
    const fga = row.average_field_goals_attempted;
    return fta === null || !fga ? null : (fta / fga) * 100;
}

const FACTORS: FactorSpec[] = [
    { key: 'efg', label: 'Shooting', weight: 45, lowerIsBetter: false, read: row => row.effective_field_goal_percentage ?? null },
    { key: 'tov', label: 'Turnovers', weight: 37, lowerIsBetter: true, read: row => row.turnover_percentage ?? null },
    { key: 'oreb', label: 'Off. boards', weight: 11, lowerIsBetter: false, read: row => row.offensive_rebound_percentage ?? null },
    { key: 'ftr', label: 'Free throws', weight: 7, lowerIsBetter: false, read: ftRate },
];

const WEIGHT_TOTAL = FACTORS.reduce((sum, factor) => sum + factor.weight, 0);

interface TeamFactors {
    row: AnalyticsRow;
    factors: Factor[];
    weakest: Factor;
    score: number;
}

function build(rows: AnalyticsRow[]): TeamFactors[] {
    // Percentiles come from the whole qualified league, never a filtered subset.
    const populations = new Map(
        FACTORS.map(factor => [
            factor.key,
            rows.map(factor.read).filter((value): value is number => value !== null),
        ]),
    );

    return rows
        .map(row => {
            const factors = FACTORS.flatMap<Factor>(factor => {
                const value = factor.read(row);
                if (value === null) return [];
                return [{
                    key: factor.key,
                    label: factor.label,
                    percentile: percentile(value, populations.get(factor.key) ?? [], {
                        lowerIsBetter: factor.lowerIsBetter,
                    }),
                    display: `${value.toFixed(1)}%`,
                }];
            });

            if (factors.length === 0) return [];

            const weightOf = (key: string) => FACTORS.find(f => f.key === key)?.weight ?? 0;
            const score = factors.reduce((sum, f) => sum + f.percentile * weightOf(f.key), 0) / WEIGHT_TOTAL;
            const weakest = factors.reduce((low, f) => (f.percentile < low.percentile ? f : low));

            return [{ row, factors, weakest, score }];
        })
        .flat()
        .sort((a, b) => b.score - a.score);
}

function Legend() {
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 14, marginBottom: 18 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 14, height: 8, borderRadius: 2, background: 'var(--cold)' }} />
                <span className="kicker" style={{ color: 'var(--paper-dim)' }}>Below league median</span>
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 14, height: 8, borderRadius: 2, background: 'var(--hot)' }} />
                <span className="kicker" style={{ color: 'var(--paper-dim)' }}>Above</span>
            </span>
            <span className="kicker" style={{ color: 'var(--paper-faint)' }}>
                {FACTORS.map(f => `${f.label} ${f.weight}%`).join(' · ')}
            </span>
        </div>
    );
}

export function FourFactors({ rows, loading, empty }: FourFactorsProps) {
    const teams = useMemo(() => build(rows), [rows]);

    if (loading) return <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>Loading…</div>;
    if (teams.length === 0) return <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>{empty}</div>;

    return (
        <div>
            <Legend />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
                {teams.map((team, index) => (
                    <Panel key={team.row.id} accent={index === 0}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14, minWidth: 0 }}>
                            <TeamChip team={team.row.team} />
                            <span
                                style={{
                                    fontSize: 13, fontWeight: 600, color: 'var(--paper)',
                                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                }}
                                title={team.row.name}
                            >
                                {team.row.name}
                            </span>
                            <span className="kicker" style={{ marginLeft: 'auto', flexShrink: 0, color: 'var(--paper-faint)' }}>
                                Weakest: {team.weakest.label}
                            </span>
                        </div>
                        <FactorBars factors={team.factors} />
                    </Panel>
                ))}
            </div>
        </div>
    );
}
