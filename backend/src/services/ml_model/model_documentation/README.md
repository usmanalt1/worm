# How the prediction model works

One class, `ModelTraner`, does both jobs. The only difference is `mode`:

| | `backtest` | `live` |
|---|---|---|
| Question | how good is this model? | who wins tonight? |
| Season | a finished one | the one in progress |
| Trains on | every *other* season | every game played so far, this season included |
| Predicts | the chosen season's games, which already have results | the games with no result yet |
| Produces | accuracy / log loss / brier / auc | probabilities only, no metrics |
| Triggered by | the Predictions page, or the weekly Dagster job | the nightly Dagster job at 09:00 London |

Everything else — the data, the features, the Elo ratings — is identical. That is
deliberate: a backtest is only informative if it builds its features the same way the
live run does.

## What the model reads

`load_data` in [models/model_trainer.py](models/model_trainer.py) pulls nine tables through
Django. All but the last are `managed = False` views onto `nba_marts.*`; `teams_roster` is
the raw ingest table in `public.*`, written by the collector rather than by dbt:

| Table | Used for |
|---|---|
| `dim_games` | one row per game: who, when, final score. The spine. |
| `fct_team_stats` | team box scores, which become rolling form |
| `fct_player_stats` | player box scores, which become star counts |
| `dim_teams` | names for display |
| `mart_team_strength` | Elo rating and opponent-adjusted form per team per game |
| `mart_team_schedule_load` | travel, time zones, altitude and congestion per team-game |
| `mart_player_value` | each player's game score and its 20-game trailing average |
| `dim_rosters` | who was on a team between which dates, for *played* games |
| `teams_roster` | today's roster snapshot, for games not yet played |

The last four are filtered by the transformer that reads them rather than by
`_select_frames`, because each is keyed on `game_id` or resolved as-of a date.

`teams_roster` used to be keyed on `(team_id, player_id, season_id)`, so a traded player
gained a row rather than moving and both teams kept one. Migration `0026` re-keyed it on
`(player_id, season_id)` and deleted the 23 superseded rows, so one row per player per
season is now enforced by the database. `RosterValueTransformer._latest_snapshot_per_player`
still resolves each player to their newest `run_timestamp`: a no-op against the current
constraint, kept because it is the model that silently prints wrong numbers if the table
ever regresses.

A snapshot can still name a player who has since been released — they stay attributed to
the team they were last seen on. Measured on the 2026-27 snapshot, 3 of 240 top-8 rotation
slots came from a superseded snapshot, which is why no "latest full sweep" rule exists.

Note `dim_games` includes *scheduled* games with null scores. That is what makes live
mode possible: an unplayed game is a real row with `home_wl` null.

## From a game to a feature row

Six transformers run in order, each feeding the next
([models/model_trainer.py](models/model_trainer.py), `_build_regular_transformers`):

1. **`GamesTransformer`** — splits each game into two team rows, one home, one away.
   1230 games become 2460 team-games.
2. **`BoxscoreTransformer`** — attaches each team's season-to-date averages, blended with
   last season's as a baseline while this season is thin, then folds the two team rows
   back into one row per game of home-minus-away differences.
3. **`PlayersTransformer`** — adds star-player counts per side.
4. **`TeamStrengthTransformer`** — adds the two Elo features.
5. **`ScheduleLoadTransformer`** — adds travel and congestion.
6. **`RosterValueTransformer`** — adds the minutes-weighted value of each rotation.

Only the last transformer's frame survives: `build()` loops the list and keeps the final
`model_df`, so each one must carry its predecessor's columns through.

The playoffs run a different chain (`_build_playoff_transformers`): steps 1 and 2 are
replaced by **`PlayoffBoxscoreTransformer`**, which calls `GamesTransformer` itself and
uses *this* season's regular season as the baseline instead of last postseason, then
steps 3–5 follow. There is no roster-value step in the playoffs.

The model only ever sees columns named `diff_*` (plus `round` and `game_in_series` in the
playoffs). Every feature is a difference: home minus away.

**Nothing in a row may postdate the game.** Season-to-date averages use `shift(1)`, Elo
uses the rating *before* the game, and form is also shifted. Without that, the model
would train on the answer.

## The feature set

`build()` picks the columns, not a hand-written list:

```python
diff_cols    = [c for c in model_df.columns if c.startswith("diff_")]
context_cols = [c for c in ("round", "game_in_series") if c in model_df.columns]
feature_cols = diff_cols + context_cols
```

So a transformer that emits a `diff_*` column has added a feature, and nothing else needs
changing. The flip side is that a stray `diff_*` column becomes a feature by accident.

**Backtest and live use the same features.** The list below is the whole input in both
modes — `mode` changes only which rows train and which get predicted, never which columns
are read. That is the point: a backtest that measured a richer feature set than the live
run would be measuring a model that never ships.

### Regular season and preseason — 26 features

Every feature is home minus away. `x` below means the per-team value before the
subtraction. Worked examples with real numbers for the three awkward ones are in
[FEATURES.md](FEATURES.md).

| # | Feature | How `x` is worked out | From |
|---|---|---|---|
| 1–13 | `diff_pre_fg_pct` `fg3_pct` `ft_pct` `oreb` `dreb` `reb` `ast` `stl` `blk` `tov` `pts` `plus_minus` `win_pct` | `(n * this_season + 10 * last_season) / (n + 10)`, where `n` = games played this season. [Worked](FEATURES.md#the-season-to-date-blend--features-1-to-13) | `BoxscoreTransformer` |
| 14 | `diff_days_rest` | days since the team's previous game | " |
| 15 | `diff_b2b` | `1` if `days_rest <= 1` | " |
| 16–18 | `diff_top5` `diff_top10` `diff_top20` | count of the team's players ranked top 5/10/20 in the league on points per game | `PlayersTransformer` |
| 19 | `diff_team_elo` | `elo_pre`: 1500, then per game `± 20(\|margin\|+3)^0.8 / (7.5 + 0.006\|edge\|) * (won - expected)`. [Worked](FEATURES.md#elo--features-19-and-20) | `TeamStrengthTransformer` |
| 20 | `diff_adj_margin` | mean of `margin + (opponent_elo - 1500) / 28.4` over the last 10 games | " |
| 21 | `diff_travel_km` | great-circle km from the previous venue | `ScheduleLoadTransformer` |
| 22 | `diff_tz_delta` | time zones crossed to get here | " |
| 23 | `diff_altitude_gain` | metres of altitude gained from the previous venue | " |
| 24 | `diff_games_prev_7d` | games played in the previous 7 days | " |
| 25 | `diff_road_trip_game` | how deep into a road trip this game is | " |
| 26 | `diff_roster_value` | `sum(value_pre * minutes_pre)` over the top 8 by `minutes_pre`, `/ 240`. [Worked](FEATURES.md#roster-value--feature-26) | `RosterValueTransformer` |

The numbering is only so the rest of this document can refer to a feature by one; the
actual column order is whatever the transformers append in, which matters to nothing.

Two things to hold onto. **1–13 are mostly last season until a team has played a while** —
at `n = 0` the weight on this season is exactly zero, so an opening-night row is last
season's team outright. **14, 15 and 21–25 are known months in advance**, because they come
off the schedule rather than off any box score.

### Playoffs — 30 features

The 10 features from `PlayersTransformer`, `TeamStrengthTransformer` and
`ScheduleLoadTransformer` (16–25 above) carry over unchanged. `diff_roster_value` does
**not** — the playoff chain omits that transformer. `PlayoffBoxscoreTransformer` supplies
the rest:

| Feature | Meaning |
|---|---|
| `diff_pre_*` (13 cols) | the same 13 form columns, but postseason-to-date, blended against *this* season's regular-season average with `SHRINKAGE_GAMES = 4` |
| `diff_days_rest`, `diff_b2b` | as above |
| `diff_series_wins_so_far` | wins in this series before this game — the series score |
| `diff_playoff_history_win_pct` | playoff win rate across *earlier* postseasons, league average where there is none |
| `diff_has_playoff_history` | whether that number is real or the league-average fill |
| `round`, `game_in_series` | read off the `game_id` — shared context, so **not** differenced |

`round` and `game_in_series` are the only two features that are not a home-minus-away
difference, which is why `build()` names them explicitly.

### How the same feature resolves for a game with no result yet

This is the part that actually differs between a backtest and a live run, and it differs
by *row*, not by mode. A backtest's rows are all played, so it only ever takes the left
column. A live run trains on played rows and predicts unplayed ones, so its prediction
rows take the right column:

| Feature group | Played game | No result yet |
|---|---|---|
| rest + schedule load (14, 15, 21–25) | from `dim_games` and `mart_team_schedule_load` | **identical** — the schedule is known in advance, so these need no special handling |
| form, 1–13 | expanding mean of the team's prior games, `shift(1)` | the same mean, frozen at the last played game |
| stars, 16–18 | that game's own star count | `pre_top{k}`, the season-to-date average count |
| Elo and form, 19–20 | own `elo_pre` / `form_adj_margin` | last rated game's `elo_post` / `form_adj_margin_post` |
| roster value, 26 | roster window from `dim_rosters` | today's `teams_roster` snapshot |

Two consequences worth holding onto:

**Every future game shares one snapshot per team.** Unplayed games contribute nothing to
the expanding mean (pandas skips the nulls), so a game in April reads the same form
numbers as tomorrow's. Elo behaves the same way, for the different reason described
below. What does keep moving is the shrinkage weight — `games_so_far` grows with the
schedule — so a later future game leans a little further off those same numbers and a
little less on last season.

**`diff_roster_value` is the one feature that reacts to a transaction.** Everything else
is derived from games played, so a team that signs a star carries no trace of it until
they take the court. `RosterValueTransformer` reads `teams_roster` for unplayed games
precisely to close that gap, and values each player off `mart_player_value`, whose
20-game window deliberately crosses seasons so a player arrives already rated.

### Features deliberately *not* in the list

- **Injuries and availability.** The feed only starts 2026-10-18, which is not enough
  snapshots to build a feature from yet. `diff_roster_value` is the nearest thing: it
  knows who is *on* the roster, not who is fit to play.
- **Who actually suited up.** `RosterValueTransformer` uses roster windows rather than box
  scores on purpose — the players who appeared in a game encode that night's injuries and
  rest, which no live prediction can know.
- **Home advantage.** Not a column. It is implicit: every feature is home-minus-away, so
  the intercept absorbs it. Elo applies its own `HOME_ADVANTAGE` internally when rating a
  game, but that never reaches the model as a feature.
- **Odds, lines, or anything market-derived.** Nothing in the pipeline reads them.

## Elo and form

Built by [../ratings/team_strength_service.py](../ratings/team_strength_service.py) into
`mart_team_strength`. Two measures per team per game, each stored twice — as it stood
*before* the game, and as it stood once that game was counted:

- **`elo_pre`** / **`elo_post`** — the team's rating entering and leaving the game. Starts
  at 1500. A result moves it by how far it beat what the rating predicted, so beating a
  strong team is worth more than beating a weak one. A rating of +400 over an opponent
  means 10:1 odds.
- **`form_adj_margin`** / **`form_adj_margin_post`** — mean margin over the last 10 games
  of this season, with each margin credited for how good that opponent was at the time.
  The `_post` column includes the current game, the other does not.

A game may only ever read its own `_pre` columns — that is what keeps a result out of the
features that predict it. The `_post` pair exists for a *later* game to inherit, which is
how live mode works (below).

The model uses the differences:

```
diff_team_elo   = elo_pre(home)         - elo_pre(away)
diff_adj_margin = form_adj_margin(home) - form_adj_margin(away)
```

How a rating gets from 1500 to where it is — the update formula, the four constants, and
three real games replayed — is in
[FEATURES.md](FEATURES.md#where-a-rating-actually-comes-from).

### What the model finally sees

Miami vs Atlanta, 12 April 2026 (`game_id` 0022501189):

| | `elo_pre` | `form_adj_margin` |
|---|---|---|
| MIA (home) | 1501.9 | -5.74 |
| ATL (away) | 1602.2 | +14.45 |

```
diff_team_elo   = 1501.9 - 1602.2  = -100.3
diff_adj_margin =  -5.74 - 14.45   =  -20.19
```

Both strongly negative: the home team was the clear underdog on rating and on recent
form. Elo alone, including the 56-point home advantage, gave Miami about a 44% chance.
Miami won 143-117. Pre-game features are honest, not clairvoyant — the point of a
backtest is to measure how often they are right across a whole season, not per game.

### Season boundaries and warm-up

Two edges worth knowing, because both bit us:

- **Elo carries over, damped**, by `CARRYOVER = 0.75` — worked through with real numbers
  worked through with real numbers in [FEATURES.md](FEATURES.md#what-a-new-season-starts-from).
- **Form needs 3 games** (`MIN_FORM_GAMES`). Each team's first 3 games of a season have
  no form value at all. `TeamStrengthTransformer` fills the missing *difference* with 0
  — "no form edge either way" — rather than dropping the game. It used to drop it, which
  silently removed 48 games from every season's backtest and made the standings read 79
  games instead of 82.
- **Playoffs are rated, and continuously.** `_read_games` takes
  `season_type in ('regular', 'playoffs')`. Playoff games carry the same `season`
  string as the regular season, and `CARRYOVER` only fires when that string *changes*,
  so a rating runs straight on into the postseason with no damping and keeps moving
  round to round. The 2025-26 champion went 1652.5 entering round 1 to 1731.9 by the
  conference finals. Only the next regular season regresses it — from the
  post-playoff rating, which is the most recent evidence there is.

## Backtest: how the split works

Say you backtest 2025-26 regular season. `df_games` holds every regular-season game of
every season. Two flags decide each row's job:

- `is_predicted` — this game is in the season under test
- `is_played` — this game has a result

```python
train_df = model_df[~is_predicted & is_played]   # all other seasons
eval_df  = model_df[is_predicted & is_played]    # 2025-26, scored against reality
```

Real numbers from a 2025-26 run: 11,933 feature rows in total, 1,230 of them 2025-26, so
the model trains on roughly 10,700 games from 2017-18 through 2024-25 and is scored on
the 1,230 it has never seen. The season under test is held out entirely — that is what
makes the metric meaningful.

Those counts were measured before `ScheduleLoadTransformer` and `RosterValueTransformer`
joined the chain. The schedule-load step drops rows, so the current total is at or below
11,933 — read the `dropped N rows` log lines for the real figure rather than trusting this
paragraph.

`train()` then reports two lines: the model, and a naive "always pick the home team"
baseline. If the model cannot beat the baseline, it is not earning its keep.

The standings table in the UI (`season_record`) is the model's **predicted** record, not
the real one — wins counted from `predicted_winner`. If a team shows fewer than 82 games
there, games are being dropped somewhere in the transformer chain.

## Live: how the split works

Same code, one flag flipped:

```python
train_df = model_df[is_played]                   # everything played, this season too
eval_df  = model_df[is_predicted & ~is_played]   # every game still to come
y_eval   = None                                  # nothing to score against
```

Two things surprise people:

**It predicts the whole rest of the season, not tonight's slate.** `eval_df` is every
unplayed game of that season type. The 2026-27 regular season currently has 1,200 stored
predictions, running from 20 October 2026 to 11 April 2027.

**Every future game shares one rating snapshot per team.** `mart_team_strength` only has
rows for *completed* games, so a game in April has no rating row of its own.
[features/team_strength_transformer.py](features/team_strength_transformer.py) resolves
each team-game in one of two ways, and the distinction is the whole ballgame:

| the game is | it reads | why |
|---|---|---|
| rated (played) | its own `elo_pre` / `form_adj_margin` | pre-game by construction, so no leakage |
| not rated (being predicted) | the last rated game's `elo_post` / `form_adj_margin_post` | the team's strength *now*, last result included |

Reading `elo_pre` for an unrated game would discard the team's most recent result and lag
by a full rating move — 8.45 points on average, up to 41.7. That is why the mart publishes
both halves of each pair.

Two more rules on the inherited path:

- If the last rated game is in an **earlier season**, the inherited Elo is regressed
  through `carry_into_new_season` first, so opening night uses 1575 for a 1600 team rather
  than 1600.
- Form is a within-season window, so it is **blanked** across a season boundary rather
  than inherited. `_merge_differentials` then fills the missing difference with 0, the
  same treatment the first three games of any season get.

So a game three weeks out is predicted with today's numbers, and tomorrow's pipeline
re-predicts it with tomorrow's.

That is the whole reason for the dependency in [../../../../dagster/assets.py](../../../../dagster/assets.py):

```python
def live_predictions(context, config, dbt_marts: dict, team_strength: dict):
```

`live_predictions` takes `team_strength` as an input it does not otherwise use, purely to
force the ratings to be rebuilt first. Predicting before the rebuild would score tonight's
games with ratings that ignore last night's results.

## Where it runs and where the output goes

The nightly job at 09:00 London (04:00 ET, after the last west-coast game):

```
latest_nba_data      NBA API      -> object storage
postgres_raw_tables  storage      -> Postgres public.*
dbt_marts            dbt build    -> nba_marts.*          (dim_games rebuilt here)
team_strength        Elo walk     -> nba_marts.mart_team_strength
live_predictions     ModelTraner  -> Redis + model_prediction_history
```

Live predictions land in two places:

- **Redis**, under `model_run_cache_key(...)`, TTL 26 hours — long enough that one run
  survives until the next replaces it, short enough that a failed pipeline serves nothing
  rather than yesterday's slate.
- **`model_prediction_history`** in Postgres, one row per game, upserted. An unplayed
  game's prediction is refreshed every night; once the game has a result,
  `persist_predictions` skips it, freezing what the model actually said before tip-off.
  Overwriting it later would be hindsight. That table is what grades the model over time
  and what `best_strategy` reads to pick which run the homepage opens on.

`best_strategy` ranks on Brier score, not hit rate — a confident correct call should beat
a hesitant one — and returns None until a season has `MIN_GRADED_GAMES` results. So for
roughly the first month the homepage stays on whichever strategy comes first in
`NightlyConfig.strategies` rather than switching. That is deliberate: the strategies sit
about a point of accuracy apart, which a few dozen games cannot resolve.

Backtests from the Predictions page cache per user, under
`user_run_cache_key(user_id, ...)` with a 24-hour TTL. **The page hydrates from that cache
on load**, so after changing anything upstream you must press Run again — a plain reload
shows the previous run.

There is also a weekly `backtest_pipeline` (Mondays 11:00, stopped by default, useful out
of season or after a model change). It selects `backtest_scorecard` alone, so it reuses
whatever marts and ratings the last nightly left behind rather than rebuilding them.

## Things that bite

- **Stale ratings.** `mart_team_strength` is rebuilt by a Python asset, not dbt. If you
  rebuild `dim_games` by hand, the ratings do not follow and the model keeps using the
  old ones. Re-materialise `team_strength`.
- **A dropped feature drops the whole game.** Every transformer decides for itself what a
  null means, and four of the five drop the row:

  | Transformer | Null feature becomes |
  |---|---|
  | `BoxscoreTransformer` | **drops** the row (no prior-game history at all) |
  | `PlayersTransformer` | **drops** the row, after falling back to `pre_top{k}` |
  | `TeamStrengthTransformer` | **drops** on missing `diff_team_elo`; fills `diff_adj_margin` with 0 |
  | `ScheduleLoadTransformer` | **drops** the row |
  | `RosterValueTransformer` | fills with 0 |

  Any new feature that can be null will quietly shrink the evaluated set unless you decide
  which of those two it is. Check the per-transformer `dropped N rows` log lines when a
  season's game count looks short — they name the culprit.
- **Star counts know who played.** For a played game `diff_top{k}` counts the rated
  players who actually appeared, so it carries that night's injuries and rest; for an
  unplayed game it falls back to the season-to-date average. A backtest therefore scores
  features slightly better-informed than the live run's, which flatters the metric by an
  amount nothing here measures. `RosterValueTransformer` avoids the same trap by reading
  roster windows instead of box scores; features 16–18 predate that decision.
- **Watch the warning list.** `_validate_season_completeness` checks for unplayed games
  and for teams with fewer games than their peers, and the result carries `warnings`
  through to the UI. A team short of 82 games means `dim_games` lost something upstream.
- **Preseason trains on regular-season games.** `TRAIN_SEASON_TYPE` maps preseason to
  regular, because preseason has no history of its own to learn from.
