"""Tuning constants for TeamStrengthService.

HOME_ADVANTAGE and ELO_PER_POINT are measured from dim_games rather than chosen; the
rest are conventional. Changing any of them re-denominates every rating, so treat an
edit as a deliberate rescale, not tuning.
"""

START = 1500.0
# A 400-point edge means 10:1 odds, which is what fixes the scale.
SCALE = 400.0
K = 20.0

# Measured: home teams win by 1.98 points on average, and one point of margin is worth
# 28.4 rating points. Prediction is insensitive to HOME_ADVANTAGE - 0 to 100 all score
# within 0.0002 log-loss, because the model relearns the home effect in its intercept.
# It matters only when the ratings themselves are shown to someone.
HOME_ADVANTAGE = 56.0
ELO_PER_POINT = 28.4

# Rosters change, so last season is evidence rather than a starting point.
CARRYOVER = 0.75

# FiveThirtyEight's NBA margin-of-victory multiplier: a bigger win moves a rating more
# with diminishing returns, and the damping grows with the edge so that favourites
# winning blowouts do not inflate.
MOV_OFFSET = 3.0
MOV_EXPONENT = 0.8
MOV_DAMPING = 7.5
MOV_DAMPING_PER_ELO = 0.006

FORM_GAMES = 10
MIN_FORM_GAMES = 3

TARGET_SCHEMA = "nba_marts"
TARGET_TABLE = "mart_team_strength"
GRAIN = ["season", "team_id", "game_id"]
WRITE_CHUNK_ROWS = 10_000
# Elo is zero-sum per game, so changes must cancel to within floating-point noise.
ZERO_SUM_TOLERANCE = 1e-6
