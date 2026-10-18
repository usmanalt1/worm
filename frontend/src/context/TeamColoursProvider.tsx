import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { apiFetch } from '../lib/api';
import { CLASH_DISTANCE, chipText, rgbDistance } from '../lib/colour';

interface TeamColourRow {
    team_id: number;
    abbreviation: string;
    team_name: string;
    display_hex: string | null;
    alt_display_hex: string | null;
}

export interface TeamColours {
    /** The colour to paint. In a matchup this is already swapped to `alt` on a clash. */
    colour: string;
    alt: string;
    text: string;
    abbr: string;
    name: string;
    /** False for a team the seed doesn't cover, so chips can go neutral. */
    known: boolean;
}

/** A team id, an abbreviation, or a full team name - whatever the endpoint gave you. */
export type TeamKey = string | number | null | undefined;

interface Lookups {
    byId: Map<number, TeamColours>;
    byAbbr: Map<string, TeamColours>;
    byName: Map<string, TeamColours>;
}

// Names dim_games spells differently from dim_teams, e.g. "LA Clippers".
const NAME_ALIASES: Record<string, string> = {
    laclippers: 'LAC',
};

const TeamColoursContext = createContext<Lookups | null>(null);

function normalise(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function emptyLookups(): Lookups {
    return { byId: new Map(), byAbbr: new Map(), byName: new Map() };
}

function buildLookups(rows: readonly TeamColourRow[]): Lookups {
    const lookups = emptyLookups();

    for (const row of rows) {
        const colour = row.display_hex;
        const team: TeamColours = colour
            ? {
                colour,
                alt: row.alt_display_hex ?? colour,
                text: chipText(colour),
                abbr: row.abbreviation,
                name: row.team_name,
                known: true,
            }
            : {
                colour: 'var(--panel-2)',
                alt: 'var(--panel-2)',
                text: 'var(--paper-dim)',
                abbr: row.abbreviation,
                name: row.team_name,
                known: false,
            };

        lookups.byId.set(row.team_id, team);
        lookups.byAbbr.set(row.abbreviation.toUpperCase(), team);
        lookups.byName.set(normalise(row.team_name), team);
    }

    return lookups;
}

function resolve(lookups: Lookups, key: TeamKey): TeamColours | null {
    if (key === null || key === undefined) return null;
    if (typeof key === 'number') return lookups.byId.get(key) ?? null;

    const raw = key.trim();
    if (!raw) return null;

    if (/^\d+$/.test(raw)) {
        const byId = lookups.byId.get(Number(raw));
        if (byId) return byId;
    }

    const byAbbr = lookups.byAbbr.get(raw.toUpperCase());
    if (byAbbr) return byAbbr;

    const name = normalise(raw);
    const alias = NAME_ALIASES[name];
    return lookups.byName.get(name) ?? (alias ? lookups.byAbbr.get(alias) ?? null : null);
}

function shortLabel(name: string): string {
    const letters = name.replace(/[^a-zA-Z0-9]/g, '');
    return letters ? letters.slice(0, 3).toUpperCase() : '—';
}

function unknownSide(key: TeamKey, colour: string): TeamColours {
    const name = typeof key === 'string' && key.trim() ? key.trim() : 'Unknown team';
    return { colour, alt: colour, text: 'var(--paper)', abbr: shortLabel(name), name, known: false };
}

function pairTeams(
    away: TeamColours | null,
    home: TeamColours | null,
    awayKey: TeamKey,
    homeKey: TeamKey,
): { away: TeamColours; home: TeamColours } {
    const homeSide = home ?? unknownSide(homeKey, 'var(--home)');
    const awaySide = away ?? unknownSide(awayKey, 'var(--away)');

    // Only the away side moves, so home always looks like itself.
    if (away && home && rgbDistance(away.colour, home.colour) < CLASH_DISTANCE) {
        return { away: { ...away, colour: away.alt, text: chipText(away.alt) }, home: homeSide };
    }

    return { away: awaySide, home: homeSide };
}

export function TeamColoursProvider({ children }: { children: ReactNode }) {
    const [rows, setRows] = useState<readonly TeamColourRow[]>([]);

    useEffect(() => {
        let cancelled = false;
        apiFetch('/api/nba/db/team_colours')
            .then(r => r.json())
            .then((data: TeamColourRow[]) => {
                if (!cancelled && Array.isArray(data)) setRows(data);
            })
            .catch(() => { /* consumers fall back to neutral chips */ });

        return () => { cancelled = true; };
    }, []);

    const lookups = useMemo(() => buildLookups(rows), [rows]);

    return <TeamColoursContext.Provider value={lookups}>{children}</TeamColoursContext.Provider>;
}

/** Null until the colours land, and for any team the seed doesn't cover. */
export function useTeam(key: TeamKey): TeamColours | null {
    const lookups = useContext(TeamColoursContext);
    return useMemo(() => (lookups ? resolve(lookups, key) : null), [lookups, key]);
}

/** For lists and charts, where a hook call per row isn't possible. */
export function useTeamResolver(): (key: TeamKey) => TeamColours | null {
    const lookups = useContext(TeamColoursContext);
    return useCallback((key: TeamKey) => (lookups ? resolve(lookups, key) : null), [lookups]);
}

/** Both sides of a matchup, with the clash swap and the --away/--home fallbacks applied. */
export function useTeamPair(awayKey: TeamKey, homeKey: TeamKey) {
    const away = useTeam(awayKey);
    const home = useTeam(homeKey);
    return useMemo(() => pairTeams(away, home, awayKey, homeKey), [away, home, awayKey, homeKey]);
}
