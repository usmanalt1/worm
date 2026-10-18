import { useMemo, type ReactNode } from 'react';
import { SegmentedControl } from '@mantine/core';
import { HeroStat, PageHero } from '../ui/PageHero';
import { SectionHeader } from '../ui/SectionHeader';
import { HomeMostImproved } from '../Home/HomeMostImproved';
import { SeasonStandings } from './SeasonStandings';
import { AnalyticsScatter } from './AnalyticsScatter';
import { AnalyticsTable } from './AnalyticsTable';
import { FourFactors } from './FourFactors';
import { LeagueTrends } from './LeagueTrends';
import { MetricLeaderboards } from './MetricLeaderboards';
import { MetricPicker } from './MetricPicker';
import { PresetRail } from './PresetRail';
import { ScopeBar } from './ScopeBar';
import { useAnalyticsQuery } from './useAnalyticsQuery';
import { useAnalyticsRows } from '../../hooks/useAnalyticsRows';
import { useViewDataFilters } from '../ViewData/ViewDataFiltersContext';
import type { AnalyticsView } from '../../types/analytics';
import type { Stage } from '../ViewData/stages';

const VIEW_OPTIONS = [
    { value: 'table', label: 'Table' },
    { value: 'scatter', label: 'Scatter' },
];
const TEAM_VIEW_OPTIONS = [...VIEW_OPTIONS, { value: 'factors', label: 'Factors' }];

function Section({ index, title, subtitle, meta, children }: {
    index: string;
    title: string;
    subtitle: string;
    meta?: ReactNode;
    children: ReactNode;
}) {
    return (
        <section style={{ marginBottom: 'var(--section-gap)' }}>
            <SectionHeader index={index} title={title} subtitle={subtitle} meta={meta} />
            {children}
        </section>
    );
}

export function Analytics() {
    // The stage still follows you to View Data, but the URL is what this page reads.
    const { setSelectedStage } = useViewDataFilters();

    const { query, seasons, setScope, setView, setMetrics, setAxes, setSeason, setStage, setMinGames, applyPreset } =
        useAnalyticsQuery();

    const seasonScope = query.scope === 'season';
    const factorsView = query.view === 'factors';
    // The axes can name a metric the chips do not, and a derived axis still needs
    // its endpoint fetched or the plot comes back empty.
    const activeMetrics = useMemo(
        () => (query.view === 'scatter' ? [...query.metrics, query.x, query.y] : query.metrics),
        [query.view, query.metrics, query.x, query.y],
    );

    const { rows, loading, error } = useAnalyticsRows(
        query.entity,
        seasonScope ? null : query.season,
        query.seasonType,
        activeMetrics,
    );

    const qualified = useMemo(
        () => rows.filter(row => (row.games_played ?? 0) >= query.minGames),
        [rows, query.minGames],
    );

    const noun = query.entity === 'player' ? 'player' : 'team';
    const stage = query.stage.toLowerCase();
    const slice = `${query.season ?? ''} ${stage}`.trim();

    const empty = error
        ? error
        : rows.length > 0
            ? `No ${noun} has ${query.minGames}+ games in the ${slice}. Drop the minimum to see more.`
            : `No ${noun} stats for the ${slice} yet.`;

    const viewToggle = (
        <SegmentedControl
            size="xs"
            value={query.view}
            onChange={value => setView(value as AnalyticsView)}
            data={query.entity === 'team' ? TEAM_VIEW_OPTIONS : VIEW_OPTIONS}
        />
    );

    const onStage = (next: Stage) => {
        setStage(next);
        setSelectedStage(next);
    };

    return (
        <div style={{ width: '100%', maxWidth: 1400, margin: '0 auto', paddingBottom: 60 }}>
            <PageHero
                eyebrow="Build Your Own"
                title="Wormalytics"
                blurb="Pick a scope, a season and your own metrics. Every view is a URL, so the one you build is the one you can send."
            >
                <HeroStat
                    label={seasonScope ? 'Scope' : `Qualified ${noun}s`}
                    value={seasonScope ? 'League' : loading ? '—' : String(qualified.length)}
                />
            </PageHero>

            <div style={{ marginTop: 20, marginBottom: 'var(--section-gap)' }}>
                <ScopeBar
                    query={query}
                    seasons={seasons}
                    onScope={setScope}
                    onSeason={setSeason}
                    onStage={onStage}
                    onMinGames={setMinGames}
                />
            </div>

            <Section
                index="01"
                title="Off the Shelf"
                subtitle="A starting point you can nudge; changing anything leaves a view of your own"
            >
                <PresetRail
                    active={query.preset}
                    onApply={preset => applyPreset({
                        // Clear what this preset doesn't set, so presets can't inherit each other.
                        x: null, y: null, metrics: null,
                        ...preset.params,
                        preset: preset.id,
                    })}
                />
            </Section>

            {seasonScope ? (
                <Section
                    index="02"
                    title="League Trends"
                    subtitle="How the league itself has changed, season by season"
                >
                    <LeagueTrends seasonType={query.seasonType} season={query.season} />
                </Section>
            ) : (
                <>
                    {factorsView ? (
                        <Section
                            index="02"
                            title="Four Factors"
                            subtitle={`What actually decides games, and what each team is worst at, ${slice}`}
                            meta={viewToggle}
                        >
                            <FourFactors rows={qualified} loading={loading} empty={empty} />
                        </Section>
                    ) : (
                        <>
                            <Section
                                index="02"
                                title="Build Your View"
                                subtitle="Every metric the warehouse holds; the first three feed the leaderboards"
                                meta={viewToggle}
                            >
                                <MetricPicker
                                    entity={query.entity}
                                    view={query.view}
                                    metrics={query.metrics}
                                    x={query.x}
                                    y={query.y}
                                    onMetrics={setMetrics}
                                    onAxes={setAxes}
                                />
                            </Section>

                            <Section
                                index="03"
                                title={query.entity === 'player' ? 'Players' : 'Teams'}
                                subtitle={
                                    query.view === 'scatter'
                                        ? `Each ${noun} in the ${slice}, plotted on your two axes`
                                        : `Your metrics for the ${slice}, sortable on any column`
                                }
                            >
                                {query.view === 'scatter' ? (
                                    <AnalyticsScatter
                                        rows={qualified}
                                        entity={query.entity}
                                        x={query.x}
                                        y={query.y}
                                        empty={empty}
                                    />
                                ) : (
                                    <AnalyticsTable
                                        rows={qualified}
                                        metrics={query.metrics}
                                        entity={query.entity}
                                        loading={loading}
                                        empty={empty}
                                    />
                                )}
                            </Section>

                            <Section
                                index="04"
                                title="Leaders"
                                subtitle={`The first three metrics you picked, ranked over the ${slice}`}
                            >
                                <MetricLeaderboards rows={qualified} metrics={query.metrics} empty={empty} />
                            </Section>
                        </>
                    )}

                    <Section
                        index={factorsView ? '03' : '05'}
                        title="Most Improved"
                        subtitle="Biggest jumps against the season before"
                    >
                        <HomeMostImproved seasonType={query.seasonType} />
                    </Section>

                    {query.entity === 'team' && (
                        <Section
                            index={factorsView ? '04' : '06'}
                            title="Standings"
                            subtitle={`The ${slice} table, sortable on any column`}
                        >
                            <SeasonStandings
                                season={query.season}
                                seasonType={query.seasonType}
                                stageLabel={query.stage}
                            />
                        </Section>
                    )}
                </>
            )}
        </div>
    );
}
