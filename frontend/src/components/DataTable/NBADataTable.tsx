import { DataTable, type DataTableSortStatus } from 'mantine-datatable';
import { useMemo, useState } from 'react';
import sortBy from 'lodash/sortBy';
import 'mantine-datatable/styles.layer.css';
import type { SeasonPlayerStats } from '../../types/player';
import { cellStyle, header, nameCellStyle, statColumns, tableProps } from './tableTheme';

export default function NBADataTable({ nbaData = [] }: { nbaData: SeasonPlayerStats[] }) {
    const [sortStatus, setSortStatus] = useState<DataTableSortStatus<SeasonPlayerStats>>({
        columnAccessor: 'average_points',
        direction: 'desc',
    });

    const records = useMemo(() => {
        const data = sortBy(nbaData, sortStatus.columnAccessor);
        return sortStatus.direction === 'desc' ? data.reverse() : data;
    }, [nbaData, sortStatus]);

    return (
        <DataTable<SeasonPlayerStats>
            {...tableProps}
            idAccessor="player_id"
            pinFirstColumn
            records={records}
            emptyState={null}
            sortStatus={sortStatus}
            onSortStatusChange={setSortStatus}
            columns={[
                { accessor: 'player_name', title: header('Player', 'Player name'), sortable: true, width: 190, cellsStyle: () => nameCellStyle },
                {
                    accessor: 'team_abbreviation', title: header('Team', 'Team the player finished the season with'), sortable: true, width: 80,
                    cellsStyle: () => ({ ...cellStyle, color: 'var(--paper-dim)' }),
                    render: ({ team_abbreviation }) => team_abbreviation ?? '—',
                },
                {
                    accessor: 'position', title: header('Pos', 'Listed position: G guard, F forward, C center'), sortable: true, width: 70,
                    cellsStyle: () => ({ ...cellStyle, color: 'var(--paper-faint)' }),
                    render: ({ position }) => position ?? '—',
                },
                ...statColumns<SeasonPlayerStats>(),
            ]}
        />
    );
}
