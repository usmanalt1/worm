import { NumberInput, SegmentedControl, Select } from '@mantine/core';
import type { ReactNode } from 'react';
import { STAGES, type Stage } from '../ViewData/stages';
import type { AnalyticsQuery } from './useAnalyticsQuery';
import type { AnalyticsScope } from '../../types/analytics';

interface ScopeBarProps {
    query: AnalyticsQuery;
    seasons: string[];
    onScope: (scope: AnalyticsScope) => void;
    onSeason: (season: string | null) => void;
    onStage: (stage: Stage) => void;
    onMinGames: (value: number) => void;
}

const SCOPE_OPTIONS = [
    { value: 'player', label: 'Players' },
    { value: 'team', label: 'Teams' },
    { value: 'season', label: 'Seasons' },
];

function Field({ label, children }: { label: string; children: ReactNode }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
            <span className="kicker">{label}</span>
            {children}
        </div>
    );
}

export function ScopeBar({ query, seasons, onScope, onSeason, onStage, onMinGames }: ScopeBarProps) {
    const seasonScope = query.scope === 'season';

    return (
        <div
            style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'flex-end',
                gap: 20,
                padding: '16px 18px',
                border: '1px solid var(--line)',
                borderRadius: 4,
                background: 'var(--panel)',
            }}
        >
            <Field label="Scope">
                <SegmentedControl
                    size="xs"
                    value={query.scope}
                    onChange={value => onScope(value as AnalyticsScope)}
                    data={SCOPE_OPTIONS}
                />
            </Field>

            <Field label="Stage">
                <SegmentedControl
                    size="xs"
                    value={query.stage}
                    onChange={value => onStage(value as Stage)}
                    data={[...STAGES]}
                />
            </Field>

            <Field label={seasonScope ? 'Highlight season' : 'Season'}>
                <Select
                    size="xs"
                    style={{ width: 130 }}
                    data={seasons}
                    value={query.season}
                    onChange={onSeason}
                    searchable
                    allowDeselect={false}
                    placeholder={seasons.length ? 'Pick a season' : 'Loading…'}
                />
            </Field>

            {/* Season scope aggregates whole seasons, so there is nothing to qualify. */}
            {!seasonScope && (
                <Field label="Min games">
                    <NumberInput
                        size="xs"
                        style={{ width: 90 }}
                        min={0}
                        max={82}
                        step={1}
                        clampBehavior="strict"
                        value={query.minGames}
                        onChange={value => onMinGames(Number(value) || 0)}
                    />
                </Field>
            )}
        </div>
    );
}
