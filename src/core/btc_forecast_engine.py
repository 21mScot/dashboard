# src/core/monthly_forecast.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd

from src.config import settings
from src.core.site_metrics import SiteMetrics


@dataclass
class MonthlyForecastRow:
    month: date
    subsidy_btc: float
    fee_btc_per_block: float
    total_reward_btc_per_block: float
    btc_mined: float


def _add_months(start: date, months: int) -> date:
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(
        start.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return date(year, month, day)


def _block_subsidy_for_month(
    start_subsidy: float, halving_date: date, current: date
) -> float:
    subsidy = start_subsidy
    interval_years = int(getattr(settings, "HALVING_INTERVAL_YEARS", 4))
    next_halving = halving_date
    while current >= next_halving:
        subsidy *= 0.5
        next_halving = date(
            next_halving.year + interval_years,
            next_halving.month,
            next_halving.day,
        )
    return subsidy


def _difficulty_multiplier(month_index: int) -> float:
    growth = getattr(settings, "DEFAULT_ANNUAL_DIFFICULTY_GROWTH_PCT", 0.0)
    if growth == 0:
        return 1.0
    return (1.0 + growth) ** (month_index / 12.0)


def build_monthly_forecast(
    site: SiteMetrics,
    start_date: date,
    project_years: int,
    fee_growth_pct_per_year: float,
    base_fee_btc_per_block: float | None = None,
    hashrate_growth_pct_per_year: float | None = None,
) -> List[MonthlyForecastRow]:
    """
    Build a month-by-month BTC forecast for the site, halving-aware with
    network hashrate growth mapped into difficulty.
    """
    if project_years <= 0 or site.site_btc_per_day <= 0:
        return []

    months = project_years * 12
    base_subsidy = float(settings.DEFAULT_BLOCK_SUBSIDY_BTC)
    halving_tuple = getattr(settings, "NEXT_HALVING_DATE", None)
    halving_date = (
        date(*halving_tuple)
        if halving_tuple and len(halving_tuple) == 3
        else date(start_date.year, start_date.month, start_date.day)
    )
    fee_growth = max(0.0, fee_growth_pct_per_year) / 100.0
    diff_growth = (
        max(0.0, hashrate_growth_pct_per_year) / 100.0
        if hashrate_growth_pct_per_year is not None
        else getattr(settings, "DEFAULT_ANNUAL_DIFFICULTY_GROWTH_PCT", 0.0)
    )
    base_fee = base_fee_btc_per_block or settings.DEFAULT_FEE_BTC_PER_BLOCK

    rows: List[MonthlyForecastRow] = []
    for idx in range(months):
        month_start = _add_months(start_date, idx)
        subsidy = _block_subsidy_for_month(base_subsidy, halving_date, month_start)
        # Override difficulty growth if provided
        if diff_growth == 0:
            diff_mult = 1.0
        else:
            diff_mult = (1.0 + diff_growth) ** (idx / 12.0)

        fee_per_block = base_fee * ((1.0 + fee_growth) ** (idx / 12.0))
        reward_factor = (
            (subsidy + fee_per_block) / base_subsidy if base_subsidy > 0 else 1.0
        )

        days_in_month = (_add_months(month_start, 1) - month_start).days
        btc_mined = site.site_btc_per_day * days_in_month * reward_factor / diff_mult

        rows.append(
            MonthlyForecastRow(
                month=month_start,
                subsidy_btc=subsidy,
                fee_btc_per_block=fee_per_block,
                total_reward_btc_per_block=subsidy + fee_per_block,
                btc_mined=btc_mined,
            )
        )

    return rows


def forecast_to_dataframe(rows: List[MonthlyForecastRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "Month": r.month,
                "BTC mined": r.btc_mined,
                "Block reward": r.total_reward_btc_per_block,
                "Block subsidy": r.subsidy_btc,
                "Block Tx Fees (BTC)": r.fee_btc_per_block,
            }
            for r in rows
        ]
    )


def annual_totals(rows: List[MonthlyForecastRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = forecast_to_dataframe(rows)
    df["Month"] = pd.to_datetime(df["Month"])
    df["Year"] = df["Month"].dt.year
    annual = df.groupby("Year", as_index=False)["BTC mined"].sum()
    annual["BTC mined"] = annual["BTC mined"].astype(float)
    return annual
