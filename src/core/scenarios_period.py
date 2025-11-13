# src/core/scenarios_period.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class AnnualEconomicsRow:
    year_index: int  # 1, 2, 3, 4...
    btc_mined: float
    btc_price_fiat: float  # GBP (or USD) per BTC
    revenue_fiat: float
    electricity_cost_fiat: float
    other_opex_fiat: float
    total_opex_fiat: float
    ebitda_fiat: float
    ebitda_margin: float  # 0–1 float


@dataclass
class ScenarioAnnualEconomics:
    name: str  # e.g. "Scenario 1 – Base case"
    years: List[AnnualEconomicsRow]

    @property
    def total_btc(self) -> float:
        return sum(y.btc_mined for y in self.years)

    @property
    def total_revenue(self) -> float:
        return sum(y.revenue_fiat for y in self.years)

    @property
    def total_opex(self) -> float:
        return sum(y.total_opex_fiat for y in self.years)

    @property
    def total_ebitda(self) -> float:
        return sum(y.ebitda_fiat for y in self.years)

    @property
    def avg_ebitda_margin(self) -> float:
        revenue = self.total_revenue
        if revenue <= 0:
            return 0.0
        return self.total_ebitda / revenue


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

    return pd.DataFrame.from_records(records)
