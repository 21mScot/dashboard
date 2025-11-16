# src/core/scenario_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.config import settings

ScenarioName = Literal["base", "best", "worst"]


@dataclass(frozen=True)
class ScenarioConfig:
    """
    Pure configuration for one scenario variant, before any calculations.

    All percentages here are expressed as fractions, e.g. +20% -> 0.20.
    """

    name: ScenarioName

    # Relative shocks vs the "base" assumptions
    price_pct: float
    difficulty_pct: float
    electricity_pct: float

    # Fraction of BTC revenue going to the client (AD operator).
    # Operator share is 1 - client_revenue_share.
    client_revenue_share: float


def build_default_scenarios(
    client_share_override: float | None = None,
) -> dict[ScenarioName, ScenarioConfig]:
    """
    Factory that builds the standard base / best / worst configs
    using the centralised constants from settings.py.

    UI and engine code should call this instead of hard-coding
    any of the percentage shocks or default revenue share.
    """

    client_share = (
        client_share_override
        if client_share_override is not None
        else settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE
    )

    return {
        "base": ScenarioConfig(
            name="base",
            price_pct=settings.SCENARIO_BASE_PRICE_PCT,
            difficulty_pct=settings.SCENARIO_BASE_DIFFICULTY_PCT,
            electricity_pct=settings.SCENARIO_BASE_ELECTRICITY_PCT,
            client_revenue_share=client_share,
        ),
        "best": ScenarioConfig(
            name="best",
            price_pct=settings.SCENARIO_BEST_PRICE_PCT,
            difficulty_pct=settings.SCENARIO_BEST_DIFFICULTY_PCT,
            electricity_pct=settings.SCENARIO_BEST_ELECTRICITY_PCT,
            client_revenue_share=client_share,
        ),
        "worst": ScenarioConfig(
            name="worst",
            price_pct=settings.SCENARIO_WORST_PRICE_PCT,
            difficulty_pct=settings.SCENARIO_WORST_DIFFICULTY_PCT,
            electricity_pct=settings.SCENARIO_WORST_ELECTRICITY_PCT,
            client_revenue_share=client_share,
        ),
    }
