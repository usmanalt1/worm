from services.data_collection.constants import Constants

# What build_nba_data() has always returned with no flags set.
CORE_TABLES = (
    Constants.SEASON_RECORD,
    Constants.TEAMS_INFO,
    Constants.PLAYERS_INFO,
    Constants.TEAM_STATS,
    Constants.PLAYER_STATS,
    Constants.TEAM_MATCHUPS,
)

NIGHTLY_TABLES = CORE_TABLES + (
    Constants.TEAMS_ROSTER,
    Constants.GAME_SCHEDULE,
    Constants.ADVANCED_PLAYER_SEASON_STATS,
    Constants.ADVANCED_TEAM_SEASON_STATS,
    Constants.PLAYER_INJURIES,
)

LOG_TABLES = (Constants.TEAM_STATS, Constants.PLAYER_STATS)

# team_matchups is excluded: 30 teams x 2 calls makes it the slowest table by far, and
# nothing in the marts needs it per historical season.
SEASON_BACKFILL_TABLES = LOG_TABLES + (
    Constants.ADVANCED_PLAYER_SEASON_STATS,
    Constants.ADVANCED_TEAM_SEASON_STATS,
)
