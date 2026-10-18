import { PRESETS, type Preset } from './presets';

interface PresetRailProps {
    active: string | null;
    onApply: (preset: Preset) => void;
}

function Card({ preset, active, onApply }: { preset: Preset; active: boolean; onApply: () => void }) {
    return (
        <button
            type="button"
            onClick={onApply}
            aria-pressed={active}
            style={{
                textAlign: 'left',
                cursor: 'pointer',
                padding: '14px 16px',
                borderRadius: 4,
                background: active ? 'rgba(232, 98, 44, 0.06)' : 'var(--panel)',
                border: '1px solid var(--line)',
                borderLeft: active ? '2px solid var(--worm)' : '1px solid var(--line)',
                color: 'var(--paper)',
                minWidth: 0,
                transition: 'background 120ms',
            }}
        >
            <div
                style={{
                    fontFamily: "'Oswald', sans-serif",
                    fontSize: 15,
                    fontWeight: 600,
                    letterSpacing: '0.01em',
                    marginBottom: 6,
                    color: active ? 'var(--worm)' : 'var(--paper)',
                }}
            >
                {preset.title}
            </div>
            <div style={{ fontSize: 12, color: 'var(--paper-dim)', lineHeight: 1.4 }}>{preset.blurb}</div>
        </button>
    );
}

export function PresetRail({ active, onApply }: PresetRailProps) {
    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
            {PRESETS.map(preset => (
                <Card
                    key={preset.id}
                    preset={preset}
                    active={active === preset.id}
                    onApply={() => onApply(preset)}
                />
            ))}
        </div>
    );
}
