import { Select, Tooltip } from '@mantine/core';
import { metricSpec, metricsForEntity, type MetricKey, type MetricSpec } from '../../lib/metrics';
import type { AnalyticsView } from '../../types/analytics';

interface MetricPickerProps {
    entity: 'player' | 'team';
    view: AnalyticsView;
    metrics: MetricKey[];
    x: MetricKey;
    y: MetricKey;
    onMetrics: (keys: MetricKey[]) => void;
    onAxes: (x: MetricKey, y: MetricKey) => void;
}

const GROUP_LABELS: Record<'box' | 'advanced', string> = {
    box: 'Box score',
    advanced: 'Advanced',
};

function Chip({ spec, selected, onClick }: { spec: MetricSpec; selected: boolean; onClick: () => void }) {
    return (
        <Tooltip label={spec.description} withArrow openDelay={300} position="top">
            <button
                type="button"
                onClick={onClick}
                aria-pressed={selected}
                style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    padding: '5px 9px',
                    borderRadius: 3,
                    cursor: 'pointer',
                    background: selected ? 'rgba(232, 98, 44, 0.14)' : 'var(--panel-2)',
                    border: `1px solid ${selected ? 'var(--worm)' : 'var(--line)'}`,
                    color: selected ? 'var(--paper)' : 'var(--paper-dim)',
                    transition: 'background 120ms, border-color 120ms',
                }}
            >
                {spec.title}
            </button>
        </Tooltip>
    );
}

function axisData(specs: MetricSpec[]) {
    return (['box', 'advanced'] as const).map(group => ({
        group: GROUP_LABELS[group],
        items: specs.filter(spec => spec.group === group).map(spec => ({
            value: spec.key,
            // Short side of the description, so the option stays searchable but fits.
            label: `${spec.title} — ${spec.description.split(':')[0]}`,
        })),
    }));
}

export function MetricPicker({ entity, view, metrics, x, y, onMetrics, onAxes }: MetricPickerProps) {
    const specs = metricsForEntity(entity);
    const selected = new Set(metrics);

    const toggle = (key: MetricKey) => {
        // Never empty: the table needs at least one column to be worth rendering.
        if (selected.has(key) && metrics.length === 1) return;
        onMetrics(selected.has(key) ? metrics.filter(m => m !== key) : [...metrics, key]);
    };

    const yInverted = !(metricSpec(y)?.higherIsBetter ?? true);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {view === 'scatter' && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-end' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <span className="kicker">X axis</span>
                        <Select
                            size="xs"
                            style={{ width: 230 }}
                            data={axisData(specs)}
                            value={x}
                            onChange={value => value && onAxes(value as MetricKey, y)}
                            allowDeselect={false}
                            searchable
                        />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <span className="kicker">Y axis{yInverted ? ' · inverted' : ''}</span>
                        <Select
                            size="xs"
                            style={{ width: 230 }}
                            data={axisData(specs)}
                            value={y}
                            onChange={value => value && onAxes(x, value as MetricKey)}
                            allowDeselect={false}
                            searchable
                        />
                    </div>
                </div>
            )}

            {(['box', 'advanced'] as const).map(group => (
                <div key={group}>
                    <div className="kicker" style={{ marginBottom: 10, color: 'var(--paper-faint)' }}>
                        {GROUP_LABELS[group]}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {specs.filter(spec => spec.group === group).map(spec => (
                            <Chip
                                key={spec.key}
                                spec={spec}
                                selected={selected.has(spec.key)}
                                onClick={() => toggle(spec.key)}
                            />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
