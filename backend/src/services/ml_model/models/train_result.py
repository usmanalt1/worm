from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from sklearn.base import BaseEstimator


@dataclass
class TrainResult:
    model: BaseEstimator
    predictions: pd.DataFrame
    metrics: Optional[dict[str, float]] = None
    season_record: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: list[str] = field(default_factory=list)
