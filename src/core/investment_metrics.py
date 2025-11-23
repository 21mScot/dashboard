# src/core/investment_metrics.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

try:
    import numpy_financial as npf
except Exception:  # noqa: BLE001
    npf = None


@dataclass
class InvestmentMetrics:
    total_net_cash_gbp: float
    irr_monthly: Optional[float]
    irr_annual: Optional[float]


def compute_investment_metrics(
    df: pd.DataFrame,
    initial_capex_gbp: float,
) -> InvestmentMetrics:
    """
    Compute headline investment metrics for a project.

    Requires a 'net_cashflow_gbp' column. initial_capex_gbp is treated as a
    negative cashflow at t=0 (positive input here).
    """
    if "net_cashflow_gbp" not in df.columns:
        raise ValueError("DataFrame must contain 'net_cashflow_gbp' column")

    net_cf = df["net_cashflow_gbp"].astype(float).to_numpy()

    print("Initial CapEx:", initial_capex_gbp)
    print("First 10 net CFs:", df["net_cashflow_gbp"].head(10).to_list())

    total_net_cash_gbp = -float(initial_capex_gbp) + float(net_cf.sum())

    cashflows = np.concatenate(([-float(initial_capex_gbp)], net_cf, [0.0]))
    print("Cashflows passed to IRR:", cashflows)

    irr_monthly = None
    if npf is not None:
        try:
            irr_monthly = float(npf.irr(cashflows))
        except Exception:
            irr_monthly = None

    if irr_monthly is None or np.isnan(irr_monthly):
        irr_monthly = None
        irr_annual = None
    else:
        irr_annual = (1.0 + irr_monthly) ** 12 - 1.0

    return InvestmentMetrics(
        total_net_cash_gbp=total_net_cash_gbp,
        irr_monthly=irr_monthly,
        irr_annual=irr_annual,
    )
