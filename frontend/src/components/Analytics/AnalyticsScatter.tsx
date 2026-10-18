import { useMemo } from 'react';
import { ScatterPlot, type ScatterPoint } from '../ui/ScatterPlot';
import { formatMetric, metricValue } from '../DataTable/tableTheme';
import { metricSpec, type MetricKey } from '../../lib/metrics';
import { useTeamResolver } from '../../context/TeamColoursProvider';
import type { AnalyticsRow } from '../../types/analytics';

interface AnalyticsScatterProps {
    rows: AnalyticsRow[];
    entity: 'player' | 'team';
    x: MetricKey;
    y: MetricKey;
    empty: string;
}

export function AnalyticsScatter({ rows, entity, x, y, empty }: AnalyticsScatterProps) {
    const resolveTeam = useTeamResolver();
    const xSpec = metricSpec(x);
    const ySpec = metricSpec(y);

    const points = useMemo<ScatterPoint[]>(() => {
        if (!xSpec || !ySpec) return [];

        return rows.flatMap(row => {
            const xValue = metricValue(row, x);
            const yValue = metricValue(row, y);
            if (xValue === null || yValue === null) return [];

            return [{
                id: row.id,
                label: row.name,
                x: xValue,
                y: yValue,
                colour: resolveTeam(row.team)?.colour ?? 'var(--worm)',
            }];
        });
    }, [rows, x, y, xSpec, ySpec, resolveTeam]);

    if (!xSpec || !ySpec) {
        return <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>Pick two metrics to plot.</div>;
    }

    const noun = entity === 'player' ? 'player' : 'team';

    return (
        <ScatterPlot
            points={points}
            xLabel={xSpec.title}
            yLabel={ySpec.title}
            invertY={!ySpec.higherIsBetter}
            formatX={value => formatMetric(value, xSpec.kind)}
            formatY={value => formatMetric(value, ySpec.kind)}
            caption={`Each dot is a ${noun}; dashed lines are the league medians. Up and right is better. Hover a dot for its numbers.`}
            empty={empty}
        />
    );
}
