# src/core/capex_config.py
from __future__ import annotations

from dataclasses import dataclass

from src.config import settings


@dataclass(frozen=True)
class CapexTaxConfig:
    """
    Configuration for how we treat CapEx and capital tax relief
    for the AD plant operator (client).
    """

    corporation_tax_rate: float
    first_year_allowance_pct: float
    miner_lifetime_years: int


def get_default_capex_tax_config() -> CapexTaxConfig:
    """
    Single place to pull the CapEx/tax assumptions for calculations.
    """

    return CapexTaxConfig(
        corporation_tax_rate=settings.CLIENT_CORPORATION_TAX_RATE,
        first_year_allowance_pct=settings.CLIENT_CAPEX_FIRST_YEAR_ALLOWANCE_PCT,
        miner_lifetime_years=settings.MINER_ACCOUNTING_LIFETIME_YEARS,
    )
