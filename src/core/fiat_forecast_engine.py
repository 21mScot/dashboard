# src/core/fiat_forecast_engine.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List

import pandas as pd


@dataclass
class FiatForecastRow:
    month: date
    btc_mined: float
    btc_price_usd: float
    revenue_usd: float
    revenue_gbp: float


def _monthly_growth_factor(annual_pct: float) -> float:
    """Convert annual % growth to a monthly compounding factor."""
    return (1.0 + annual_pct / 100.0) ** (1.0 / 12.0)


def build_fiat_monthly_forecast(
    monthly_btc_rows: Iterable,
    start_price_usd: float,
    annual_price_growth_pct: float,
    usd_to_gbp: float,
) -> List[FiatForecastRow]:
    """
    Build a fiat forecast using BTC monthly production and a compounding BTC price path.
    """
    rows: List[FiatForecastRow] = []
    monthly_factor = _monthly_growth_factor(annual_price_growth_pct)

    for idx, btc_row in enumerate(monthly_btc_rows):
        # btc_row expected to have month and btc_mined attributes
        month = getattr(btc_row, "month", None) or getattr(btc_row, "Month", None)
        btc_mined = getattr(btc_row, "btc_mined", None) or getattr(
            btc_row, "BTC mined", None
        )
        if month is None or btc_mined is None:
            continue

        price_usd = start_price_usd * (monthly_factor**idx)
        revenue_usd = btc_mined * price_usd
        revenue_gbp = revenue_usd * usd_to_gbp

        rows.append(
            FiatForecastRow(
                month=month,
                btc_mined=btc_mined,
                btc_price_usd=price_usd,
                revenue_usd=revenue_usd,
                revenue_gbp=revenue_gbp,
            )
        )

    return rows


def fiat_forecast_to_dataframe(rows: List[FiatForecastRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        [
            {
                "Month": r.month,
                "BTC mined": r.btc_mined,
                "BTC price (USD)": r.btc_price_usd,
                "Revenue (GBP)": r.revenue_gbp,
            }
            for r in rows
        ]
    )
    # Reorder columns to desired output
    return df[["Month", "Revenue (GBP)", "BTC price (USD)", "BTC mined"]]
