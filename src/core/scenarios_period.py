# src/core/scenarios_period.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class AnnualEconomicsRow:
    year_index: int
    btc_mined: float
    btc_price_fiat: float
    revenue_fiat: float
    electricity_cost_fiat: float
    other_opex_fiat: float
    total_opex_fiat: float
    ebitda_fiat: float
    ebitda_margin: float  # as a fraction, e.g. 0.92 for 92%


@dataclass
class ScenarioAnnualEconomics:
    """Container for multi-year economics for a single scenario."""

    name: str
    years: List[AnnualEconomicsRow]

    @property
    def total_btc(self) -> float:
        return sum(row.btc_mined for row in self.years)

    @property
    def total_revenue(self) -> float:
        return sum(row.revenue_fiat for row in self.years)

    @property
    def total_opex(self) -> float:
        return sum(row.total_opex_fiat for row in self.years)

    @property
    def avg_ebitda_margin(self) -> float:
        """Revenue-weighted average EBITDA margin."""
        total_rev = self.total_revenue
        if total_rev <= 0:
            return 0.0
        weighted = sum(row.ebitda_margin * row.revenue_fiat for row in self.years)
        return weighted / total_rev


def annual_economics_to_dataframe(econ: ScenarioAnnualEconomics) -> pd.DataFrame:
    """Convert annual economics into a tidy DataFrame for display."""
    records = []
    for row in econ.years:
        records.append(
            {
                "Year": row.year_index,
                "BTC mined": row.btc_mined,
                "BTC price": row.btc_price_fiat,
                "Revenue (£)": row.revenue_fiat,
                "Electricity cost (£)": row.electricity_cost_fiat,
                "Other OpEx (£)": row.other_opex_fiat,
                "Total OpEx (£)": row.total_opex_fiat,
                "EBITDA (£)": row.ebitda_fiat,
                "EBITDA margin (%)": row.ebitda_margin * 100.0,
            }
        )

    df = pd.DataFrame.from_records(records)
    return df
