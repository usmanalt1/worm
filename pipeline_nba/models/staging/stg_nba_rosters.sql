SELECT
    CAST(team_id AS VARCHAR)   AS team_id,
    CAST(player_id AS VARCHAR) AS player_id,
    player                    AS player_name,
    age                       AS age,
    position,
    CAST(season_id AS VARCHAR) AS season_id,
    season,
    run_timestamp
-- Not partitioned on team_id: that keeps a row per team a player has been seen on.
FROM {{ get_latest_by_run_timestamp('teams_roster', 'season_id, player_id') }}