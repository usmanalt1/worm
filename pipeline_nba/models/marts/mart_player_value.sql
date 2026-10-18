{# One value per player per game, plus the average of their recent games.

   The rolling window deliberately crosses seasons: a player's quality carries over, and
   that is what lets a roster be rated on opening night, when team Elo still reflects last
   season's roster. #}

with scored as (
    select
        season,
        season_type,
        player_id,
        team_id,
        game_id,
        game_date,
        min as minutes,
        -- Hollinger game score: one number per game, scaled roughly like points.
        pts
        + 0.4 * fgm
        - 0.7 * fga
        - 0.4 * (fta - ftm)
        + 0.7 * oreb
        + 0.3 * dreb
        + stl
        + 0.7 * ast
        + 0.7 * blk
        - 0.4 * pf
        - tov as game_score
    from {{ ref('fct_player_stats') }}
    where season_type = 'regular'
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
