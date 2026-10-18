from app.models import MartPlayerVolatility

FIELDS = (
    "player_id",
    "games",
    "minutes_per_game",
    "volatility_raw",
    "volatility_adj",
    "volatility_se",
    "volatility_shrunk",
    "league_mean",
    "tau",
)


def player_volatility(season: str, season_type: str) -> list[dict]:
    """Per-player game-to-game swing for one season, shrunk toward the league mean.

    `volatility` is the role-adjusted, shrunk estimate, which is what should be ranked.
    The raw one overstates the spread (a short sample carries more sampling error) and
    correlates -0.35 with minutes per game, so it part-ranks bench role.
    """
    rows = MartPlayerVolatility.objects.filter(
        season=season, season_type=season_type
    ).values(*FIELDS)

    return [
        {
            "player_id": row["player_id"],
            "volatility": _round(row["volatility_shrunk"], 2),
            "volatility_raw": _round(row["volatility_raw"], 2),
            "volatility_adj": _round(row["volatility_adj"], 2),
            "volatility_se": _round(row["volatility_se"], 3),
            # Not games_played: games under 10 minutes never entered the fit.
            "games_rated": row["games"],
            "league_mean": _round(row["league_mean"], 2),
            "tau": _round(row["tau"], 3),
        }
        for row in rows
    ]


def _round(value, digits: int):
    return None if value is None else round(value, digits)
