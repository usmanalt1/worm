"""Client for the third-party NBA injury feed.

The feed reports current status only, so the history has to be accumulated: one snapshot
per day, appended, which is what makes a past date reconstructable later.
"""

import logging
import time

import pandas as pd
import requests

from config.settings import settings

BASE_URL = "https://api.bigballsdata.com/v1"
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

logger = logging.getLogger(__name__)


class InjuryFeedService:
    def fetch_nba(self) -> pd.DataFrame:
        """Current status for every listed NBA player. One request covers the league."""
        if not settings.BIGBALLS_API_KEY:
            raise RuntimeError("BIGBALLS_API_KEY is unset, so the injury feed cannot be read")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(
                    f"{BASE_URL}/injuries",
                    params={"sport": "basketball"},
                    headers={"x-api-key": settings.BIGBALLS_API_KEY},
                    timeout=TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                return self._to_frame(response.json())
            except Exception as e:
                logger.warning(f"Injury feed attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(2 ** attempt)

    @staticmethod
    def _to_frame(payload: dict) -> pd.DataFrame:
        """The feed's own player ids are not NBA ids, so names are carried for matching."""
        rows = []
        for item in payload.get("data", {}).get("injuries", []):
            player = item.get("player") or {}
            team = player.get("team") or {}
            rows.append({
                "source_player_id": player.get("id"),
                "player_name": player.get("name"),
                "team_name": team.get("name"),
                "team_abbreviation": team.get("abbreviation"),
                "status": item.get("status"),
                "injury_type": item.get("injury_type"),
                "return_date": item.get("return_date"),
                "comment": item.get("comment"),
                "source_updated_at": item.get("updated_at"),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df = df.dropna(subset=["source_player_id"])
        df["return_date"] = pd.to_datetime(df["return_date"], errors="coerce").dt.date
        df["source_updated_at"] = pd.to_datetime(df["source_updated_at"], errors="coerce")

        return df
