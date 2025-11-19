# src/core/miner_models.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MinerOption:
    """
    Represents a single ASIC miner option.

    Kept in core models so both UI (selection) and core calculations
    (site metrics, capex) can depend on the same schema.
    """

    name: str
    hashrate_th: float  # terahash per second
    power_w: int  # watts
    efficiency_j_per_th: float  # joules per terahash
    supplier: str | None = None
    price_usd: float | None = None
