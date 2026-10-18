from django.db.models import Avg, Count

from app.models import MartTeamStrength

# mart_team_strength carries no season_type, so the stage comes from the game_id prefix.
# Mirrors the season_type_from_game_id macro in pipeline_nba/macros/season_type.sql.
GAME_ID_PREFIX = {"regular": "002", "playoffs": "004", "preseason": "001"}


def team_context(season: str, season_type: str) -> list[dict]:
    """Per-team Elo, strength of schedule and schedule-adjusted margin for one season.

    adj_margin is margin credited for opponent quality, so the gap between it and a
    team's raw plus/minus is what the schedule was worth to them.
    """
    prefix = GAME_ID_PREFIX.get(season_type)
    if prefix is None:
        return []

    games = MartTeamStrength.objects.filter(season=season, game_id__startswith=prefix)

    aggregates = (
        games.values("team_id")
        .annotate(
            games_rated=Count("game_id"),
            opponent_elo=Avg("opponent_elo_pre"),
            adj_margin=Avg("adj_margin"),
        )
    )

    # Elo after a team's last game is its end-of-season rating. distinct on is Postgres
    # only, which this table already is: it is written by the ratings pipeline, not dbt.
    finals = {
        row["team_id"]: row["elo_post"]
        for row in games.order_by("team_id", "-game_date", "-game_id")
        .distinct("team_id")
        .values("team_id", "elo_post")
    }

    return [
        {
            "team_id": row["team_id"],
            "team_elo": _round(finals.get(row["team_id"]), 0),
            "opponent_elo": _round(row["opponent_elo"], 0),
            "adj_margin": _round(row["adj_margin"], 2),
            "games_rated": row["games_rated"],
        }
        for row in aggregates
    ]


def _round(value, digits: int):
    return None if value is None else round(value, digits)
