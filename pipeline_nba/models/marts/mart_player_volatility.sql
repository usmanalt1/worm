{# Game-to-game swing in a player's output, with the league moments needed to shrink it.

   Volatility is neutral: a high value is a boom-or-bust creator, not a worse player.

   Adjusted for minutes twice, for two different reasons: within a player, so the measure
   is not picking up role churn; and across the league, because a per-36 rate is genuinely
   noisier when extrapolated from short stints, which left raw volatility correlated -0.35
   with minutes per game and so ranked bench role as much as temperament.

   Regular season only, inherited from mart_player_value. #}

{% set min_minutes = 10 %}
{% set min_games = 15 %}
{% set min_games_for_moments = 30 %}

with games as (
    -- A short stint swamps a per-36 rate, so those are out before anything is fitted.
    select
        season,
        season_type,
        player_id,
        minutes,
        game_score / minutes * 36.0 as per36
    from {{ ref('mart_player_value') }}
    where minutes >= {{ min_minutes }}
),

-- Fit per36 on minutes per player: without this the measure picks up role churn
-- (a 12-minute night next to a 38-minute one) rather than reliability of output.
fits as (
    select
        season,
        season_type,
        player_id,
        count(*) as games,
        sum(minutes) as minutes_total,
        avg(per36) as mean_per36,
        regr_slope(per36, minutes) as slope,
        regr_intercept(per36, minutes) as intercept
    from games
    group by 1, 2, 3
    having count(*) >= {{ min_games }}
),

residuals as (
    select
        f.season,
        f.season_type,
        f.player_id,
        f.games,
        f.minutes_total,
        f.mean_per36,
        -- A player whose minutes never vary has no slope; fall back to a plain mean.
        sum(power(
            g.per36 - (coalesce(f.intercept, f.mean_per36) + coalesce(f.slope, 0) * g.minutes),
            2
        )) as sq_error
    from fits f
    join games g
        on g.player_id = f.player_id
        and g.season = f.season
        and g.season_type = f.season_type
    group by 1, 2, 3, 4, 5, 6
),

scored as (
    select
        season,
        season_type,
        player_id,
        games,
        minutes_total,
        mean_per36,
        minutes_total / games as minutes_per_game,
        -- Two fitted parameters, so the residual variance loses two degrees of freedom.
        sqrt(sq_error / (games - 2)) as volatility_raw,
        sqrt(sq_error / (games - 2)) / sqrt(2.0 * (games - 2)) as volatility_se
    from residuals
),

-- The league's volatility-to-minutes slope. Taken over a qualified population, as are
-- the moments below: short samples carry more sampling error, and including them inflates
-- the observed spread and so overstates tau.
role as (
    select
        season,
        season_type,
        regr_slope(volatility_raw, minutes_per_game) as role_slope,
        avg(minutes_per_game) as league_minutes_per_game
    from scored
    where games >= {{ min_games_for_moments }}
    group by 1, 2
),

adjusted as (
    select
        s.*,
        r.role_slope,
        -- Centred on the league's minutes load, so the adjustment removes the role
        -- effect without shifting the scale the reader sees.
        s.volatility_raw
            - coalesce(r.role_slope, 0) * (s.minutes_per_game - r.league_minutes_per_game)
            as volatility_adj
    from scored s
    join role r
        on r.season = s.season
        and r.season_type = s.season_type
),

moments as (
    select
        season,
        season_type,
        avg(volatility_adj) as league_mean,
        greatest(0, var_samp(volatility_adj) - avg(power(volatility_se, 2))) as tau_sq
    from adjusted
    where games >= {{ min_games_for_moments }}
    group by 1, 2
)

select
    a.season,
    a.season_type,
    a.player_id,
    a.games,
    a.minutes_total,
    a.minutes_per_game,
    a.mean_per36,
    a.volatility_raw,
    a.volatility_adj,
    a.volatility_se,
    a.role_slope,
    m.league_mean,
    sqrt(m.tau_sq) as tau,
    -- Empirical Bayes posterior mean: a noisy estimate is pulled toward the league.
    m.league_mean
        + (m.tau_sq / nullif(m.tau_sq + power(a.volatility_se, 2), 0))
        * (a.volatility_adj - m.league_mean) as volatility_shrunk
from adjusted a
join moments m
    on m.season = a.season
    and m.season_type = a.season_type
