from services.data_collection.collectors.game_logs import PlayerGameLogs, TeamGameLogs
from services.data_collection.collectors.injuries import PlayerInjuries
from services.data_collection.collectors.matchups import TeamMatchups
from services.data_collection.collectors.reference import (
    PlayersInfo,
    SeasonRecord,
    TeamInfo,
    TeamRoster,
)
from services.data_collection.collectors.schedule import GameSchedule
from services.data_collection.collectors.season_stats import (
    AdvancedPlayerSeasonStats,
    AdvancedTeamSeasonStats,
)
from services.data_collection.nba_client import NBAClient

# Dependency-first, so a plan reads in the order it will run.
COLLECTOR_CLASSES = (
    SeasonRecord,
    TeamInfo,
    PlayersInfo,
    TeamRoster,
    TeamGameLogs,
    PlayerGameLogs,
    AdvancedPlayerSeasonStats,
    AdvancedTeamSeasonStats,
    GameSchedule,
    TeamMatchups,
    PlayerInjuries,
)


def build_registry(client: NBAClient = None) -> dict:
    client = client or NBAClient()
    return {cls.name: cls(client=client) for cls in COLLECTOR_CLASSES}


# A table can be written at more than one grain, so the mapping is explicit: a
# collection always means the per-game log, never a season-total endpoint.
DATASET_FOR_TABLE = {cls.table: cls.name for cls in COLLECTOR_CLASSES}

TABLES = tuple(DATASET_FOR_TABLE)


def dataset_for_table(table: str) -> str:
    if table not in DATASET_FOR_TABLE:
        raise ValueError(
            f"No collector writes '{table}'. Known tables: {', '.join(sorted(DATASET_FOR_TABLE))}"
        )
    return DATASET_FOR_TABLE[table]
