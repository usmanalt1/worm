{# One value per player per game, plus the average of their recent games.

   The rolling window deliberately crosses seasons: a player's quality carries over, and
   that is what lets a roster be rated on opening night, when team Elo still reflects last
   season's roster. #}

with scored as (
    -- fct_player_stats has no game_date; inner join, as an unplaceable row cannot be ordered.
    select
        p.season,
        p.season_type,
        p.player_id,
        p.team_id,
        p.game_id,
        g.game_date,
        p.min as minutes,
        -- Hollinger game score: one number per game, scaled roughly like points.
        p.pts
        + 0.4 * p.fgm
        - 0.7 * p.fga
        - 0.4 * (p.fta - p.ftm)
        + 0.7 * p.oreb
        + 0.3 * p.dreb
        + p.stl
        + 0.7 * p.ast
        + 0.7 * p.blk
        - 0.4 * p.pf
        - p.tov as game_score
    from {{ ref('fct_player_stats') }} p
    join {{ ref('dim_games') }} g on g.game_id = p.game_id
    where p.season_type = 'regular'
)

select
    season,
    season_type,
    player_id,
    team_id,
    game_id,
    game_date,
    minutes,
    game_score,
    -- Ends one row short of this game, so a game is never inside its own value.
    avg(game_score) over w as value_pre,
    avg(minutes) over w as minutes_pre
from scored
window w as (
    partition by player_id order by game_date, game_id
    rows between 20 preceding and 1 preceding
)
