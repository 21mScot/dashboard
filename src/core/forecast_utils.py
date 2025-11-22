from __future__ import annotations

from datetime import date
from typing import List, Tuple

import pandas as pd

from src.core.btc_forecast_engine import forecast_to_dataframe


def build_halving_dates(
    next_halving: Tuple[int, int, int] | None,
    interval_years: int,
    last_month_date: date,
) -> List[date]:
    """
    Generate halving dates from the next known halving tuple until the last month date.

    Args:
        next_halving: Tuple of (year, month, day) for the next halving, or None.
        interval_years: Interval between halvings in years (usually 4).
        last_month_date: The last month present in the forecast timeline.

    Returns:
        A list of date objects representing halving dates up to last_month_date.
    """
    if not next_halving or len(next_halving) != 3:
        return []

    halving_points: List[date] = []
    current = date(*next_halving)
    while current <= last_month_date:
        halving_points.append(current)
        current = date(current.year + interval_years, current.month, current.day)
    return halving_points


def compute_y_domain(series: pd.Series, pad_pct: float) -> Tuple[float, float]:
    """
    Compute a simple (0, max*(1+pad)) y-domain for charting.
    """
    pad = max(0.0, pad_pct or 0.0)
    max_val = series.max() if not series.empty else 0.0
    upper = float(max_val * (1 + pad)) if max_val > 0 else 1.0
    return (0.0, upper)


def build_unified_monthly_table(monthly_df, fiat_df, usd_to_gbp: float):
    """
    Merge BTC and fiat monthly data and compute BTC price in GBP.
    Expects both dataframes to have a Month column.
    """
    if monthly_df is None or fiat_df is None or monthly_df.empty or fiat_df.empty:
        return monthly_df

    unified_df = monthly_df[["Month", "BTC mined"]].copy()
    unified_df = unified_df.merge(
        fiat_df[["Month", "Revenue (GBP)", "BTC price (USD)"]],
        on="Month",
        how="left",
    )
    if "BTC price (USD)" in unified_df.columns:
        unified_df["BTC price (GBP)"] = unified_df["BTC price (USD)"] * usd_to_gbp
    return unified_df[["Month", "BTC mined", "Revenue (GBP)", "BTC price (GBP)"]]


def prepare_btc_display(
    monthly_rows,
    pad_pct: float,
    next_halving: Tuple[int, int, int] | None,
    interval_years: int,
):
    """
    From raw monthly rows, build a DataFrame with Month parsed, y-domain,
    and halving dates.
    """
    monthly_df = forecast_to_dataframe(monthly_rows)
    if monthly_df.empty:
        return monthly_df, (0.0, 1.0), []
    monthly_df["Month"] = pd.to_datetime(monthly_df["Month"])
    y_domain = compute_y_domain(monthly_df["BTC mined"], pad_pct)
    halving_dates = build_halving_dates(
        next_halving, interval_years, monthly_df["Month"].max().date()
    )
    return monthly_df, y_domain, halving_dates


def prepare_fiat_display(
    fiat_rows,
    pad_pct: float,
    next_halving: Tuple[int, int, int] | None,
    interval_years: int,
):
    """
    From raw fiat rows, build a DataFrame with Month parsed, y-domain,
    and halving dates.
    """
    fiat_df = pd.DataFrame(fiat_rows)
    if fiat_df.empty:
        return fiat_df, (0.0, 1.0), []

    # Normalize column names if coming from dataclasses (lowercase field names)
    if "Month" not in fiat_df.columns and "month" in fiat_df.columns:
        fiat_df["Month"] = fiat_df["month"]
    if "Revenue (GBP)" not in fiat_df.columns and "revenue_gbp" in fiat_df.columns:
        fiat_df["Revenue (GBP)"] = fiat_df["revenue_gbp"]
    if "BTC price (USD)" not in fiat_df.columns and "btc_price_usd" in fiat_df.columns:
        fiat_df["BTC price (USD)"] = fiat_df["btc_price_usd"]
    if "BTC mined" not in fiat_df.columns and "btc_mined" in fiat_df.columns:
        fiat_df["BTC mined"] = fiat_df["btc_mined"]

    # Ensure required columns exist
    if "Month" not in fiat_df.columns:
        fiat_df["Month"] = pd.NaT
    if "Revenue (GBP)" not in fiat_df.columns:
        fiat_df["Revenue (GBP)"] = 0.0

    if not pd.api.types.is_datetime64_any_dtype(fiat_df["Month"]):
        fiat_df["Month"] = pd.to_datetime(fiat_df["Month"])
    # Drop rows where Month is NaT to avoid comparison issues
    fiat_df = fiat_df.dropna(subset=["Month"])
    if fiat_df.empty:
        return fiat_df, (0.0, 1.0), []
    y_domain = compute_y_domain(fiat_df["Revenue (GBP)"], pad_pct)
    halving_dates = build_halving_dates(
        next_halving, interval_years, fiat_df["Month"].max().date()
    )
    return fiat_df, y_domain, halving_dates
