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

The numbers are only so the rest of this document can refer to a feature by one. The
actual column order is whatever order the transformers happen to append in, which matters
to nothing — `StandardScaler` and the estimator both work positionally on the same frame.

| # | Feature | From | Meaning (home minus away) |
|---|---|---|---|
| 1 | `diff_pre_fg_pct` | `BoxscoreTransformer` | season-to-date field-goal % |
| 2 | `diff_pre_fg3_pct` | " | three-point % |
| 3 | `diff_pre_ft_pct` | " | free-throw % |
| 4 | `diff_pre_oreb` | " | offensive rebounds per game |
| 5 | `diff_pre_dreb` | " | defensive rebounds per game |
| 6 | `diff_pre_reb` | " | total rebounds per game |
| 7 | `diff_pre_ast` | " | assists per game |
| 8 | `diff_pre_stl` | " | steals per game |
| 9 | `diff_pre_blk` | " | blocks per game |
| 10 | `diff_pre_tov` | " | turnovers per game |
| 11 | `diff_pre_pts` | " | points per game |
| 12 | `diff_pre_plus_minus` | " | plus/minus per game |
| 13 | `diff_pre_win_pct` | " | win rate so far |
| 14 | `diff_days_rest` | " | days since the team's previous game |
| 15 | `diff_b2b` | " | on the second night of a back-to-back |
| 16 | `diff_top5` | `PlayersTransformer` | count of top-5 scorers in the league |
| 17 | `diff_top10` | " | count of top-10 scorers |
| 18 | `diff_top20` | " | count of top-20 scorers |
| 19 | `diff_team_elo` | `TeamStrengthTransformer` | Elo rating entering the game |
| 20 | `diff_adj_margin` | " | opponent-adjusted margin over the last 10 games |
| 21 | `diff_travel_km` | `ScheduleLoadTransformer` | great-circle km from the previous venue |
| 22 | `diff_tz_delta` | " | time zones crossed to get here |
| 23 | `diff_altitude_gain` | " | metres of altitude gained from the previous venue |
| 24 | `diff_games_prev_7d` | " | games played in the previous 7 days |
| 25 | `diff_road_trip_game` | " | how deep into a road trip this game is |
| 26 | `diff_roster_value` | `RosterValueTransformer` | minutes-weighted value of the top-8 rotation |

Features 1–13 are each blended against last season's average while this season is thin
(`SHRINKAGE_GAMES = 10`), so a team's third game is read mostly off last season and its
fiftieth almost entirely off this one. 14 and 15 come off `game_date` arithmetic, not the
box score, so they are known for a game months away.

#### Worked example: the blend

```
pre_x = (games_so_far * this_season_x + 10 * prior_season_x) / (games_so_far + 10)
```

New York's third game of 2025-26 (away, 26 October, `game_id` 0022500108). They had scored
119 and 105 in the two games before it, and averaged 115.7805 across all 82 games of
2024-25:

```
games_so_far = 2
this_season  = (119 + 105) / 2 = 112.0
prior_season = 115.7805
pre_pts      = (2 * 112.0 + 10 * 115.7805) / (2 + 10) = 115.1504
```

`away_pre_pts` on that row is **115.1504**. Note how little the two actual games moved it:
they carry 2/12 of the weight against last season's 10/12. By game 50 the ratio is 50/60
and last season barely registers. The same arithmetic runs for all 13 columns, and
`PlayersTransformer` uses the same shape with `STAR_SHRINKAGE_GAMES = 10` for star counts.

Two consequences people trip over: at `games_so_far = 0` the weight on this season is
*exactly* zero, so every opening-night row is last season's team outright; and if a team
has no prior season at all (`prior_season_x` is null) the blend is skipped and the raw
this-season value is used, which is why a team's genuinely first games can be dropped
downstream rather than blended.

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

#### Worked example: roster value

```
roster_value = sum(value_pre * minutes_pre for the top 8 by minutes_pre) / 240
```

New York's rotation for the 2026-27 opener, each player's `value_pre` and `minutes_pre`
being their last known 20-game averages from `mart_player_value`:

| player | `value_pre` | `minutes_pre` | product |
|---|---|---|---|
| Jalen Brunson | 18.01 | 36.15 | 650.9 |
| OG Anunoby | 14.86 | 34.40 | 511.0 |
| Mikal Bridges | 8.75 | 30.95 | 270.8 |
| Josh Hart | 12.05 | 29.90 | 360.3 |
| Karl-Anthony Towns | 18.17 | 29.90 | 543.3 |
| Miles McBride | 8.64 | 25.85 | 223.3 |
| Landry Shamet | 5.82 | 24.30 | 141.4 |
| James Wiseman | 6.70 | 22.25 | 149.0 |
| | | **sum** | **2850.0** |

```
NYK roster_value = 2850.0 / 240 = 11.8751
PHI roster_value =                16.6275
diff_roster_value = 11.8751 - 16.6275 = -4.7524
```

So the model entered that game told the *away* roster was the stronger one by 4.75, while
`diff_team_elo` said the home side was 216.65 points better. The 240 is five players for
48 minutes — a whole team's game — which is what makes the number read on roughly the same
scale as a player's game score rather than as an arbitrary sum.

Ranking on `minutes_pre` rather than on value is deliberate: it asks who will actually play,
not who is best. A high-value player on 12 minutes a night should not count the same as a
starter.

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

### Worked example: where a rating actually comes from

Every rating in the mart is the result of replaying every game in order from a standing
start. Four constants do the work, all in
[../ratings/team_strength_constants.py](../ratings/team_strength_constants.py):

```
START  = 1500   every team's first ever rating
SCALE  = 400    a 400-point edge means 10:1 odds
K      = 20     the base size of one game's move
HOME_ADVANTAGE = 56
```

One game updates both teams in four steps ([`_accumulate`](../ratings/team_strength_service.py)):

```
edge     = home_elo - away_elo + HOME_ADVANTAGE
expected = 1 / (1 + 10 ** (-edge / 400))                     # what the rating predicted
move     = 20 * (|margin| + 3) ** 0.8 / (7.5 + 0.006 * |edge|)   # how much a result is worth
change   = move * (home_won - expected)
```

then `home_elo + change` and `away_elo - change`. The change is applied with opposite
signs, which is why Elo is zero-sum per game and why `grain_problems` refuses to publish a
set whose per-game changes do not cancel.

The three terms are each doing a separate job:

- **`expected`** makes the move depend on surprise, not on winning. Beating a team you
  were already expected to beat moves you very little.
- **`move`** grows with margin but with a 0.8 exponent, so a 40-point win is worth more
  than a 4-point win but nowhere near ten times more.
- **`0.006 * |edge|`** in the denominator damps the move further when the teams were
  already far apart, so a strong favourite blowing out a weak team cannot inflate.

#### Cleveland's first three games, 2017-18

The very first game in the data, so both teams genuinely start at 1500. CLE at home, won
by 3:

```
edge     = 1500 - 1500 + 56                     = 56.0
expected = 1 / (1 + 10 ** (-56 / 400))          = 0.5799
move     = 20 * (3 + 3) ** 0.8 / (7.5 + 0.336)  = 10.7018
change   = 10.7018 * (1 - 0.5799)               = +4.4958
```

CLE 1500 → **1504.4958**, Boston 1500 → **1495.5042**. Winning by 3 at home is worth 4.5
points, not 20, because the rating already had CLE at 58% and the margin was slim.

Game 2, CLE away against a team now rated 1510.0033, won by 19. The formula is always
written from the home team's side, so `margin` is −19 and the change lands on CLE with the
sign flipped:

```
edge     = 1510.0033 - 1504.4958 + 56 = 61.5075
expected = 0.5876
move     = 30.1333          # |margin| is 19 now, not 3
change   = 30.1333 * (0 - 0.5876) = -17.7064   applied to the home team
```

CLE (away) 1504.4958 → **1522.2022**. A 19-point road win against a slight favourite is
worth 17.7 points — nearly four times game 1, almost all of it from the margin term.

Game 3, CLE at home rated 1522.2022, **lost** by 21:

```
edge   = 1522.2022 - 1500.7616 + 56 = 77.4406
expected = 0.6096
move   = 31.9178
change = 31.9178 * (0 - 0.6096) = -19.4582
```

CLE → **1502.7440**, giving back almost everything. Losing by 21 at home as the favourite
is the most expensive thing in the model: wrong result, large margin, high expectation.

Those four figures — 1504.4958, 1522.2022, 1502.7440 and the 1495.5042 for Boston — are
exactly what `mart_team_strength` stores for those games. If you change a constant and the
walk no longer reproduces them, that is the change doing something, not a rounding drift.

#### What a new season starts from

A rating never resets to 1500 again. It regresses, once, on the team's first game of a new
season (`CARRYOVER = 0.75`):

```
new = 1500 + 0.75 * (old - 1500)
```

Real transitions out of 2017-18:

| | ended 2017-18 | opened 2018-19 |
|---|---|---|
| GSW | 1734.3308 | 1675.7481 |
| HOU | 1711.1974 | 1658.3980 |
| BOS | 1587.3527 | 1565.5145 |
| CLE | 1571.0110 | 1553.2583 |

A quarter of the distance from average is given back each summer, so a 1734 team opens at
1676 rather than 1500. The reasoning is in the constant's own comment: rosters change, so
last season is evidence, not a starting point. **This is the single number that decides how
much last season dominates opening night** — `diff_team_elo` is the largest coefficient in
the model, and on opening night it is almost entirely carried. If October predictions look
too confident, this is the lever, not a new feature.

Note the regression fires on a change of `season` *string*, so the playoffs inherit
untouched — see the third bullet below.

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
  under "What a new season starts from" above.
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
