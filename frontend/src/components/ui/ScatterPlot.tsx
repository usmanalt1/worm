import { useMemo, useState } from 'react';

export interface ScatterPoint {
    id: number;
    label: string;
    x: number;
    y: number;
    /** Team colour, or --worm where the team is unknown. Identity only, never magnitude. */
    colour: string;
}

interface ScatterPlotProps {
    points: ScatterPoint[];
    xLabel: string;
    yLabel: string;
    /** Flip y when lower is better, so up and right always mean better. */
    invertY?: boolean;
    formatX: (value: number) => string;
    formatY: (value: number) => string;
    /** One plain sentence on how to read the plot, shown when nothing is hovered. */
    caption: string;
    empty?: string;
}

const VIEW_W = 820;
const VIEW_H = 460;
const PAD = { top: 16, right: 18, bottom: 44, left: 56 };
const TICKS = 4;
const DOT_R = 5;

const PLOT_W = VIEW_W - PAD.left - PAD.right;
const PLOT_H = VIEW_H - PAD.top - PAD.bottom;

const tickText = {
    fontFamily: 'var(--mono)',
    fontSize: 10,
    fill: 'var(--paper-faint)',
    letterSpacing: '0.08em',
} as const;

function domain(values: number[]): [number, number] {
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (min === max) return [min - 1, max + 1];
    const pad = (max - min) * 0.06;
    return [min - pad, max + pad];
}

function median(values: number[]): number {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function ticksOf([min, max]: [number, number]): number[] {
    return Array.from({ length: TICKS + 1 }, (_, i) => min + ((max - min) * i) / TICKS);
}

export function ScatterPlot({
    points, xLabel, yLabel, invertY = false, formatX, formatY, caption, empty = 'Nothing to plot.',
}: ScatterPlotProps) {
    const [hovered, setHovered] = useState<number | null>(null);

    const scales = useMemo(() => {
        if (points.length === 0) return null;
        const xs = points.map(p => p.x);
        const ys = points.map(p => p.y);
        const xDomain = domain(xs);
        const yDomain = domain(ys);

        const toX = (value: number) =>
            PAD.left + ((value - xDomain[0]) / (xDomain[1] - xDomain[0])) * PLOT_W;
        // SVG y grows downward, so the default already puts high values up; inverting
        // means dropping that flip.
        const toY = (value: number) => {
            const t = (value - yDomain[0]) / (yDomain[1] - yDomain[0]);
            return PAD.top + (invertY ? t : 1 - t) * PLOT_H;
        };

        return { xDomain, yDomain, toX, toY, xMedian: median(xs), yMedian: median(ys) };
    }, [points, invertY]);

    if (!scales) {
        return <div style={{ fontSize: 13, color: 'var(--paper-faint)' }}>{empty}</div>;
    }

    const { xDomain, yDomain, toX, toY, xMedian, yMedian } = scales;
    const active = hovered === null ? null : points.find(p => p.id === hovered) ?? null;

    return (
        <div>
            <svg
                viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
                style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
                role="img"
                aria-label={`${yLabel} against ${xLabel}`}
            >
                {ticksOf(yDomain).map(value => (
                    <g key={`y-${value}`}>
                        <line
                            x1={PAD.left} x2={PAD.left + PLOT_W}
                            y1={toY(value)} y2={toY(value)}
                            stroke="var(--line)" strokeWidth={1}
                        />
                        <text x={PAD.left - 8} y={toY(value)} textAnchor="end" dominantBaseline="middle" style={tickText}>
                            {formatY(value)}
                        </text>
                    </g>
                ))}

                {ticksOf(xDomain).map(value => (
                    <g key={`x-${value}`}>
                        <line
                            x1={toX(value)} x2={toX(value)}
                            y1={PAD.top} y2={PAD.top + PLOT_H}
                            stroke="var(--line)" strokeWidth={1}
                        />
                        <text x={toX(value)} y={PAD.top + PLOT_H + 16} textAnchor="middle" style={tickText}>
                            {formatX(value)}
                        </text>
                    </g>
                ))}

                {/* League medians: what makes a quadrant reading mean anything. */}
                <line
                    x1={toX(xMedian)} x2={toX(xMedian)} y1={PAD.top} y2={PAD.top + PLOT_H}
                    stroke="var(--paper-faint)" strokeWidth={1} strokeDasharray="3 4" opacity={0.5}
                />
                <line
                    x1={PAD.left} x2={PAD.left + PLOT_W} y1={toY(yMedian)} y2={toY(yMedian)}
                    stroke="var(--paper-faint)" strokeWidth={1} strokeDasharray="3 4" opacity={0.5}
                />

                {points.map(point => {
                    const dimmed = hovered !== null && hovered !== point.id;
                    return (
                        <circle
                            key={point.id}
                            cx={toX(point.x)}
                            cy={toY(point.y)}
                            r={hovered === point.id ? DOT_R + 2 : DOT_R}
                            fill={point.colour}
                            // Surface ring, so overlapping dots stay countable.
                            stroke="var(--panel)"
                            strokeWidth={1.5}
                            opacity={dimmed ? 0.55 : 1}
                            style={{ transition: 'opacity 120ms, r 120ms', cursor: 'pointer' }}
                            onMouseEnter={() => setHovered(point.id)}
                            onMouseLeave={() => setHovered(null)}
                        >
                            <title>{point.label}</title>
                        </circle>
                    );
                })}

                <text
                    x={PAD.left + PLOT_W / 2} y={VIEW_H - 6}
                    textAnchor="middle" style={tickText}
                >
                    {xLabel.toUpperCase()}
                </text>
                <text
                    x={0} y={0} textAnchor="middle" style={tickText}
                    transform={`translate(14, ${PAD.top + PLOT_H / 2}) rotate(-90)`}
                >
                    {`${yLabel}${invertY ? ' (inverted)' : ''}`.toUpperCase()}
                </text>
            </svg>

            <div style={{ marginTop: 12, minHeight: 18, fontSize: 12, fontFamily: 'var(--mono)', color: 'var(--paper-dim)' }}>
                {active ? (
                    <span style={{ color: 'var(--paper)' }}>
                        {active.label} · {xLabel} {formatX(active.x)} · {yLabel} {formatY(active.y)}
                    </span>
                ) : (
                    <span>{caption}</span>
                )}
            </div>
        </div>
    );
}
