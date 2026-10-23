from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from nba_api.stats.library.parameters import SeasonType, SeasonTypeAllStar, SeasonTypePlayoffs

REGULAR = SeasonType.default
PLAYOFFS = SeasonTypePlayoffs.playoffs
PRESEASON = SeasonTypeAllStar.preseason

ALL_SEASON_TYPES = (PRESEASON, REGULAR, PLAYOFFS)

# What the marts key on; the API strings above are not stored.
STORED_SEASON_TYPE = {
    REGULAR: "regular",
    PLAYOFFS: "playoffs",
    PRESEASON: "preseason",
}


SEASON_TYPE_NAMES = {
    "preseason": PRESEASON,
    "regular": REGULAR,
    "playoffs": PLAYOFFS,
}


def season_types_from_names(names) -> tuple:
    """Map friendly names ("playoffs") onto the values the endpoints take."""
    resolved = []
    for name in names:
        key = name.strip().lower()
        if key not in SEASON_TYPE_NAMES:
            raise ValueError(
                f"Unknown season type '{name}'. Choose from: {', '.join(SEASON_TYPE_NAMES)}"
            )
        resolved.append(SEASON_TYPE_NAMES[key])
    return tuple(resolved)


class Grain(Enum):
    PER_GAME = "per_game"
    PER_SEASON_ENTITY = "per_season_entity"
    SNAPSHOT = "snapshot"
    REFERENCE = "reference"


def season_id_for(season_year: str) -> str:
    """e.g. "2026-27" -> "26027"."""
    start, end = season_year.split("-")
    return f"{start[-2:]}0{end[-2:]}"


def season_year_for(as_of: date) -> str:
    """The season containing a date; July onward belongs to the season about to start."""
    start = as_of.year - 1 if as_of.month <= 9 else as_of.year
    return f"{start}-{str(start + 1)[2:]}"


@dataclass(frozen=True)
class CollectionRequest:
    """Seasons x season types x tables. An empty `tables` means every registered table."""

    seasons: tuple
    season_types: tuple = (REGULAR,)
    tables: tuple = ()
    run_id: str = None
    as_of: date = field(default_factory=date.today)


@dataclass(frozen=True)
class WorkItem:
    """One collector call: a dataset for one season, and one season type where it applies."""

    dataset: str
    season_year: str
    season_type: str = None
    as_of: date = None

    @property
    def season_id(self) -> str:
        return season_id_for(self.season_year)
