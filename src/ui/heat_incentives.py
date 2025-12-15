# src/ui/heat_incentives.py
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from src.config.env import APP_ENV, ENV_DEV

# Defaults for the lean Level 1 estimate
HOURS_PER_YEAR = 8760
DEFAULT_HEAT_RECOVERY_FRACTION = 0.95
DEFAULT_UTILISABLE_FRACTION = 0.75
DEFAULT_MARGINAL_RHI_TARIFF_P = 2.2  # p/kWh

SCENARIO_RHI_ASSUMPTIONS = {
    "Worst": {"utilisable": 0.65, "tariff_p": 2.0},
    "Base": {"utilisable": 0.75, "tariff_p": 2.2},
    "Best": {"utilisable": 0.85, "tariff_p": 2.4},
}


@dataclass
class RHIComputation:
    site_power_kw: float
    load_factor: float
    hours_per_year: float
    heat_recovery_fraction: float
    utilisable_fraction: float
    delta_q_kwhth_per_year: float
    marginal_tariff_p_per_kwh: float
    rhi_uplift_gbp_per_year: float
    hint_required: bool = False


def _clamp_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_rhi_level1(
    site_power_kw: float,
    load_factor: float,
    heat_recovery_fraction: float = DEFAULT_HEAT_RECOVERY_FRACTION,
    utilisable_fraction: float = DEFAULT_UTILISABLE_FRACTION,
    marginal_tariff_p: float = DEFAULT_MARGINAL_RHI_TARIFF_P,
) -> RHIComputation:
    """
    Level 1 estimate: single-pass substitution of mining heat into digester load.
    """
    safe_power_kw = max(0.0, float(site_power_kw or 0.0))
    safe_load_factor = _clamp_fraction(load_factor or 0.0)

    if safe_power_kw <= 0.0 or safe_load_factor <= 0.0:
        return RHIComputation(
            site_power_kw=safe_power_kw,
            load_factor=safe_load_factor,
            hours_per_year=0.0,
            heat_recovery_fraction=heat_recovery_fraction,
            utilisable_fraction=utilisable_fraction,
            delta_q_kwhth_per_year=0.0,
            marginal_tariff_p_per_kwh=marginal_tariff_p,
            rhi_uplift_gbp_per_year=0.0,
            hint_required=True,
        )

    hours_per_year = HOURS_PER_YEAR * safe_load_factor
    recoverable_heat_kwth = safe_power_kw * heat_recovery_fraction
    delta_q_kwhth_per_year = (
        recoverable_heat_kwth * hours_per_year * utilisable_fraction
    )
    marginal_tariff_gbp_per_kwh = marginal_tariff_p / 100.0
    rhi_uplift_gbp_per_year = delta_q_kwhth_per_year * marginal_tariff_gbp_per_kwh

    return RHIComputation(
        site_power_kw=safe_power_kw,
        load_factor=safe_load_factor,
        hours_per_year=hours_per_year,
        heat_recovery_fraction=heat_recovery_fraction,
        utilisable_fraction=utilisable_fraction,
        delta_q_kwhth_per_year=delta_q_kwhth_per_year,
        marginal_tariff_p_per_kwh=marginal_tariff_p,
        rhi_uplift_gbp_per_year=rhi_uplift_gbp_per_year,
        hint_required=False,
    )


def compute_rhi_scenarios(
    site_power_kw: float,
    load_factor: float,
) -> dict[str, RHIComputation]:
    """
    Build RHI estimates for Worst/Base/Best using fixed scenario assumptions.
    """
    results: dict[str, RHIComputation] = {}
    for label, params in SCENARIO_RHI_ASSUMPTIONS.items():
        results[label] = compute_rhi_level1(
            site_power_kw=site_power_kw,
            load_factor=load_factor,
            utilisable_fraction=params["utilisable"],
            marginal_tariff_p=params["tariff_p"],
        )
    return results


def _format_currency_per_year(value: float) -> str:
    return f"£{value:,.0f}/yr"


def _format_heat_per_year(value: float) -> str:
    return f"{value:,.0f} kWhth/yr"


def _compute_required_power_kw(
    target_uplift_gbp: float,
    tariff_p: float,
    load_factor: float,
    heat_recovery: float,
    utilisable: float,
) -> tuple[float, float]:
    if tariff_p <= 0 or load_factor <= 0 or heat_recovery <= 0 or utilisable <= 0:
        return 0.0, 0.0
    marginal_tariff_gbp = tariff_p / 100.0
    required_delta_q = abs(target_uplift_gbp / marginal_tariff_gbp)
    denominator = HOURS_PER_YEAR * load_factor * heat_recovery * utilisable
    required_power_kw = abs(required_delta_q / denominator) if denominator > 0 else 0.0
    return required_delta_q, required_power_kw


def render_heat_and_incentives(site_power_kw: float, load_factor: float) -> None:
    """
    Render the lean Heat & Incentives section (Level 1).
    """
    st.markdown("## 3. Heat & Incentives")

    # Pull override values from session (expander rendered below uses the same keys)
    override_utilisable = st.session_state.get(
        "rhi_override_utilisable", DEFAULT_UTILISABLE_FRACTION
    )
    override_tariff_p = st.session_state.get(
        "rhi_override_tariff_p", DEFAULT_MARGINAL_RHI_TARIFF_P
    )
    utilisable_fraction = override_utilisable or DEFAULT_UTILISABLE_FRACTION
    marginal_tariff_p = override_tariff_p or DEFAULT_MARGINAL_RHI_TARIFF_P

    base_result = compute_rhi_level1(
        site_power_kw=site_power_kw,
        load_factor=load_factor,
        heat_recovery_fraction=DEFAULT_HEAT_RECOVERY_FRACTION,
        utilisable_fraction=utilisable_fraction,
        marginal_tariff_p=marginal_tariff_p,
    )
    scenario_results = compute_rhi_scenarios(
        site_power_kw=site_power_kw,
        load_factor=load_factor,
    )
    st.session_state["rhi_site_power_kw"] = site_power_kw
    st.session_state["rhi_load_factor"] = load_factor

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Estimated RHI uplift (indicative)",
            _format_currency_per_year(base_result.rhi_uplift_gbp_per_year),
            help=(
                "Calculated from site power × uptime × default heat recovery (0.95) × "
                "default utilisable fraction (0.75) × assumed marginal tariff "
                f"({DEFAULT_MARGINAL_RHI_TARIFF_P:.2f} p/kWh). "
                "Refine assumptions in the expander if required."
            ),
        )
    with c2:
        st.metric(
            "Estimated additional eligible heat enabled",
            _format_heat_per_year(base_result.delta_q_kwhth_per_year),
        )
    with c3:
        st.metric(
            "Assumed marginal RHI tariff",
            f"{base_result.marginal_tariff_p_per_kwh:.2f} p/kWh",
        )
    st.caption(
        "Based on "
        f"{base_result.site_power_kw:,.0f} kW × "
        f"{base_result.load_factor * 100:.1f}% uptime × "
        f"{base_result.heat_recovery_fraction:.2f} heat recovery × "
        f"{base_result.utilisable_fraction:.2f} utilisable × "
        f"{base_result.marginal_tariff_p_per_kwh:.2f} p/kWh."
    )

    st.caption(
        "Indicative estimate: assumes mining waste heat replaces non-eligible digester "
        "heating and frees accredited renewable heat for eligible uses "
        "(e.g., wood drying). Mining heat itself is not RHI-eligible."
    )

    if base_result.hint_required:
        st.info("Enter site power and uptime to estimate RHI uplift.")

    with st.expander("View indicative RHI range", expanded=False):
        st.caption(
            "Indicative RHI range (auto-assumed). "
            "Range based on conservative, default, and optimistic assumptions for "
            "utilisable heat and marginal RHI tariff. No additional inputs required."
        )
        sc_cols = st.columns(3)
        for idx, label in enumerate(["Worst", "Base", "Best"]):
            res = scenario_results[label]
            with sc_cols[idx]:
                st.metric(
                    f"{label} case uplift",
                    _format_currency_per_year(res.rhi_uplift_gbp_per_year),
                )

    target_uplift = 22000.0
    target_delta_q, target_power_kw = _compute_required_power_kw(
        target_uplift,
        base_result.marginal_tariff_p_per_kwh,
        base_result.load_factor,
        base_result.heat_recovery_fraction,
        base_result.utilisable_fraction,
    )
    if (
        base_result.marginal_tariff_p_per_kwh > 0
        and base_result.load_factor > 0
        and target_delta_q > 0
    ):
        st.caption(
            f"At {base_result.marginal_tariff_p_per_kwh:.2f} p/kWh, £22,000/yr implies "
            f"≈{target_delta_q:,.0f} kWhth/yr, which requires "
            f"≈{target_power_kw:,.0f} kW at "
            f"{base_result.load_factor * 100:.1f}% uptime (using defaults)."
        )

    # Optional overrides (Level 2 placeholder) — rendered after headline figures
    with st.expander("Refine RHI estimate (optional)", expanded=False):
        st.write(
            "If you know your tariff tiers, digester heat demand, and eligible heat "
            "sink (e.g., wood drying), you can refine ΔQ and the marginal tariff. "
            "Advanced refinement (tariff tiers, digester demand, eligible sink) "
            "can be added later if needed."
        )
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Override utilisable fraction (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=override_utilisable,
                step=0.01,
                format="%.2f",
                key="rhi_override_utilisable",
            )
        with col2:
            st.number_input(
                "Override marginal tariff (p/kWh)",
                min_value=0.0,
                value=override_tariff_p,
                step=0.01,
                format="%.2f",
                key="rhi_override_tariff_p",
            )

        expected_uplift = st.number_input(
            "Operator expected uplift (£/yr) (optional)",
            min_value=0.0,
            value=0.0,
            step=1000.0,
        )
        if expected_uplift > 0:
            if marginal_tariff_p <= 0:
                st.info("Enter a non-zero tariff to see required heat/power.")
            else:
                req_delta_q, req_power_kw = _compute_required_power_kw(
                    target_uplift_gbp=expected_uplift,
                    tariff_p=marginal_tariff_p,
                    load_factor=base_result.load_factor,
                    heat_recovery=base_result.heat_recovery_fraction,
                    utilisable=base_result.utilisable_fraction,
                )
                diff_gbp = base_result.rhi_uplift_gbp_per_year - expected_uplift
                pct_diff = diff_gbp / expected_uplift if expected_uplift else 0.0

                st.markdown("##### Calibration helper")
                cal1, cal2, cal3 = st.columns(3)
                with cal1:
                    st.metric(
                        "Implied eligible heat needed",
                        _format_heat_per_year(req_delta_q),
                    )
                with cal2:
                    st.metric(
                        "Implied miner power needed",
                        f"{req_power_kw:,.0f} kW" if req_power_kw > 0 else "—",
                    )
                with cal3:
                    st.metric(
                        "Difference vs current estimate",
                        _format_currency_per_year(diff_gbp),
                        delta=f"{pct_diff:+.1%}" if expected_uplift else None,
                    )

        if APP_ENV == ENV_DEV:
            with st.expander("Refine RHI debugger...", expanded=False):
                st.caption("Debug view for current RHI inputs and outputs (dev only).")
                st.json(
                    {
                        "inputs": {
                            "power_kw": f"{base_result.site_power_kw:,.0f}",
                            "load_factor": f"{base_result.load_factor:.3f}",
                            "hours_per_year": f"{base_result.hours_per_year:,.1f}",
                            "heat_recovery_fraction": (
                                f"{base_result.heat_recovery_fraction:.2f}"
                            ),
                            "utilisable_fraction": (
                                f"{base_result.utilisable_fraction:.2f}"
                            ),
                            "marginal_tariff_p_per_kwh": (
                                f"{base_result.marginal_tariff_p_per_kwh:.2f}"
                            ),
                        },
                        "outputs": {
                            "delta_q_kwhth_per_year": (
                                f"{base_result.delta_q_kwhth_per_year:,.0f}"
                            ),
                            "rhi_uplift_gbp_per_year": (
                                f"{base_result.rhi_uplift_gbp_per_year:,.0f}"
                            ),
                        },
                        "scenarios": {
                            label: {
                                "utilisable_fraction": f"{res.utilisable_fraction:.2f}",
                                "marginal_tariff_p_per_kwh": (
                                    f"{res.marginal_tariff_p_per_kwh:.2f}"
                                ),
                                "delta_q_kwhth_per_year": (
                                    f"{res.delta_q_kwhth_per_year:,.0f}"
                                ),
                                "rhi_uplift_gbp_per_year": (
                                    f"{res.rhi_uplift_gbp_per_year:,.0f}"
                                ),
                            }
                            for label, res in scenario_results.items()
                        },
                    }
                )

    # Persist for downstream tabs (scenarios)
    st.session_state["rhi_level1_base"] = base_result
    st.session_state["rhi_level1_scenarios"] = scenario_results
