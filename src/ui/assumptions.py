from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd
import streamlit as st

from src.config import settings


@dataclass
class BulletItem:
    text: str
    subitems: List[str] = field(default_factory=list)


@dataclass
class AssumptionSection:
    title: str
    paragraphs: List[str]
    bullets: List[BulletItem] = field(default_factory=list)
    table: Optional[List[List[str]]] = None


def get_assumptions_sections() -> list[AssumptionSection]:
    """Return shared assumptions/methodology text for UI and PDF."""
    block_subsidy_lines = [
        f"We assume a block subsidy of **{settings.DEFAULT_BLOCK_SUBSIDY_BTC} BTC** "
        "(post-2024 halving).",
        "This subsidy is applied uniformly across the entire forecast period for "
        "this proof-of-concept version.",
        "Future versions may introduce a halving schedule so forecasts automatically "
        "reduce subsidy at each halving point.",
    ]

    return [
        AssumptionSection(
            title="Network data modes",
            paragraphs=[
                "We use a single set of BTC network parameters for all calculations "
                "in this dashboard. Those parameters come from one of three modes:",
                "In all cases, the left-hand sidebar displays the exact BTC price, "
                "difficulty, and block subsidy values that the model actually uses.",
            ],
            bullets=[
                BulletItem(
                    text="**Live mode**",
                    subitems=[
                        "Source: external APIs (CoinGecko for BTC price, "
                        "Blockchain.info for difficulty, Mempool.space for block "
                        "height).",
                        "When used: when *Use live BTC network data* is enabled and "
                        "all API calls succeed.",
                        "Effect: all BTC/day and revenue calculations use the latest "
                        "available network values.",
                    ],
                ),
                BulletItem(
                    text="**Static mode (user-selected)**",
                    subitems=[
                        "Source: fixed defaults defined in the app settings.",
                        "When used: when the toggle is **off**.",
                        "Effect: calculations use a stable snapshot, useful for "
                        "testing, demonstrations and repeatable comparisons.",
                    ],
                ),
                BulletItem(
                    text="**Static fallback mode (live unavailable)**",
                    subitems=[
                        "Source: the same fixed defaults as static mode.",
                        "When used: when the toggle is **on**, but live data cannot "
                        "be retrieved (offline, rate-limited, API issues).",
                        "Effect: the app clearly warns that live data failed and "
                        "automatically falls back to static assumptions.",
                    ],
                ),
            ],
        ),
        AssumptionSection(
            title="Block subsidy",
            paragraphs=block_subsidy_lines,
        ),
        AssumptionSection(
            title="External validation of miner economics",
            paragraphs=[
                "To ensure miner-level BTC/day and USD/day calculations are accurate, "
                "the `miner_economics` engine has been validated against three "
                "independent industry sources. Each plays a different role in the "
                "validation hierarchy.",
            ],
            bullets=[
                BulletItem(
                    text="WhatToMine — Primary (strict mathematical validation)",
                    subitems=[
                        "Status: Closed-source.",
                        "Why used: Most configurable calculator in the industry.",
                        "Allows exact alignment of assumptions: hashrate, power draw, "
                        "BTC price, difficulty, block reward, pool fees (0%).",
                        "Result: Our model reproduces WhatToMine outputs when given "
                        "the same inputs.",
                        "Role: Core benchmark for correctness.",
                    ],
                ),
                BulletItem(
                    text="HashrateIndex — Secondary (market realism)",
                    subitems=[
                        "Status: Commercial data provider.",
                        "Why used: Provides widely viewed profitability figures.",
                        "Difficulty/reward cannot be configured directly, but "
                        "revenue/day ranges offer a realistic market comparison.",
                        "Role: Ensures forecasts sit within credible real-world "
                        "ranges.",
                        "Note: Some differences are expected due to transaction fees "
                        "and internal assumptions.",
                    ],
                ),
                BulletItem(
                    text="Braiins — Tertiary (sanity check)",
                    subitems=[
                        "Status: Proprietary tool.",
                        "Why used: Provides a third, independent view of miner "
                        "profitability.",
                        "Does not allow configuration of difficulty, BTC price or "
                        "subsidy, and does not output BTC/day directly.",
                        "Role: Used only for high-level confidence, not strict "
                        "validation.",
                    ],
                ),
            ],
            table=[
                ["Source", "Purpose", "Validation type", "Notes"],
                [
                    "WhatToMine",
                    "Core correctness",
                    "Strict mathematical",
                    "Fully configurable",
                ],
                [
                    "HashrateIndex",
                    "Market realism",
                    "External confirmation",
                    "Uses market fees & data",
                ],
                [
                    "Braiins",
                    "Confidence & sanity check",
                    "Approximate validation",
                    "Not configurable",
                ],
            ],
        ),
        AssumptionSection(
            title="Other modelling notes",
            paragraphs=[
                "Network difficulty is treated as constant within each scenario "
                "period.",
                "BTC/day estimates include **only block subsidy**, not transaction "
                "fees.",
                "Electricity cost, uptime and cooling overheads are fully "
                "user-configurable in the **Site setup** panel.",
                "Future enhancements may include transaction-fee modelling, "
                "miner-specific efficiency curves, difficulty-projection curves, and "
                "halving-aware long-term forecasts.",
            ],
        ),
    ]


def render_assumptions_and_methodology() -> None:
    """Render the Assumptions & Methodology tab content."""

    st.subheader("📋 Assumptions & Methodology")
    for section in get_assumptions_sections():
        st.markdown(f"### {section.title}")
        for paragraph in section.paragraphs:
            st.markdown(paragraph)
        for bullet in section.bullets:
            lines = [f"- {bullet.text}"]
            for sub in bullet.subitems:
                lines.append(f"  - {sub}")
            st.markdown("\n".join(lines))
        if section.table:
            df = pd.DataFrame(section.table[1:], columns=section.table[0])
            st.dataframe(df, hide_index=True, width="stretch")
