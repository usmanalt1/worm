LOGISTIC_REGRESSION_MODEL = "logistic_regression_model"
RANDOM_FOREST_MODEL = "random_forest_model"
LAST_RUN = "last_run"
TEAM_COLOURS = "team_colours"


def model_run_cache_key(strategy: str, season: str, season_type: str) -> str:
    return f"model:{strategy}:{season}:{season_type}"


def user_run_cache_key(user_id: int, strategy: str, season: str, season_type: str, mode: str) -> str:
    """One Wormhole run. The "user:" prefix is what keeps it out of get_all_runs."""
    return f"user:{user_id}:run:{strategy}:{season}:{season_type}:{mode}"


def user_last_run_key(user_id: int) -> str:
    return f"user:{user_id}:last_run"


def hot_and_cold_cache_key(season: str, season_type: str, limit: int) -> str:
    """`season` is the requested one, so a cached entry covers the season resolution too."""
    return f"hot_and_cold_{season}_{season_type}_{limit}"


def league_trends_cache_key(season_type: str) -> str:
    """Versioned: an unversioned key served a previous build's payload shape for a day."""
    return f"league_trends_v1_{season_type}"
