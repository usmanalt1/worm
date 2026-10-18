select
    player_id,
    player_name,
    draft_year,
    season,
    round_number,
    round_pick,
    overall_pick,
    draft_type,
    team_id as drafted_by_team_id,
    -- Pedigree bands kept here so a feature never re-derives them: 14 picks is the
    -- lottery, 15 the band being tested, 30 the first round.
    overall_pick <= 14 as is_lottery_pick,
    overall_pick <= 15 as is_top15_pick,
    round_number = 1 as is_first_round_pick,
    round_number = 2 as is_second_round_pick,
    run_timestamp
from {{ ref('stg_nba_draft_history') }}
