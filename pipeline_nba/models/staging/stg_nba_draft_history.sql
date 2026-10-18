SELECT
    player_id,
    player_name,
    draft_year,
    season,
    round_number,
    round_pick,
    overall_pick,
    draft_type,
    team_id,
    run_timestamp
FROM {{ get_latest_by_run_timestamp('draft_history', 'player_id') }}
