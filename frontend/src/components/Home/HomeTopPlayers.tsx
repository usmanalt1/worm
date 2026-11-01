import type { PlayerOption } from '../../hooks/useLatestPlayerBoxScores';
import { Panel } from '../ui/Panel';
import { PlayerHeadShots } from '../ui/PlayerHeadShots';
import { SectionHeader } from '../ui/SectionHeader';

interface TopPlayersProps {
    index: string;
    topPlayers: PlayerOption[];
}

function Stat({ label, value }: { label: string; value: number }) {
    return (
        <div style={{ textAlign: 'center' }}>
            <div className="kicker" style={{ color: 'var(--paper-faint)' }}>{label}</div>
            <div style={{ fontFamily: 'var(--mono)', fontVariantNumeric: 'tabular-nums', fontSize: 15 }}>
                {value}
            </div>
        </div>
    );
}

export function HomeTopPlayers({ index, topPlayers }: TopPlayersProps) {
    return (
        <section style={{ marginBottom: 'var(--section-gap)' }}>
            <SectionHeader
                index={index}
                title="Top Performers"
                subtitle="Who put up the biggest numbers on the most recent slate"
            />

            {topPlayers.length === 0 ? (
                <div style={{ fontSize: 13, color: 'var(--paper-faint)', padding: '8px 0' }}>
                    No top players available.
                </div>
            ) : (
                <div className="rail">
                    <div style={{ display: 'flex', gap: 14, width: 'max-content' }}>
                        {topPlayers.map((player) => (
                            <Panel
                                key={player.player_id}
                                style={{
                                    width: 196,
                                    flexShrink: 0,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    gap: 10,
                                }}
                            >
                                <PlayerHeadShots playerId={player.player_id} />

                                <div style={{ alignSelf: 'stretch', textAlign: 'center', minWidth: 0 }}>
                                    <div
                                        style={{
                                            fontFamily: 'var(--heading)',
                                            fontSize: 15,
                                            whiteSpace: 'nowrap',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                        }}
                                    >
                                        {player.player_name}
                                    </div>
                                    <span className="kicker" style={{ color: 'var(--paper-faint)' }}>
                                        {player.team_abbreviation}
                                    </span>
                                </div>

                                <div style={{ display: 'flex', gap: 16 }}>
                                    <Stat label="Pts" value={player.points} />
                                    <Stat label="Reb" value={player.rebounds} />
                                    <Stat label="Ast" value={player.assists} />
                                </div>
                            </Panel>
                        ))}
                    </div>
                </div>
            )}
        </section>
    );
}
