-- Rosters drive this, not the players feed: a player on a roster is in the league even
-- when the feed has not caught up, and the feed carries players who have left it.
select
    CAST(r.player_id AS INTEGER) as player_id,
    r.season_id,
    coalesce(p.player_name, r.player_name) as player_name,
    r.age,
    r.position,
    p.first_name,
    p.last_name,
    coalesce(p.is_active, TRUE) as is_active,
    r.season,
    r.run_timestamp
FROM {{ ref('stg_nba_rosters') }} r
left join {{ ref('stg_nba_players') }} p
    on r.player_id = CAST(p.player_id AS VARCHAR)
    -- season_id, not season: it pins both sides to the same collection run, and the
    -- feed has carried more than one season_id for a single season.
    and r.season_id = p.season_id
