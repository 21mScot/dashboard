# src/core/capex.py

from __future__ import annotations

from dataclasses import dataclass

from src.config import settings


@dataclass
class CapexBreakdown:
    """
    Simple breakdown of client-side CapEx in GBP.

    All components are expressed in GBP; we convert from USD using the
    supplied FX rate when computing.
    """

    asic_count: int
    asic_cost_gbp: float
    shipping_gbp: float
    import_duty_gbp: float
    spares_gbp: float
    racking_gbp: float
    cables_gbp: float
    switchgear_gbp: float
    networking_gbp: float
    installation_labour_gbp: float
    certification_gbp: float

    @property
    def total_gbp(self) -> float:
        return (
            self.asic_cost_gbp
            + self.shipping_gbp
            + self.import_duty_gbp
            + self.spares_gbp
            + self.racking_gbp
            + self.cables_gbp
            + self.switchgear_gbp
            + self.networking_gbp
            + self.installation_labour_gbp
            + self.certification_gbp
        )


def compute_capex_breakdown(
    asic_count: int,
    miner_price_usd: float | None = None,
    usd_to_gbp: float | None = None,
) -> CapexBreakdown:
    """
    Compute a model-based CapEx breakdown for the given ASIC count.

    Uses constants from settings.py for infrastructure and installation.
    Miner price can be provided from the UI; otherwise the default in
    settings.py is used. All values are converted from USD to GBP.
    """

    if usd_to_gbp is None:
        usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    if asic_count <= 0:
        # Return an all-zero breakdown so the UI can still render safely.
        return CapexBreakdown(
            asic_count=0,
            asic_cost_gbp=0.0,
            shipping_gbp=0.0,
            import_duty_gbp=0.0,
            spares_gbp=0.0,
            racking_gbp=0.0,
            cables_gbp=0.0,
            switchgear_gbp=0.0,
            networking_gbp=0.0,
            installation_labour_gbp=0.0,
            certification_gbp=0.0,
        )

    # --- ASIC-related costs (USD) ---
    unit_price_usd = miner_price_usd or settings.ASIC_PRICE_USD
    asic_price_usd = unit_price_usd * asic_count
    shipping_usd = settings.ASIC_SHIPPING_USD * asic_count
    import_duty_usd = asic_price_usd * settings.ASIC_IMPORT_DUTY_RATE
    spares_usd = asic_price_usd * settings.ASIC_SPARES_RATE

    # --- Infrastructure / ancillary (USD) ---
    racking_usd = settings.RACKING_COST_PER_MINER_USD * asic_count
    cables_usd = settings.CABLES_COST_PER_MINER_USD * asic_count
    switchgear_usd = settings.SWITCHGEAR_TOTAL_USD
    networking_usd = settings.NETWORKING_TOTAL_USD

    # --- Installation / commissioning (USD) ---
    installation_labour_usd = (
        settings.INSTALL_LABOUR_HOURS * settings.INSTALL_LABOUR_RATE_USD
    )
    certification_usd = settings.CERTIFICATION_COST_USD

    # Convert everything to GBP
    def to_gbp(value_usd: float) -> float:
        return value_usd * usd_to_gbp

    return CapexBreakdown(
        asic_count=asic_count,
        asic_cost_gbp=to_gbp(asic_price_usd),
        shipping_gbp=to_gbp(shipping_usd),
        import_duty_gbp=to_gbp(import_duty_usd),
        spares_gbp=to_gbp(spares_usd),
        racking_gbp=to_gbp(racking_usd),
        cables_gbp=to_gbp(cables_usd),
        switchgear_gbp=to_gbp(switchgear_usd),
        networking_gbp=to_gbp(networking_usd),
        installation_labour_gbp=to_gbp(installation_labour_usd),
        certification_gbp=to_gbp(certification_usd),
    )
