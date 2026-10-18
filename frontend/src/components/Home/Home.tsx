import { useMemo } from 'react';
import { Games } from '../ScrollableGames/Games';
import { HomeHero } from './HomeHero';
import { HomeHotCold } from './HomeHotCold';
import { HomeLastNight } from './HomeLastNight';
import { HomePostseason } from './HomePostseason';
import { HomeSeasonLeaders } from './HomeSeasonLeaders';
import { HomeModelPulse } from './HomeModelPulse';
import { HomePredictionRail } from './HomePredictionRail';
import { SectionHeader } from '../ui/SectionHeader';
import { usePredictionHistory } from '../../hooks/usePredictionHistory';
import { useStatsSeason } from '../../hooks/useStatsSeason';
import { computeModelStats } from '../../utils/modelStats';

/** Midnight today, so a game being played right now still counts as upcoming. */
function startOfToday(): number {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}

export function Home() {
    const {
        strategy, season, upcomingSeasonType, gradedSeasonType, upcoming, graded, loading,
    } = usePredictionHistory();
    const stats = useMemo(() => computeModelStats(graded), [graded]);

    // not necessarily the season being predicted - see useStatsSeason
    const statsSeason = useStatsSeason();

    // already unplayed and soonest first, across both season types
    const nextSlate = useMemo(() => {
        const today = startOfToday();
        return upcoming
            .filter((prediction) => new Date(prediction.game_date).getTime() >= today)
            .slice(0, 10);
    }, [upcoming]);

    const latest = useMemo(
        () => [...stats.graded]
            .sort((a, b) => new Date(b.game_date).getTime() - new Date(a.game_date).getTime())
            .slice(0, 10),
        [stats.graded],
    );

    const upsets = useMemo(
        () => stats.graded
            .filter((prediction) => !prediction.hit)
            .sort((a, b) => b.confidence - a.confidence)
            .slice(0, 10),
        [stats.graded],
    );

    const modelName = strategy?.replace(/_/g, ' ');
    const typeLabel = upcomingSeasonType === 'preseason' ? 'preseason' : 'season';

    // numbered in render order: the track record section hides itself early in a season
    let section = 0;
    const nextIndex = () => String(++section).padStart(2, '0');

    const hasTrackRecord = stats.games > 0;

    return (
        <div style={{ width: '100%', maxWidth: 1400, margin: '0 auto', paddingBottom: 60 }}>
            <HomeHero strategy={strategy} season={season} seasonType={upcomingSeasonType} statsSeason={statsSeason} />

            {hasTrackRecord && (
                <HomeModelPulse
                    strategy={strategy}
                    stats={stats}
                    index={nextIndex()}
                    seasonType={gradedSeasonType}
                />
            )}

            <section style={{ marginBottom: 'var(--section-gap)' }}>
                <SectionHeader
                    index={nextIndex()}
                    title="Next Up"
                    subtitle={modelName ? `What ${modelName} makes of the ${typeLabel} games still to come` : 'Upcoming predictions'}
                />
                <HomePredictionRail
                    predictions={nextSlate}
                    empty={loading ? 'Loading predictions…' : 'No upcoming games predicted yet.'}
                />
            </section>

            <HomeLastNight
                index={nextIndex()}
                strategy={strategy}
                stats={stats}
                loading={loading}
                seasonType={gradedSeasonType}
            />

            <section style={{ marginBottom: 'var(--section-gap)' }}>
                <SectionHeader
                    index={nextIndex()}
                    title="Around the League"
                    subtitle={statsSeason ? `Final scores from the end of ${statsSeason}` : 'Most recent final scores'}
                />
                <Games season={statsSeason} />
            </section>

            <HomeSeasonLeaders index={nextIndex()} season={statsSeason} />

            <HomeHotCold index={nextIndex()} />

            <HomePostseason index={nextIndex()} />

        </div>
    );
}
