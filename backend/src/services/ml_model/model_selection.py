"""Which strategy the home page presents, decided from how they have actually called games."""

from typing import List, Optional

from services.ml_model.prediction_history import read_graded

# The strategies sit about a point of accuracy apart, so a handful of graded games says
# nothing about which is ahead. This is a floor on absurdity, not a significance test:
# even a full season struggles to separate them.
MIN_GRADED_GAMES = 200


def brier_score(strategy: str, season: str, season_type: str) -> Optional[float]:
    """Mean squared error of this strategy's probabilities, lower being better.

    Scored on the forecast rather than on right-or-wrong, so a confident correct call
    beats a hesitant one and a confident miss is punished. None until there are
    MIN_GRADED_GAMES to judge on.
    """
    graded = read_graded(
        strategy=strategy, season=season, season_type=season_type, graded_only=True,
    )
    if len(graded) < MIN_GRADED_GAMES:
        return None

    squared_errors = [
        (row["home_win_probability"] - (1.0 if row["actual_home_win"] else 0.0)) ** 2
        for row in graded
    ]

    return sum(squared_errors) / len(squared_errors)


def best_strategy(season: str, season_type: str, candidates: List[str]) -> Optional[str]:
    """The best-scoring candidate, None while the season is too young to tell them apart.

    None is the useful answer early on: it leaves the caller on its configured default
    rather than chasing whichever strategy got lucky in the opening week.
    """
    scored = [
        (strategy, score)
        for strategy, score in ((name, brier_score(name, season, season_type)) for name in candidates)
        if score is not None
    ]
    if not scored:
        return None

    # min keeps the first of equal scores, so a tie falls to the order candidates came in
    return min(scored, key=lambda pair: pair[1])[0]
