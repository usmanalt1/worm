from django.db.models import Avg, ExpressionWrapper, FloatField, Sum
from django.db.models.functions import NullIf

from app.models import FctAdvancedTeamSeasonStats, FctTeamStats


def _round(value, digits: int = 1):
    """float() first: SQL numeric arrives as Decimal and would serialise as a string."""
    return None if value is None else round(float(value), digits)


def league_trends(season_type: str) -> list[dict]:
    """League-wide scoring, three-point share and pace, one row per season, oldest first."""
    scoring = (
        FctTeamStats.objects
        .filter(season_type=season_type)
        .values("season")
        .annotate(
            points_per_game=Avg("pts"),
            # From season totals: averaging per-game ratios overweights a low-volume night.
            three_point_attempt_share=ExpressionWrapper(
                Sum("fg3a") * 100.0 / NullIf(Sum("fga"), 0),
                output_field=FloatField(),
            ),
        )
        .order_by("season")
    )

    pace_by_season = {
        row["season"]: row["pace"]
        for row in (
            FctAdvancedTeamSeasonStats.objects
            .filter(season_type=season_type)
            .values("season")
            .annotate(pace=Avg("pace"))
        )
    }

    return [
        {
            "season": row["season"],
            "points_per_game": _round(row["points_per_game"]),
            "three_point_attempt_share": _round(row["three_point_attempt_share"]),
            "pace": _round(pace_by_season.get(row["season"])),
        }
        for row in scoring
    ]
