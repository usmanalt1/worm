import { useState } from 'react';
import { Panel } from './Panel';

export interface TrendSeries {
    key: string;
    label: string;
    /** One entry per season, in the same order for every series. */
    values: (number | null)[];
    format: (value: number) => string;
}

interface TrendLinesProps {
    seasons: string[];
    series: TrendSeries[];
    empty?: string;
}

const VIEW_W = 320;
const VIEW_H = 132;
const PAD = { top: 10, right: 10, bottom: 22, left: 40 };
const PLOT_W = VIEW_W - PAD.left - PAD.right;
const PLOT_H = VIEW_H - PAD.top - PAD.bottom;
const DOT_R = 4;

const tickText = {
    fontFamily: 'var(--mono)',
    fontSize: 9,
    fill: 'var(--paper-faint)',
    letterSpacing: '0.06em',
} as const;

// Each measure keeps its own axis: points, a percentage share and possessions per 48
// on one scale would need three y axes, which lies about all three.
function Chart({
    series, seasons, hovered, onHover,
}: {
    series: TrendSeries;
    seasons: string[];
    hovered: number | null;
    onHover: (index: number | null) => void;
}) {
    const present = series.values
        .map((value, index) => ({ value, index }))
        .filter((entry): entry is { value: number; index: number } => entry.value !== null);

    if (present.length < 2) {
        return (
            <Panel title={series.label}>
                <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>Not enough seasons yet.</div>
            </Panel>
        );
    }

    const values = present.map(entry => entry.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const pad = (max - min) * 0.12 || 1;
    const [low, high] = [min - pad, max + pad];

    const toX = (index: number) =>
        PAD.left + (seasons.length === 1 ? PLOT_W / 2 : (index / (seasons.length - 1)) * PLOT_W);
    const toY = (value: number) => PAD.top + (1 - (value - low) / (high - low)) * PLOT_H;

    const line = present.map(entry => `${toX(entry.index)},${toY(entry.value)}`).join(' ');
    const active = hovered === null ? null : present.find(entry => entry.index === hovered) ?? null;

    return (
        <Panel title={series.label} titleMeta={active ? series.format(active.value) : undefined}>
            <svg
                viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
                style={{ width: '100%', height: 'auto', display: 'block' }}
                role="img"
                aria-label={`${series.label} by season`}
                onMouseLeave={() => onHover(null)}
            >
                {[low, (low + high) / 2, high].map(tick => (
                    <g key={tick}>
                        <line
                            x1={PAD.left} x2={PAD.left + PLOT_W} y1={toY(tick)} y2={toY(tick)}
                            stroke="var(--line)" strokeWidth={1}
                        />
                        <text x={PAD.left - 6} y={toY(tick)} textAnchor="end" dominantBaseline="middle" style={tickText}>
                            {series.format(tick)}
                        </text>
                    </g>
                ))}

                {active && (
                    <line
                        x1={toX(active.index)} x2={toX(active.index)} y1={PAD.top} y2={PAD.top + PLOT_H}
                        stroke="var(--paper-faint)" strokeWidth={1} strokeDasharray="3 4"
                    />
                )}

                <polyline points={line} fill="none" stroke="var(--worm)" strokeWidth={2} />

                {present.map(entry => (
                    <circle
                        key={entry.index}
                        cx={toX(entry.index)}
                        cy={toY(entry.value)}
                        r={hovered === entry.index ? DOT_R + 1.5 : DOT_R}
                        fill="var(--worm)"
                        stroke="var(--panel)"
                        strokeWidth={1.5}
                        opacity={hovered !== null && hovered !== entry.index ? 0.55 : 1}
                        style={{ transition: 'opacity 120ms, r 120ms', cursor: 'pointer' }}
                        onMouseEnter={() => onHover(entry.index)}
                    />
                ))}

                <text x={PAD.left} y={VIEW_H - 6} textAnchor="start" style={tickText}>
                    {seasons[0]}
                </text>
                <text x={PAD.left + PLOT_W} y={VIEW_H - 6} textAnchor="end" style={tickText}>
                    {seasons[seasons.length - 1]}
                </text>
            </svg>
        </Panel>
    );
}

/** One panel per measure, sharing a season axis and a hover. */
export function TrendLines({ seasons, series, empty = 'No seasons on record.' }: TrendLinesProps) {
    const [hovered, setHovered] = useState<number | null>(null);

    if (seasons.length === 0) {
        return <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>{empty}</div>;
    }

    return (
        <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
                {series.map(one => (
                    <Chart key={one.key} series={one} seasons={seasons} hovered={hovered} onHover={setHovered} />
                ))}
            </div>

            <div style={{ marginTop: 12, minHeight: 18, fontSize: 12, fontFamily: 'var(--mono)', color: 'var(--paper-dim)' }}>
                {hovered !== null ? (
                    <span style={{ color: 'var(--paper)' }}>
                        {seasons[hovered]}
                        {series.map(one => {
                            const value = one.values[hovered];
                            return ` · ${one.label} ${value === null ? '—' : one.format(value)}`;
                        })}
                    </span>
                ) : (
                    <span>Each panel keeps its own scale. Hover a season to read all three.</span>
                )}
            </div>
        </div>
    );
}
