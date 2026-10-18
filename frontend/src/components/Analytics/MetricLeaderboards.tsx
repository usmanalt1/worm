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

type Direction = 'high' | 'low';

interface Board {
    id: string;
    title: string;
    meta: string;
    rows: LeaderboardRow[];
}

function boardRows(rows: AnalyticsRow[], spec: MetricSpec, direction: Direction): LeaderboardRow[] {
    const scored = rows
        .map(row => ({ row, value: metricValue(row, spec.key) }))
        .filter((entry): entry is { row: AnalyticsRow; value: number } => entry.value !== null);

    scored.sort((a, b) => (direction === 'high' ? b.value - a.value : a.value - b.value));

    return scored.slice(0, BOARD_SIZE).map((entry, index) => ({
        rank: index + 1,
        label: entry.row.name,
        value: formatMetric(entry.value, spec.kind),
        // A zero-based bar only reads right when the top of the board is the good end.
        magnitude: spec.higherIsBetter === true && direction === 'high' ? entry.value : undefined,
    }));
}

function boardsFor(rows: AnalyticsRow[], spec: MetricSpec): Board[] {
    // Neither end of a neutral metric is better, so both get a board.
    if (spec.higherIsBetter === null) {
        return [
            { id: `${spec.key}-low`, title: `${spec.title} · lowest`, meta: 'Low to high', rows: boardRows(rows, spec, 'low') },
            { id: `${spec.key}-high`, title: `${spec.title} · highest`, meta: 'High to low', rows: boardRows(rows, spec, 'high') },
        ];
    }

    const direction: Direction = spec.higherIsBetter ? 'high' : 'low';
    return [{
        id: spec.key,
        title: spec.title,
        meta: spec.higherIsBetter ? 'High to low' : 'Low to high',
        rows: boardRows(rows, spec, direction),
    }];
}

export function MetricLeaderboards({ rows, metrics, empty }: MetricLeaderboardsProps) {
    const boards = metrics
        .slice(0, BOARD_COUNT)
        .map(metricSpec)
        .filter((spec): spec is MetricSpec => spec !== undefined)
        .flatMap(spec => boardsFor(rows, spec));

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
            {boards.map((board, index) => (
                <Leaderboard
                    key={board.id}
                    title={board.title}
                    titleMeta={board.meta}
                    rows={board.rows}
                    accent={index === 0}
                    empty={empty}
                    maxHeight={340}
                />
            ))}
        </div>
    );
}
