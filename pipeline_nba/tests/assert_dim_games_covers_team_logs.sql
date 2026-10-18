-- Every game with a box score reaches dim_games; the home/away split must not drop one.
select t.game_id
from {{ ref('fct_team_stats') }} t
left join {{ ref('dim_games') }} g on g.game_id = t.game_id
where g.game_id is null
group by t.game_id
