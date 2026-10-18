from django.db import models


class SeasonRecord(models.Model):
    season_id = models.IntegerField(unique=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'season_record'


class TeamInfo(models.Model):
    # NBA's own team id; `id` is the surrogate pk and this table repeats it per season.
    team_id = models.IntegerField(null=True, blank=True, db_index=True)
    season_id = models.IntegerField()
    abbreviation = models.CharField(max_length=10)
    nickname = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    year_founded = models.IntegerField()
    full_name = models.CharField(max_length=100, null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'teams_info'
        constraints = [
            models.UniqueConstraint(fields=["season_id", "abbreviation"], name="teams_info_unique_season_abbr"),
        ]


class PlayerInfo(models.Model):
    # see TeamInfo.team_id
    player_id = models.IntegerField(null=True, blank=True, db_index=True)
    season_id = models.IntegerField()
    full_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_active = models.BooleanField()
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'players_info'
        constraints = [
            models.UniqueConstraint(fields=["season_id", "full_name"], name="players_info_unique_season_name"),
        ]


class TeamRoster(models.Model):
    team_id = models.IntegerField()
    player_id = models.IntegerField()
    season_id = models.IntegerField()
    player = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    position = models.CharField(max_length=20, null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'teams_roster'
        constraints = [
            models.UniqueConstraint(fields=["player_id", "season_id"], name="teams_roster_unique_player_season"),
        ]


class PlayerStats(models.Model):
    season_id = models.IntegerField()
    player_id = models.IntegerField()
    player_name = models.CharField(max_length=100)
    team_id = models.IntegerField()
    team_abbreviation = models.CharField(max_length=10)
    team_name = models.CharField(max_length=50)
    game_id = models.CharField(max_length=20)
    game_date = models.DateField(null=True, blank=True)
    matchup = models.CharField(max_length=50)
    wl = models.CharField(max_length=2, null=True, blank=True)
    min = models.FloatField()
    fgm = models.FloatField()
    fga = models.FloatField()
    fg_pct = models.FloatField()
    fg3m = models.FloatField()
    fg3a = models.FloatField()
    fg3_pct = models.FloatField()
    ftm = models.FloatField()
    fta = models.FloatField()
    ft_pct = models.FloatField()
    oreb = models.FloatField()
    dreb = models.FloatField()
    reb = models.FloatField()
    ast = models.FloatField()
    stl = models.FloatField()
    blk = models.FloatField()
    tov = models.FloatField()
    pf = models.FloatField()
    pts = models.FloatField()
    plus_minus = models.FloatField()
    fantasy_pts = models.FloatField(null=True, blank=True)
    video_available = models.IntegerField(null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'player_stats'
        constraints = [
            models.UniqueConstraint(fields=["game_id", "player_id", "season_id"], name="player_stats_unique_game_player_season"),
        ]


class TeamStats(models.Model):
    season_id = models.IntegerField()
    team_id = models.IntegerField()
    team_abbreviation = models.CharField(max_length=10)
    team_name = models.CharField(max_length=50)
    game_id = models.CharField(max_length=20)
    game_date = models.DateField(null=True, blank=True)
    matchup = models.CharField(max_length=50)
    wl = models.CharField(max_length=2, null=True, blank=True)
    min = models.FloatField()
    fgm = models.FloatField()
    fga = models.FloatField()
    fg_pct = models.FloatField()
    fg3m = models.FloatField()
    fg3a = models.FloatField()
    fg3_pct = models.FloatField()
    ftm = models.FloatField()
    fta = models.FloatField()
    ft_pct = models.FloatField()
    oreb = models.FloatField()
    dreb = models.FloatField()
    reb = models.FloatField()
    ast = models.FloatField()
    stl = models.FloatField()
    blk = models.FloatField()
    tov = models.FloatField()
    pf = models.FloatField()
    pts = models.FloatField()
    plus_minus = models.FloatField()
    video_available = models.IntegerField(null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'team_stats'
        constraints = [
            models.UniqueConstraint(fields=["game_id", "team_id", "season_id"], name="team_stats_unique_game_team_season"),
        ]


class TeamMatchups(models.Model):
    season_id = models.IntegerField()
    team_id = models.IntegerField()
    team_abbreviation = models.CharField(max_length=10)
    team_name = models.CharField(max_length=50)
    game_id = models.CharField(max_length=20)
    game_date = models.DateField(null=True, blank=True)
    matchup = models.CharField(max_length=50)
    wl = models.CharField(max_length=2, null=True, blank=True)
    min = models.FloatField()
    pts = models.FloatField()
    fgm = models.FloatField()
    fga = models.FloatField()
    fg_pct = models.FloatField()
    fg3m = models.FloatField()
    fg3a = models.FloatField()
    fg3_pct = models.FloatField()
    ftm = models.FloatField()
    fta = models.FloatField()
    ft_pct = models.FloatField()
    oreb = models.FloatField()
    dreb = models.FloatField()
    reb = models.FloatField()
    ast = models.FloatField()
    stl = models.FloatField()
    blk = models.FloatField()
    tov = models.FloatField()
    pf = models.FloatField()
    plus_minus = models.FloatField()
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'team_matchups'
        constraints = [
            models.UniqueConstraint(fields=["season_id", "team_id", "game_date"], name="team_matchups_unique_season_team_date"),
        ]


class PlayerAwards(models.Model):
    player_id = models.IntegerField()
    first_name = models.TextField(null=True, blank=True)
    last_name = models.TextField(null=True, blank=True)
    team = models.TextField(null=True, blank=True)
    # DESCRIPTION, not TYPE, distinguishes award types - TYPE is always "Award".
    description = models.TextField()
    all_nba_team_number = models.TextField(null=True, blank=True)
    season = models.TextField(null=True, blank=True)
    month = models.TextField(null=True, blank=True)
    week = models.TextField(null=True, blank=True)
    conference = models.TextField(null=True, blank=True)
    subtype1 = models.TextField(null=True, blank=True)
    subtype2 = models.TextField(null=True, blank=True)
    subtype3 = models.TextField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'player_awards'
        constraints = [
            models.UniqueConstraint(
                fields=["player_id", "season", "description", "all_nba_team_number", "month", "week"],
                name="player_awards_unique_player_season_desc_month_week",
            ),
        ]


class PlayerInjury(models.Model):
    # One row per listed player per day, appended rather than replaced, so a status can be
    # reconstructed as of a past date. source_player_id is the feed's id, not an NBA one.
    source_player_id = models.CharField(max_length=64)
    player_name = models.CharField(max_length=100)
    team_name = models.CharField(max_length=100, null=True, blank=True)
    team_abbreviation = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=40, null=True, blank=True)
    injury_type = models.CharField(max_length=100, null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    collected_date = models.DateField()
    # Carried by the storage partition, as on every other raw table.
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'player_injuries'
        constraints = [
            models.UniqueConstraint(
                fields=["source_player_id", "collected_date"],
                name="player_injuries_unique_player_day",
            ),
        ]


class DraftHistory(models.Model):
    # One row per drafted player. A pick is immutable, so this is reference data rather
    # than a per-season snapshot; draft_year is the draft, season the one it fed.
    player_id = models.IntegerField()
    player_name = models.CharField(max_length=100, null=True, blank=True)
    draft_year = models.IntegerField()
    season = models.CharField(max_length=20, null=True, blank=True)
    round_number = models.IntegerField(null=True, blank=True)
    round_pick = models.IntegerField(null=True, blank=True)
    overall_pick = models.IntegerField(null=True, blank=True)
    draft_type = models.CharField(max_length=50, null=True, blank=True)
    team_id = models.IntegerField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'draft_history'
        constraints = [
            models.UniqueConstraint(fields=["player_id"], name="draft_history_unique_player_id"),
        ]


class GameSchedule(models.Model):
    # Pulled ahead of tip-off, so unlike TeamStats this has rows for unplayed games.
    # game_status: 1=Scheduled, 2=Live, 3=Final.
    season_id = models.IntegerField()
    season = models.CharField(max_length=20, null=True, blank=True)
    game_id = models.CharField(max_length=20)
    game_date = models.DateField(null=True, blank=True)
    home_team_id = models.IntegerField()
    away_team_id = models.IntegerField()
    game_status = models.IntegerField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'game_schedule'
        constraints = [
            models.UniqueConstraint(fields=["game_id"], name="game_schedule_unique_game_id"),
        ]


# Mart models (dbt-managed, read-only)

class DimPlayers(models.Model):
    player_id = models.IntegerField(primary_key=True)
    season_id = models.CharField(max_length=20)
    player_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    position = models.CharField(max_length=20, null=True, blank=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."dim_players"'


class DimGames(models.Model):
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField(null=True, blank=True)
    season_id = models.IntegerField()
    season = models.CharField(max_length=20, null=True, blank=True)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    home_team_id = models.IntegerField()
    home_team_abbreviation = models.CharField(max_length=10)
    home_team_name = models.CharField(max_length=50)
    home_pts = models.FloatField(null=True, blank=True)
    home_wl = models.CharField(max_length=2, null=True, blank=True)
    away_team_id = models.IntegerField()
    away_team_abbreviation = models.CharField(max_length=10)
    away_team_name = models.CharField(max_length=50)
    away_pts = models.FloatField(null=True, blank=True)
    away_wl = models.CharField(max_length=2, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."dim_games"'


class DimTeams(models.Model):
    team_id = models.IntegerField(primary_key=True)
    season_id = models.IntegerField()
    team_name = models.CharField(max_length=50)
    team_abbreviation = models.CharField(max_length=10)
    nickname = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    year_founded = models.IntegerField(null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)
    display_hex = models.CharField(max_length=7, null=True, blank=True)
    alt_display_hex = models.CharField(max_length=7, null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."dim_teams"'

class DimRosters(models.Model):
    player_id = models.IntegerField(primary_key=True)
    player_name = models.CharField(max_length=100)
    team_id = models.CharField(max_length=20)
    team_abbreviation = models.CharField(max_length=10)
    season_id = models.CharField(max_length=20)
    season = models.CharField(max_length=20)
    first_game_with_team = models.DateField(null=True, blank=True)
    last_game_with_team = models.DateField(null=True, blank=True)
    was_traded = models.BooleanField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."dim_rosters"'


class DimSeasons(models.Model):
    season_id = models.IntegerField(primary_key=True)
    season_name = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."dim_seasons"'


class FctPlayerStats(models.Model):
    season_id = models.CharField(max_length=20)
    # Denormalised in dbt: dim_players only covers the latest season, so the FK
    # inner-joins away every earlier player.
    player_name = models.CharField(max_length=100, null=True, blank=True)
    player = models.ForeignKey(
        DimPlayers,
        on_delete=models.DO_NOTHING,
        db_column='player_id',
        db_constraint=False,
    )
    team_id = models.IntegerField()
    game_id = models.CharField(max_length=20, primary_key=True)
    wl = models.CharField(max_length=2, null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    fgm = models.FloatField(null=True, blank=True)
    fga = models.FloatField(null=True, blank=True)
    fg_pct = models.FloatField(null=True, blank=True)
    fg3m = models.FloatField(null=True, blank=True)
    fg3a = models.FloatField(null=True, blank=True)
    fg3_pct = models.FloatField(null=True, blank=True)
    ftm = models.FloatField(null=True, blank=True)
    fta = models.FloatField(null=True, blank=True)
    ft_pct = models.FloatField(null=True, blank=True)
    oreb = models.FloatField(null=True, blank=True)
    dreb = models.FloatField(null=True, blank=True)
    reb = models.FloatField(null=True, blank=True)
    ast = models.FloatField(null=True, blank=True)
    stl = models.FloatField(null=True, blank=True)
    blk = models.FloatField(null=True, blank=True)
    tov = models.FloatField(null=True, blank=True)
    pf = models.FloatField(null=True, blank=True)
    pts = models.FloatField(null=True, blank=True)
    plus_minus = models.FloatField(null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."fct_player_stats"'


class FctTeamStats(models.Model):
    season_id = models.IntegerField()
    team_id = models.IntegerField()
    game_id = models.CharField(max_length=20, primary_key=True)
    wl = models.CharField(max_length=2, null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    fgm = models.FloatField(null=True, blank=True)
    fga = models.FloatField(null=True, blank=True)
    fg_pct = models.FloatField(null=True, blank=True)
    fg3m = models.FloatField(null=True, blank=True)
    fg3a = models.FloatField(null=True, blank=True)
    fg3_pct = models.FloatField(null=True, blank=True)
    ftm = models.FloatField(null=True, blank=True)
    fta = models.FloatField(null=True, blank=True)
    ft_pct = models.FloatField(null=True, blank=True)
    oreb = models.FloatField(null=True, blank=True)
    dreb = models.FloatField(null=True, blank=True)
    reb = models.FloatField(null=True, blank=True)
    ast = models.FloatField(null=True, blank=True)
    stl = models.FloatField(null=True, blank=True)
    blk = models.FloatField(null=True, blank=True)
    tov = models.FloatField(null=True, blank=True)
    pf = models.FloatField(null=True, blank=True)
    pts = models.FloatField(null=True, blank=True)
    plus_minus = models.FloatField(null=True, blank=True)
    season = models.CharField(max_length=20, null=True, blank=True)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."fct_team_stats"'


class MlModels(models.Model):
    model_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'ml_models'

# Advanced season stats: raw (Django-managed)
# The *_RANK and sp_work_* columns are dropped: derivable from the rest.

class AdvancedPlayerSeasonStats(models.Model):
    season_id = models.CharField(max_length=20)
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20)
    player_id = models.BigIntegerField()
    player_name = models.CharField(max_length=100, null=True, blank=True)
    nickname = models.CharField(max_length=100, null=True, blank=True)
    team_id = models.BigIntegerField(null=True, blank=True)
    team_abbreviation = models.CharField(max_length=10, null=True, blank=True)
    age = models.FloatField(null=True, blank=True)
    gp = models.IntegerField(null=True, blank=True)
    w = models.IntegerField(null=True, blank=True)
    l = models.IntegerField(null=True, blank=True)
    w_pct = models.FloatField(null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    off_rating = models.FloatField(null=True, blank=True)
    def_rating = models.FloatField(null=True, blank=True)
    net_rating = models.FloatField(null=True, blank=True)
    ast_pct = models.FloatField(null=True, blank=True)
    ast_to = models.FloatField(null=True, blank=True)
    ast_ratio = models.FloatField(null=True, blank=True)
    oreb_pct = models.FloatField(null=True, blank=True)
    dreb_pct = models.FloatField(null=True, blank=True)
    reb_pct = models.FloatField(null=True, blank=True)
    tm_tov_pct = models.FloatField(null=True, blank=True)
    efg_pct = models.FloatField(null=True, blank=True)
    ts_pct = models.FloatField(null=True, blank=True)
    usg_pct = models.FloatField(null=True, blank=True)
    pace = models.FloatField(null=True, blank=True)
    pace_per40 = models.FloatField(null=True, blank=True)
    poss = models.FloatField(null=True, blank=True)
    pie = models.FloatField(null=True, blank=True)
    fgm = models.FloatField(null=True, blank=True)
    fga = models.FloatField(null=True, blank=True)
    fg_pct = models.FloatField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'advanced_player_season_stats'
        constraints = [
            models.UniqueConstraint(
                fields=["season", "season_type", "player_id"],
                name="adv_player_season_unique",
            ),
        ]


class AdvancedTeamSeasonStats(models.Model):
    season_id = models.CharField(max_length=20)
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20)
    team_id = models.BigIntegerField()
    team_name = models.CharField(max_length=50, null=True, blank=True)
    gp = models.IntegerField(null=True, blank=True)
    w = models.IntegerField(null=True, blank=True)
    l = models.IntegerField(null=True, blank=True)
    w_pct = models.FloatField(null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    off_rating = models.FloatField(null=True, blank=True)
    def_rating = models.FloatField(null=True, blank=True)
    net_rating = models.FloatField(null=True, blank=True)
    ast_pct = models.FloatField(null=True, blank=True)
    ast_to = models.FloatField(null=True, blank=True)
    ast_ratio = models.FloatField(null=True, blank=True)
    oreb_pct = models.FloatField(null=True, blank=True)
    dreb_pct = models.FloatField(null=True, blank=True)
    reb_pct = models.FloatField(null=True, blank=True)
    tm_tov_pct = models.FloatField(null=True, blank=True)
    efg_pct = models.FloatField(null=True, blank=True)
    ts_pct = models.FloatField(null=True, blank=True)
    pace = models.FloatField(null=True, blank=True)
    pace_per40 = models.FloatField(null=True, blank=True)
    poss = models.FloatField(null=True, blank=True)
    pie = models.FloatField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'advanced_team_season_stats'
        constraints = [
            models.UniqueConstraint(
                fields=["season", "season_type", "team_id"],
                name="adv_team_season_unique",
            ),
        ]


# Advanced season stats: marts (dbt-managed, read-only)

class FctAdvancedPlayerSeasonStats(models.Model):
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20)
    player_id = models.BigIntegerField(primary_key=True)
    player_name = models.CharField(max_length=100, null=True, blank=True)
    team_id = models.BigIntegerField(null=True, blank=True)
    team_abbreviation = models.CharField(max_length=10, null=True, blank=True)
    age = models.FloatField(null=True, blank=True)
    games_played = models.IntegerField(null=True, blank=True)
    wins = models.IntegerField(null=True, blank=True)
    losses = models.IntegerField(null=True, blank=True)
    average_minutes = models.FloatField(null=True, blank=True)
    offensive_rating = models.FloatField(null=True, blank=True)
    defensive_rating = models.FloatField(null=True, blank=True)
    net_rating = models.FloatField(null=True, blank=True)
    assist_percentage = models.FloatField(null=True, blank=True)
    assist_to_turnover = models.FloatField(null=True, blank=True)
    assist_ratio = models.FloatField(null=True, blank=True)
    offensive_rebound_percentage = models.FloatField(null=True, blank=True)
    defensive_rebound_percentage = models.FloatField(null=True, blank=True)
    rebound_percentage = models.FloatField(null=True, blank=True)
    turnover_percentage = models.FloatField(null=True, blank=True)
    effective_field_goal_percentage = models.FloatField(null=True, blank=True)
    true_shooting_percentage = models.FloatField(null=True, blank=True)
    usage_percentage = models.FloatField(null=True, blank=True)
    pace = models.FloatField(null=True, blank=True)
    possessions = models.FloatField(null=True, blank=True)
    pie = models.FloatField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."fct_advanced_player_season_stats"'


class FctAdvancedTeamSeasonStats(models.Model):
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20)
    team_id = models.BigIntegerField(primary_key=True)
    team_name = models.CharField(max_length=50, null=True, blank=True)
    games_played = models.IntegerField(null=True, blank=True)
    wins = models.IntegerField(null=True, blank=True)
    losses = models.IntegerField(null=True, blank=True)
    average_minutes = models.FloatField(null=True, blank=True)
    offensive_rating = models.FloatField(null=True, blank=True)
    defensive_rating = models.FloatField(null=True, blank=True)
    net_rating = models.FloatField(null=True, blank=True)
    assist_percentage = models.FloatField(null=True, blank=True)
    assist_to_turnover = models.FloatField(null=True, blank=True)
    assist_ratio = models.FloatField(null=True, blank=True)
    offensive_rebound_percentage = models.FloatField(null=True, blank=True)
    defensive_rebound_percentage = models.FloatField(null=True, blank=True)
    rebound_percentage = models.FloatField(null=True, blank=True)
    turnover_percentage = models.FloatField(null=True, blank=True)
    effective_field_goal_percentage = models.FloatField(null=True, blank=True)
    true_shooting_percentage = models.FloatField(null=True, blank=True)
    pace = models.FloatField(null=True, blank=True)
    possessions = models.FloatField(null=True, blank=True)
    pie = models.FloatField(null=True, blank=True)
    run_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."fct_advanced_team_season_stats"'


# One row per unplayed game per nightly run; the surviving row is the last before tip-off.

class ModelPredictionHistory(models.Model):
    strategy = models.CharField(max_length=50)
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20)
    game_id = models.CharField(max_length=20)
    game_date = models.DateField(null=True, blank=True)
    home_team_id = models.IntegerField(null=True, blank=True)
    home_team_name = models.CharField(max_length=50, null=True, blank=True)
    away_team_name = models.CharField(max_length=50, null=True, blank=True)
    home_win_probability = models.FloatField()
    predicted_home_win = models.BooleanField()
    predicted_at = models.DateTimeField()

    class Meta:
        db_table = "model_prediction_history"
        constraints = [
            models.UniqueConstraint(
                fields=["strategy", "season", "season_type", "game_id"],
                name="prediction_history_unique_strategy_season_game",
            ),
        ]
        indexes = [
            models.Index(fields=["strategy", "season", "season_type"], name="pred_hist_strategy_season_idx"),
        ]


class MartPlayerGameForm(models.Model):
    """form_* is the last 10 games, base_* everything earlier, delta_* the difference."""
    season_id = models.CharField(max_length=20)
    season = models.CharField(max_length=20, null=True, blank=True)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    player_id = models.IntegerField()
    player_name = models.CharField(max_length=100, null=True, blank=True)
    team_id = models.IntegerField()
    # Composite grain, so not actually unique; Django just needs a single pk.
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField(null=True, blank=True)
    game_number = models.IntegerField(null=True, blank=True)
    games_in_season = models.IntegerField(null=True, blank=True)
    is_latest = models.BooleanField(null=True, blank=True)
    pts = models.FloatField(null=True, blank=True)
    reb = models.FloatField(null=True, blank=True)
    ast = models.FloatField(null=True, blank=True)
    form_pts = models.FloatField(null=True, blank=True)
    form_reb = models.FloatField(null=True, blank=True)
    form_ast = models.FloatField(null=True, blank=True)
    form_ts_pct = models.FloatField(null=True, blank=True)
    base_pts = models.FloatField(null=True, blank=True)
    base_ts_pct = models.FloatField(null=True, blank=True)
    delta_pts = models.FloatField(null=True, blank=True)
    delta_ts_pct = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."mart_player_game_form"'


class MartTeamGameForm(models.Model):
    """Team equivalent of MartPlayerGameForm; win percentages are 0-100."""
    season_id = models.CharField(max_length=20)
    season = models.CharField(max_length=20, null=True, blank=True)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    team_id = models.IntegerField()
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField(null=True, blank=True)
    game_number = models.IntegerField(null=True, blank=True)
    games_in_season = models.IntegerField(null=True, blank=True)
    is_latest = models.BooleanField(null=True, blank=True)
    margin = models.FloatField(null=True, blank=True)
    win = models.IntegerField(null=True, blank=True)
    form_margin = models.FloatField(null=True, blank=True)
    form_win_pct = models.FloatField(null=True, blank=True)
    form_wins = models.IntegerField(null=True, blank=True)
    form_games = models.IntegerField(null=True, blank=True)
    base_margin = models.FloatField(null=True, blank=True)
    base_win_pct = models.FloatField(null=True, blank=True)
    delta_margin = models.FloatField(null=True, blank=True)
    delta_win_pct = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."mart_team_game_form"'


class MartTeamStrength(models.Model):
    """elo_pre is the rating going into the game, elo_post the one after it.

    A game may only read its own _pre columns; the _post pair is what a *later* game
    inherits. Regular season and playoffs, built by the team_strength Dagster asset
    rather than dbt.
    """
    season = models.CharField(max_length=20)
    # Composite grain, so not actually unique; Django just needs a single pk.
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField(null=True, blank=True)
    team_id = models.IntegerField()
    is_home = models.IntegerField(null=True, blank=True)
    elo_pre = models.FloatField(null=True, blank=True)
    elo_post = models.FloatField(null=True, blank=True)
    opponent_elo_pre = models.FloatField(null=True, blank=True)
    margin = models.FloatField(null=True, blank=True)
    adj_margin = models.FloatField(null=True, blank=True)
    form_adj_margin = models.FloatField(null=True, blank=True)
    form_adj_margin_post = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."mart_team_strength"'


class MartPlayerValue(models.Model):
    """Per player-game box-score value, and the average of their previous 20 games.

    value_pre crosses seasons on purpose, so a player carries a value into a new season
    before playing a game in it. Null on a player's very first game.
    """
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    player_id = models.IntegerField()
    team_id = models.IntegerField(null=True, blank=True)
    # Composite grain with player_id, so not actually unique; Django needs a single pk.
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField(null=True, blank=True)
    minutes = models.FloatField(null=True, blank=True)
    game_score = models.FloatField(null=True, blank=True)
    value_pre = models.FloatField(null=True, blank=True)
    minutes_pre = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."mart_player_value"'


class MartTeamScheduleLoad(models.Model):
    """Travel and schedule load per team-game.

    Measured against the team's previous venue, so 0 on its first game of a season.
    road_trip_game is 0 at home and n on the nth consecutive away game.
    """
    season = models.CharField(max_length=20)
    season_id = models.CharField(max_length=20, null=True, blank=True)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    # Composite grain with team_id, so not actually unique; Django needs a single pk.
    game_id = models.CharField(max_length=20, primary_key=True)
    game_date = models.DateField(null=True, blank=True)
    team_id = models.IntegerField()
    is_home = models.IntegerField(null=True, blank=True)
    venue_altitude_m = models.IntegerField(null=True, blank=True)
    road_trip_game = models.IntegerField(null=True, blank=True)
    games_prev_7d = models.IntegerField(null=True, blank=True)
    travel_km = models.FloatField(null=True, blank=True)
    tz_delta = models.IntegerField(null=True, blank=True)
    altitude_gain = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."mart_team_schedule_load"'


class MartPlayerVolatility(models.Model):
    """Game-to-game swing in a player's output per season, with the shrinkage moments.

    High volatility is boom-or-bust, not worse. Adjusted for the league's
    volatility-to-minutes slope, so it ranks temperament rather than bench role.
    Regular season only.
    """
    season = models.CharField(max_length=20)
    season_type = models.CharField(max_length=20, null=True, blank=True)
    # Composite grain with season, so not actually unique; Django needs a single pk.
    player_id = models.IntegerField(primary_key=True)
    games = models.IntegerField(null=True, blank=True)
    minutes_total = models.FloatField(null=True, blank=True)
    minutes_per_game = models.FloatField(null=True, blank=True)
    mean_per36 = models.FloatField(null=True, blank=True)
    volatility_raw = models.FloatField(null=True, blank=True)
    volatility_adj = models.FloatField(null=True, blank=True)
    volatility_se = models.FloatField(null=True, blank=True)
    volatility_shrunk = models.FloatField(null=True, blank=True)
    role_slope = models.FloatField(null=True, blank=True)
    league_mean = models.FloatField(null=True, blank=True)
    tau = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"nba_marts"."mart_player_volatility"'
