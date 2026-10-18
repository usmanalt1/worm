import { Leaderboard, type LeaderboardRow } from '../ui/Leaderboard';
import { formatMetric, metricValue } from '../DataTable/tableTheme';
import { metricSpec, type MetricKey, type MetricSpec } from '../../lib/metrics';
import type { AnalyticsRow } from '../../types/analytics';

interface MetricLeaderboardsProps {
    rows: AnalyticsRow[];
    metrics: MetricKey[];
    empty: string;
}

const BOARD_COUNT = 3;
const BOARD_SIZE = 10;

function boardRows(rows: AnalyticsRow[], spec: MetricSpec): LeaderboardRow[] {
    const scored = rows
        .map(row => ({ row, value: metricValue(row, spec.key) }))
        .filter((entry): entry is { row: AnalyticsRow; value: number } => entry.value !== null);

    scored.sort((a, b) => (spec.higherIsBetter ? b.value - a.value : a.value - b.value));

    return scored.slice(0, BOARD_SIZE).map((entry, index) => ({
        rank: index + 1,
        label: entry.row.name,
        value: formatMetric(entry.value, spec.kind),
        // A zero-based bar under a lower-is-better stat reads backwards: longest = worst.
        magnitude: spec.higherIsBetter ? entry.value : undefined,
    }));
}

export function MetricLeaderboards({ rows, metrics, empty }: MetricLeaderboardsProps) {
    const specs = metrics
        .slice(0, BOARD_COUNT)
        .map(metricSpec)
        .filter((spec): spec is MetricSpec => spec !== undefined);

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
            {specs.map((spec, index) => (
                <Leaderboard
                    key={spec.key}
                    title={spec.title}
                    titleMeta={spec.higherIsBetter ? 'High to low' : 'Low to high'}
                    rows={boardRows(rows, spec)}
                    accent={index === 0}
                    empty={empty}
                    maxHeight={340}
                />
            ))}
        </div>
    );
}
