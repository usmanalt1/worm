import { Panel } from './Panel';
import { TeamChip } from './TeamChip';
import { useTeamPair, type TeamColours } from '../../context/TeamColoursProvider';

interface PredictionBarProps {
    homeTeam: string;
    awayTeam: string;
    homeWinProbability: number;
    homePts?: number;
    awayPts?: number;
    predictedHomeWin?: boolean;
    actualHomeWin?: boolean | null;
    gameDate?: string;
}

interface SideProps {
    team: string;
    pct: number;
    pts?: number;
    colours: TeamColours;
    picked: boolean;
}

function Side({ team, pct, pts, colours, picked }: SideProps) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '3px 0' }}>
            <TeamChip team={colours} />
            <span
                title={team}
                style={{
                    flex: 1,
                    minWidth: 0,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    fontSize: 13,
                    fontWeight: picked ? 600 : 400,
                    color: picked ? 'var(--paper)' : 'var(--paper-dim)',
                }}
            >
                {team}
            </span>
            {typeof pts === 'number' && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--paper)', fontVariantNumeric: 'tabular-nums' }}>
                    {pts}
                </span>
            )}
            <span
                style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 12,
                    color: picked ? 'var(--paper)' : 'var(--paper-dim)',
                    fontVariantNumeric: 'tabular-nums',
                    width: 34,
                    textAlign: 'right',
                }}
            >
                {pct}%
            </span>
        </div>
    );
}

export function PredictionBar({
    homeTeam,
    awayTeam,
    homeWinProbability,
    homePts,
    awayPts,
    predictedHomeWin,
    actualHomeWin,
    gameDate,
}: PredictionBarProps) {
    const homePct = Math.round(homeWinProbability * 100);
    const awayPct = 100 - homePct;
    const hasResult = typeof actualHomeWin === 'boolean';
    const correct = hasResult && predictedHomeWin === actualHomeWin;
    const { away, home } = useTeamPair(awayTeam, homeTeam);

    return (
        <Panel style={{ width: 284, flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span className="kicker">
                    {gameDate ? new Date(gameDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''}
                </span>
                {hasResult && (
                    <span
                        className="kicker"
                        style={{ color: correct ? 'var(--win)' : 'var(--lose)', fontWeight: 600 }}
                    >
                        {correct ? '✓ Hit' : '✕ Miss'}
                    </span>
                )}
            </div>

            <Side team={awayTeam} pct={awayPct} pts={awayPts} colours={away} picked={predictedHomeWin === false} />
            <Side team={homeTeam} pct={homePct} pts={homePts} colours={home} picked={predictedHomeWin === true} />

            <div style={{ display: 'flex', gap: 2, height: 6, marginTop: 10 }}>
                <div style={{ width: `${awayPct}%`, background: away.colour, borderRadius: '3px 0 0 3px' }} />
                <div style={{ flex: 1, background: home.colour, borderRadius: '0 3px 3px 0' }} />
            </div>
        </Panel>
    );
}
