import type { CSSProperties, ReactNode } from 'react';

interface PanelProps {
    title?: string;
    titleMeta?: ReactNode;
    /** Brand rule down the left edge, marking the section's lead panel. */
    accent?: boolean;
    children: ReactNode;
    style?: CSSProperties;
}

export function Panel({ title, titleMeta, accent, children, style }: PanelProps) {
    return (
        <div
            style={{
                border: '1px solid var(--line)',
                borderLeft: accent ? '2px solid var(--worm)' : '1px solid var(--line)',
                borderRadius: 4,
                padding: '16px 18px',
                background: 'var(--panel)',
                color: 'var(--paper)',
                boxSizing: 'border-box',
                ...style,
            }}
        >
            {(title || titleMeta) && (
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        justifyContent: 'space-between',
                        gap: 12,
                        marginBottom: 14,
                    }}
                >
                    {title && <span className="kicker">{title}</span>}
                    {titleMeta && <span className="kicker" style={{ color: 'var(--paper-faint)' }}>{titleMeta}</span>}
                </div>
            )}
            {children}
        </div>
    );
}
