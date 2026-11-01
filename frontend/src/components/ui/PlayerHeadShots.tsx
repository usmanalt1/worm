export function PlayerHeadShots({ playerId }: { playerId: number }) {
    return (
        <img src={`https://cdn.nba.com/headshots/nba/latest/260x190/${playerId}.png`} alt="Player Headshot" loading="lazy" style={{ display: 'block', height: 100, width: 'auto' }} />
    );
}           