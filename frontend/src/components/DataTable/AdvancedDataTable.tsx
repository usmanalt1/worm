import { DataTable, type DataTableSortStatus } from 'mantine-datatable';
import { useMemo, useState } from 'react';
import sortBy from 'lodash/sortBy';
import 'mantine-datatable/styles.layer.css';
import type { SeasonAdvancedPlayerStats, SeasonAdvancedTeamStats } from '../../types/stats';
import { advancedColumns, cellStyle, header, nameCellStyle, tableProps } from './tableTheme';

export function AdvancedPlayerTable({ rows = [] }: { rows: SeasonAdvancedPlayerStats[] }) {
    const [sortStatus, setSortStatus] = useState<DataTableSortStatus<SeasonAdvancedPlayerStats>>({
        columnAccessor: 'average_minutes',
        direction: 'desc',
    });

    const records = useMemo(() => {
        const data = sortBy(rows, sortStatus.columnAccessor);
        return sortStatus.direction === 'desc' ? data.reverse() : data;
    }, [rows, sortStatus]);

    return (
        <DataTable<SeasonAdvancedPlayerStats>
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
                ...advancedColumns<SeasonAdvancedPlayerStats>(),
            ]}
        />
    );
}

export function AdvancedTeamTable({ rows = [] }: { rows: SeasonAdvancedTeamStats[] }) {
    const [sortStatus, setSortStatus] = useState<DataTableSortStatus<SeasonAdvancedTeamStats>>({
        columnAccessor: 'net_rating',
        direction: 'desc',
    });

    const records = useMemo(() => {
        const data = sortBy(rows, sortStatus.columnAccessor);
        return sortStatus.direction === 'desc' ? data.reverse() : data;
    }, [rows, sortStatus]);

    return (
        <DataTable<SeasonAdvancedTeamStats>
            {...tableProps}
            idAccessor="team_id"
            pinFirstColumn
            records={records}
            emptyState={null}
            sortStatus={sortStatus}
            onSortStatusChange={setSortStatus}
            columns={[
                { accessor: 'team_name', title: header('Team', 'Team name'), sortable: true, width: 200, cellsStyle: () => nameCellStyle },
                ...advancedColumns<SeasonAdvancedTeamStats>(),
            ]}
        />
    );
}
