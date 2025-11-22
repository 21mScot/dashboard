from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class BTCForecastContext:
    monthly_rows: List[dict]
    monthly_df: pd.DataFrame
    fee_growth_pct: float
    difficulty_growth_pct: float


@dataclass
class FiatForecastContext:
    fiat_rows: List[dict]
    fiat_df: pd.DataFrame
    price_growth_pct: float
