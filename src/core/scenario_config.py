# src/core/scenario_config.py
from __future__ import annotations

from typing import Literal

from src.config import settings
from src.core.scenario_models import ScenarioConfig

ScenarioName = Literal["base", "best", "worst"]


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
