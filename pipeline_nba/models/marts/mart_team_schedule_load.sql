{# Travel and schedule load per team-game. Built on dim_games, which carries scheduled
   games too, so every column here is known before tip-off. #}

with team_games as (
    select
        season, season_id, season_type, game_id, game_date,
        home_team_id as team_id,
        home_team_id as venue_team_id,
        1 as is_home
    from {{ ref('dim_games') }}

    union all

    select
        season, season_id, season_type, game_id, game_date,
        away_team_id as team_id,
        home_team_id as venue_team_id,
        0 as is_home
    from {{ ref('dim_games') }}
),

located as (
    select
        t.season,
        t.season_id,
        t.season_type,
        t.game_id,
        t.game_date,
        t.team_id,
        t.is_home,
        v.latitude         as venue_lat,
        v.longitude        as venue_lon,
        v.altitude_m       as venue_altitude_m,
        v.utc_offset_hours as venue_utc_offset
    from team_games t
    join {{ ref('team_locations') }} v on v.team_id = t.venue_team_id
),

sequenced as (
    select
        located.*,
        lag(venue_lat) over w        as prev_lat,
        lag(venue_lon) over w        as prev_lon,
        lag(venue_altitude_m) over w as prev_altitude_m,
        lag(venue_utc_offset) over w as prev_utc_offset,
        -- Home games so far cuts the season into road trips: each block is one home game
        -- plus the away games that follow it.
        sum(is_home) over (
            partition by team_id, season order by game_date, game_id
            rows between unbounded preceding and current row
        ) as home_block
    from located
    window w as (partition by team_id, season order by game_date, game_id)
),

trips as (
    select
        sequenced.*,
        sum(case when is_home = 0 then 1 else 0 end) over (
            partition by team_id, season, home_block order by game_date, game_id
            rows between unbounded preceding and current row
        ) as road_trip_game
    from sequenced
),

-- Self-join rather than a RANGE window, which each warehouse spells differently.
density as (
    select
        t.team_id,
        t.season,
        t.game_id,
        count(p.game_id) as games_prev_7d
    from trips t
    left join trips p
        on  p.team_id = t.team_id
        and p.season = t.season
        and p.game_date < t.game_date
        and p.game_date >= t.game_date - 7
    group by t.team_id, t.season, t.game_id
)

select
    t.season,
    t.season_id,
    t.season_type,
    t.game_id,
    t.game_date,
    t.team_id,
    t.is_home,
    t.venue_altitude_m,
    t.road_trip_game,
    d.games_prev_7d,
    -- 0, not null, on a team's first game of a season: there is no previous venue, so
    -- there is no travel load carried into it.
    coalesce({{ haversine_km('t.prev_lat', 't.prev_lon', 't.venue_lat', 't.venue_lon') }}, 0) as travel_km,
    coalesce(t.venue_utc_offset - t.prev_utc_offset, 0) as tz_delta,
    coalesce(t.venue_altitude_m - t.prev_altitude_m, 0) as altitude_gain
from trips t
join density d
    on d.team_id = t.team_id and d.season = t.season and d.game_id = t.game_id
