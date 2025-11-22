from __future__ import annotations

from datetime import date
from typing import List, Tuple


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
