from __future__ import annotations

import streamlit as st

from src.config import settings


def render_assumptions_and_methodology() -> None:
    """Render the Assumptions & Methodology tab content."""

    st.subheader("📋 Assumptions & Methodology")

    # -----------------------------------------------------
    # NETWORK DATA MODES
    # -----------------------------------------------------
    st.markdown("### Network data modes")

    st.markdown(
        """
We use a single set of BTC network parameters for all calculations in this
dashboard. Those parameters come from one of three modes:

- **Live mode**  
  - Source: external APIs  
    - BTC price → CoinGecko  
    - Difficulty → Blockchain.info  
    - Block height → Mempool.space  
  - When used: when *Use live BTC network data* is enabled **and** all API
    calls succeed.  
  - Effect: all BTC/day and revenue calculations use the latest available
    network values.

- **Static mode (user-selected)**  
  - Source: fixed defaults defined in the app settings.  
  - When used: when the toggle is **off**.  
  - Effect: calculations use a stable snapshot, useful for testing,
    demonstrations and repeatable comparisons.

- **Static fallback mode (live unavailable)**  
  - Source: the same fixed defaults as static mode.  
  - When used: when the toggle is **on**, but live data cannot be retrieved
    (e.g., offline, rate-limited, API issues).  
  - Effect: the app clearly warns that live data failed and automatically
    falls back to static assumptions.

In all cases, the **left-hand sidebar displays the exact BTC price,
difficulty, and block subsidy values that the model actually uses**.
        """
    )

    # -----------------------------------------------------
    # BLOCK SUBSIDY
    # -----------------------------------------------------
    st.markdown("### Block subsidy")

    st.markdown(
        f"""
- We assume a block subsidy of **{settings.DEFAULT_BLOCK_SUBSIDY_BTC} BTC**
  (post-2024 halving).  
- This subsidy is applied uniformly across the entire forecast period for this
  proof-of-concept version.  
- Future versions may introduce a halving schedule so forecasts automatically
  reduce subsidy at each halving point.
        """
    )

    # -----------------------------------------------------
    # EXTERNAL VALIDATION SOURCES
    # -----------------------------------------------------
    st.markdown("### External validation of miner economics")

    st.markdown(
        """
To ensure miner-level BTC/day and USD/day calculations are accurate, the
`miner_economics` engine has been validated against three independent
industry sources. Each plays a different role in the validation hierarchy.

#### **1. WhatToMine — Primary (strict mathematical validation)**  
- **Status:** Closed-source  
- **Why used:** Most configurable calculator in the industry.  
- Allows exact alignment of assumptions:  
  - Hashrate  
  - Power draw  
  - Bitcoin price  
  - Difficulty  
  - Block reward  
  - Pool fees (set to 0%)  
- **Result:** Our model reproduces WhatToMine outputs when given the same
  inputs.  
- **Role:** Core benchmark for correctness.

#### **2. HashrateIndex — Secondary (market realism)**  
- **Status:** Commercial data provider  
- **Why used:** Provides widely viewed profitability figures.  
- Difficulty/reward cannot be configured directly, but revenue/day ranges
  offer a realistic market comparison.  
- **Role:** Ensures forecasts sit within credible real-world ranges.  
- **Note:** Some differences are expected due to transaction fees and internal
  assumptions.

#### **3. Braiins — Tertiary (sanity check)**  
- **Status:** Proprietary tool  
- **Why used:** Provides a third, independent view of miner profitability.  
- Does **not** allow configuration of difficulty, BTC price or subsidy, and
  does not output BTC/day directly.  
- **Role:** Used only for high-level confidence, not strict validation.

#### **Validation hierarchy summary**

|Source       |Purpose                  |Validation type       |Notes                  |
|-------------|-------------------------|----------------------|-----------------------|
|WhatToMine   |Core correctness         |Strict mathematical   |Fully configurable     |
|HashrateIndex|Market realism           |External confirmation |Uses market fees & data|
|Braiins      |Confidence & sanity check|Approximate validation|Not configurable       |

Together, these sources provide:  
- **Mathematical correctness** (WhatToMine)  
- **Market realism** (HashrateIndex)  
- **External confidence** (Braiins)
        """
    )

    # -----------------------------------------------------
    # OTHER MODELLING NOTES
    # -----------------------------------------------------
    st.markdown("### Other modelling notes")

    st.markdown(
        """
- Network difficulty is treated as constant within each scenario period.  
- BTC/day estimates include **only block subsidy**, not transaction fees.  
- Electricity cost, uptime and cooling overheads are fully user-configurable
  in the **Site setup** panel.  
- Future enhancements may include:  
  - Transaction-fee modelling  
  - Miner-specific efficiency curves  
  - Difficulty-projection curves  
  - Halving-aware long-term forecasts  
        """
    )
