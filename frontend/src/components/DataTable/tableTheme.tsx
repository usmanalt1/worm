import { Tooltip } from '@mantine/core';
import type { DataTableColumn } from 'mantine-datatable';
import type { AdvancedAverages, BoxScoreAverages } from '../../types/stats';
import {
    ADVANCED_KEYS, BOX_SCORE_KEYS, metricSpec,
    type MetricKey, type MetricKind, type MetricSpec,
} from '../../lib/metrics';

export const headerStyle = {
    backgroundColor: 'var(--panel-2)',
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '12px',
    fontWeight: 700,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    color: 'var(--paper-faint)',
};

export const cellStyle = {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '14px',
    color: 'var(--paper-dim)',
    fontVariantNumeric: 'tabular-nums' as const,
};

export const nameCellStyle = { ...cellStyle, color: 'var(--paper)', fontWeight: 700 };

export const signedCellStyle = (value: number | null) => ({
    ...cellStyle,
    color: value === null ? 'var(--paper-faint)'
        : value > 0 ? 'var(--win)' : value < 0 ? 'var(--lose)' : 'var(--paper-faint)',
});

export const average = (value: number | null) => (value === null ? '—' : value.toFixed(1));

export const signed = (value: number | null) =>
    value === null ? '—' : value > 0 ? `+${average(value)}` : average(value);

// Already 0-100 from the API.
export const percent = (value: number | null) => (value === null ? '—' : `${value.toFixed(1)}%`);

export const tableProps = {
    withTableBorder: true,
    striped: true,
    highlightOnHover: true,
    borderRadius: 'sm',
    verticalSpacing: 'xs',
    horizontalSpacing: 'md',
    backgroundColor: 'var(--court)',
    borderColor: 'var(--line)',
    rowBorderColor: 'var(--line)',
    stripedColor: 'var(--panel)',
    highlightOnHoverColor: 'var(--panel-2)',
    styles: { header: headerStyle },
} as const;


// The span gives Tooltip an element to attach to, keeping the header itself sortable.
export function header(label: string, description: string) {
    return (
        <Tooltip label={description} withArrow openDelay={200} position="top">
            <span style={{ cursor: 'help' }}>{label}</span>
        </Tooltip>
    );
}

// Fixed, so the table scrolls sideways rather than squashing the columns.
const STAT_WIDTH = 78;

export function metricValue<T>(record: T, key: MetricKey): number | null {
    const value = (record as Record<string, unknown>)[key];
    return typeof value === 'number' ? value : null;
}

export function formatMetric(value: number | null, kind: MetricKind): string {
    if (kind === 'percent') return percent(value);
    if (kind === 'signed') return signed(value);
    if (kind === 'count') return String(value ?? '—');
    return average(value);
}

function columnFor<T>(spec: MetricSpec): DataTableColumn<T> {
    return {
        accessor: spec.key,
        title: header(spec.title, spec.description),
        sortable: true,
        width: STAT_WIDTH,
        textAlign: 'right' as const,
        cellsStyle: (record: T) =>
            spec.kind === 'signed' ? signedCellStyle(metricValue(record, spec.key)) : cellStyle,
        render: (record: T) => formatMetric(metricValue(record, spec.key), spec.kind),
    };
}

/** Columns for exactly these metrics, in this order. Unknown keys are dropped. */
export function columnsFor<T>(keys: readonly MetricKey[]): DataTableColumn<T>[] {
    return keys
        .map(metricSpec)
        .filter((spec): spec is MetricSpec => spec !== undefined)
        .map(spec => columnFor<T>(spec));
}

export function statColumns<T extends BoxScoreAverages>(): DataTableColumn<T>[] {
    return columnsFor<T>(BOX_SCORE_KEYS);
}

export function advancedColumns<T extends AdvancedAverages>(): DataTableColumn<T>[] {
    return columnsFor<T>(ADVANCED_KEYS);
}
