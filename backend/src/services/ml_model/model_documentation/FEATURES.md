# Worked examples: how a feature's number is arrived at

Three features where the stored number is hard to trace back to its inputs. Every figure
below was read out of the live pipeline, not derived by hand, so if you change a constant
and these stop reproducing, that is the change doing something rather than rounding drift.

The feature reference itself is in [README.md](README.md#the-feature-set).

## Elo — features 19 and 20

### Where a rating actually comes from

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
untouched — see "Season boundaries and warm-up" in [README.md](README.md#season-boundaries-and-warm-up).

## The season-to-date blend — features 1 to 13

### The arithmetic

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

## Roster value — feature 26

### The arithmetic

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

