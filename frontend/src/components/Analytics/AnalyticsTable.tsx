import { useMemo, useState } from 'react';
import { DataTable, type DataTableSortStatus } from 'mantine-datatable';
import partition from 'lodash/partition';
import sortBy from 'lodash/sortBy';
import { TeamChip } from '../ui/TeamChip';
import { columnsFor, metricValue, nameCellStyle, tableProps } from '../DataTable/tableTheme';
import type { MetricKey } from '../../lib/metrics';
import type { AnalyticsRow } from '../../types/analytics';

interface AnalyticsTableProps {
    rows: AnalyticsRow[];
    metrics: MetricKey[];
    entity: 'player' | 'team';
    loading: boolean;
    empty: string;
}

const NAME_ACCESSOR = 'name';

export function AnalyticsTable({ rows, metrics, entity, loading, empty }: AnalyticsTableProps) {
    const [sortStatus, setSortStatus] = useState<DataTableSortStatus<AnalyticsRow>>({
        columnAccessor: metrics[0] ?? NAME_ACCESSOR,
        direction: 'desc',
    });

    const sorted = useMemo(() => {
        const accessor = String(sortStatus.columnAccessor);

        if (accessor === NAME_ACCESSOR) {
            const byName = sortBy(rows, row => row.name.toLowerCase());
            return sortStatus.direction === 'desc' ? byName.reverse() : byName;
        }

        // Rows missing the sorted metric go last either way: sortBy puts nulls last
        // ascending, so reversing for descending would float them to the top.
        const read = (row: AnalyticsRow) => metricValue(row, accessor as MetricKey);
        const [present, missing] = partition(rows, row => read(row) !== null);
        const ordered = sortBy(present, read);
        if (sortStatus.direction === 'desc') ordered.reverse();

        return [...ordered, ...missing];
    }, [rows, sortStatus]);

    const columns = useMemo(() => [
        {
            accessor: NAME_ACCESSOR,
            title: entity === 'player' ? 'Player' : 'Team',
            sortable: true,
            width: 220,
            cellsStyle: () => nameCellStyle,
            render: (row: AnalyticsRow) => (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                    <TeamChip team={row.team} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {row.name}
                    </span>
                </span>
            ),
        },
        ...columnsFor<AnalyticsRow>(metrics),
    ], [metrics, entity]);

    return (
        <DataTable<AnalyticsRow>
            {...tableProps}
            height={560}
            records={sorted}
            columns={columns}
            idAccessor="id"
            fetching={loading}
            sortStatus={sortStatus}
            onSortStatusChange={setSortStatus}
            noRecordsText={empty}
        />
    );
}
