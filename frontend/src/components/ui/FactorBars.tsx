import { diverging, divergingColour } from '../../lib/colour';

export interface Factor {
    key: string;
    label: string;
    /** 0..1 against the qualified league, already inverted for lower-is-better factors. */
    percentile: number;
    display: string;
}

const COLUMNS = '84px minmax(0, 1fr) 52px';
const BAR_HEIGHT = 12;

/** Diverging bars off a league-median centre line: the longest cold bar is the weakness. */
export function FactorBars({ factors }: { factors: Factor[] }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {factors.map(factor => {
                const { side, widthPct } = diverging(factor.percentile - 0.5, 0.5);
                const above = side === 'up';

                return (
                    <div
                        key={factor.key}
                        style={{ display: 'grid', gridTemplateColumns: COLUMNS, alignItems: 'center', gap: 10 }}
                    >
                        <span className="kicker" style={{ color: 'var(--paper-dim)' }}>{factor.label}</span>

                        <div style={{ position: 'relative', height: BAR_HEIGHT }}>
                            <div style={{ position: 'absolute', inset: 0, background: 'var(--panel-2)', borderRadius: 2 }} />
                            <div
                                aria-hidden
                                style={{
                                    position: 'absolute', left: '50%', top: -2, bottom: -2,
                                    width: 1, background: 'var(--line)',
                                }}
                            />
                            <div
                                style={{
                                    position: 'absolute',
                                    top: 0,
                                    height: BAR_HEIGHT,
                                    // Each side owns half the track, so a full bar is 50% of it.
                                    left: above ? '50%' : undefined,
                                    right: above ? undefined : '50%',
                                    width: `${widthPct / 2}%`,
                                    background: divergingColour(side),
                                    borderRadius: above ? '0 2px 2px 0' : '2px 0 0 2px',
                                }}
                            />
                        </div>

                        <span
                            style={{
                                fontFamily: 'var(--mono)', fontSize: 12, textAlign: 'right',
                                color: 'var(--paper)', fontVariantNumeric: 'tabular-nums',
                            }}
                        >
                            {factor.display}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
