
from nba_api.live.nba.endpoints.scoreboard import ScoreBoard
from nba_api.live.nba.endpoints.boxscore import BoxScore
from nba_api.live.nba.endpoints.playbyplay import PlayByPlay

class PollerService:
    def __init__(self):
        pass

    def check_status(self):
        
        return scoreboard.get_dict()
