from __future__ import annotations

from dataclasses import dataclass
from math import floor

from src.ui.miner_selection import MinerOption
from src.ui.site_inputs import SiteInputs


@dataclass
class SiteDerivedMetrics:
    """Derived metrics from site inputs + selected miner."""

    asics_supported: int
    asic_power_kw: float
    site_power_kw: float
    site_power_used_kw: float
    site_power_spare_kw: float

    # Placeholders for future BTC integration
    btc_per_asic_per_day: float | None = None
    btc_per_site_per_day: float | None = None


def compute_site_metrics(
    site_inputs: SiteInputs, miner: MinerOption
) -> SiteDerivedMetrics:
    """Given site inputs and a miner, compute how many ASICs fit and power usage."""
    asic_power_kw = miner.power_w / 1000.0

    if asic_power_kw <= 0:
        asics_supported = 0
    else:
        asics_supported = floor(site_inputs.site_power_kw / asic_power_kw)

    site_power_used_kw = asics_supported * asic_power_kw
    site_power_spare_kw = site_inputs.site_power_kw - site_power_used_kw

    return SiteDerivedMetrics(
        asics_supported=asics_supported,
        asic_power_kw=asic_power_kw,
        site_power_kw=site_inputs.site_power_kw,
        site_power_used_kw=site_power_used_kw,
        site_power_spare_kw=site_power_spare_kw,
        # btc_per_asic_per_day and btc_per_site_per_day left as None for now –
        # we’ll wire these in from the SEC backend later.
    )
