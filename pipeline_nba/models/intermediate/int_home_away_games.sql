-- Matchup is the usual home/away signal, but a neutral-site game (NBA Cup in Las Vegas,
-- the global games) reads '@' on both team logs, so the schedule's designated home team
-- decides; matchup only covers games the schedule has not loaded.
WITH sides AS (
    SELECT
        t.game_id,
        t.game_date,
        t.season_id,
        t.season,
        t.team_id,
        t.team_abbreviation,
        t.team_name,
        t.wl,
        t.pts,
        t.run_timestamp,
        CASE
            WHEN t.team_id = s.home_team_id THEN TRUE
            WHEN t.team_id = s.away_team_id THEN FALSE
            ELSE COALESCE(t.matchup LIKE '%vs.%', FALSE)
        END AS is_home
    FROM {{ ref('stg_nba_team_logs') }} t
    LEFT JOIN {{ ref('stg_nba_game_schedule') }} s ON s.game_id = t.game_id
),
-- Ranked rather than filtered on is_home, so a game whose two logs agree on a side
-- still produces one home and one away row instead of dropping out of the join.
ranked AS (
    SELECT
        sides.*,
        ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY is_home DESC, team_id) AS side
    FROM sides
),
played AS (
    SELECT
        h.game_id,
        h.game_date,
        h.season_id,
        h.season,
        h.team_id           AS home_team_id,
        h.team_abbreviation AS home_team_abbreviation,
        h.team_name         AS home_team_name,
        h.pts               AS home_pts,
        h.wl                AS home_wl,
        a.team_id           AS away_team_id,
        a.team_abbreviation AS away_team_abbreviation,
        a.team_name         AS away_team_name,
        a.pts               AS away_pts,
        a.wl                AS away_wl,
        -- The staging dedup is per team-game, so the two logs can land in different runs.
        GREATEST(h.run_timestamp, a.run_timestamp) AS run_timestamp
    FROM ranked h
    INNER JOIN ranked a ON a.game_id = h.game_id AND a.side = 2
    WHERE h.side = 1
),
-- Scheduled games with no box score yet; excluded once played, so the real result wins.
latest_season_id AS (
    SELECT MAX(season_id) AS season_id
    FROM {{ ref('stg_nba_game_schedule') }}
),

nba_teams as (
    SELECT team_id, team_abbreviation, team_name
    FROM {{ ref('stg_nba_teams') }} team_stats
    inner join latest_season_id lsi on lsi.season_id = team_stats.season_id
),

scheduled AS (
    SELECT
        s.game_id,
        s.game_date,
        s.season_id,
        s.season,
        s.home_team_id,
        ht.team_abbreviation AS home_team_abbreviation,
        ht.team_name         AS home_team_name,
        CAST(NULL AS DOUBLE PRECISION) AS home_pts,
        CAST(NULL AS VARCHAR)          AS home_wl,
        s.away_team_id,
        awt.team_abbreviation AS away_team_abbreviation,
        awt.team_name         AS away_team_name,
        CAST(NULL AS DOUBLE PRECISION) AS away_pts,
        CAST(NULL AS VARCHAR)          AS away_wl,
        s.run_timestamp
    FROM {{ ref('stg_nba_game_schedule') }} s
    LEFT JOIN nba_teams ht ON ht.team_id = s.home_team_id
    LEFT JOIN nba_teams awt ON awt.team_id = s.away_team_id
    WHERE s.game_id NOT IN (SELECT game_id FROM played)
)

SELECT * FROM played
UNION ALL
SELECT * FROM scheduled