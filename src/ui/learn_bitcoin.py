from __future__ import annotations

import streamlit as st


def render_learn_about_bitcoin() -> None:
    """Render the 'Learn about Bitcoin' section with UX-friendly expanders."""

    st.header("Learn about Bitcoin")
    st.caption(
        "A curated set of trusted resources to help you understand Bitcoin, "
        "why it uses energy, and how mining fits into your site economics."
    )

    # --- 1. Bitcoin in 5 minutes ---
    with st.expander("1. Bitcoin in 5 minutes", expanded=True):
        st.markdown(
            """
**Start here if you're new to Bitcoin.**

- 🌐 **Sats vs Fiat** - a visual, first-principles introduction to Bitcoin:
  - [satsvsfiat.com](https://www.satsvsfiat.com/)
- 📘 **What is Bitcoin?** - plain-English explainer:
  - [River Learn - What is Bitcoin?](https://river.com/learn/what-is-bitcoin/)

> Use these if you want a quick overview before looking at numbers, mining,
> or investment decisions.
"""
        )

    # --- 2. Why Bitcoin uses energy ---
    with st.expander("2. Why Bitcoin uses energy"):
        st.markdown(
            """
**This section is for understanding *why* Bitcoin uses energy and why miners exist.**

- ⚡ **Energy, money, and Bitcoin**:
  - [Sats vs Fiat - Energy & Money][svf-energy]
- 📊 **Mining energy mix & sustainability**:
  - [Bitcoin Mining Council - Data & Reports][bmc-data]
- 🛠️ **How mining keeps Bitcoin secure**:
  - [River Learn - How Bitcoin Mining Works][river-mining]

> These resources help answer questions like:
> *"Is mining wasteful?", "Is this environmentally defensible?", and
> "Why is energy use essential to Bitcoin's security?"*

[svf-energy]: https://www.satsvsfiat.com/
[bmc-data]: https://bitcoinminingcouncil.com/
[river-mining]: https://river.com/learn/what-is-bitcoin-mining/
"""
        )

    # --- 3. How Bitcoin mining works in practice ---
    with st.expander("3. How Bitcoin mining works in practice"):
        st.markdown(
            """
**For operators and engineers who want to understand the mechanics.**

- 🧱 **Blocks, hashrate, difficulty, and reward:**
  - [Mempool.Space Academy - Mining](https://mempool.space/academy/mining)
- 🧮 **Mining guides, firmware, and optimisation:**
  - [Braiins - Mining Blog & Guides](https://braiins.com/blog)
- 📈 **ASIC market data (efficiency, prices, revenue per TH):**
  - [HashrateIndex - Mining Data](https://hashrateindex.com/)

> These links pair well with the tools in this app that show:
> miner efficiency, breakeven power price, site utilisation, and payback.
"""
        )

    # --- 4. Bitcoin as sound money & investment logic ---
    with st.expander("4. Bitcoin as sound money & investment logic"):
        st.markdown(
            """
**For decision-makers looking at Bitcoin from an economic and strategic angle.**

- 📗 **Book - The Bitcoin Standard** (Saifedean Ammous)
  - Explains Bitcoin as hard money and why fixed supply matters.
- 🧠 **Essay series - "Gradually, Then Suddenly" (Parker Lewis):**
  - [Unchained - Gradually, Then Suddenly][gts]
- 📊 **Macro & investment perspective - Lyn Alden:**
  - [Lyn Alden - Bitcoin Research](https://www.lynalden.com/)

> These resources help answer:
> *"Why would I hold or mine Bitcoin at all?", "How does halving affect supply?",*
> and *"Is this a hedge, a speculation, or infrastructure?"*

[gts]: https://unchained.com/blog/category/gradually-then-suddenly/
"""
        )

    # --- 5. Technical deep dive (optional) ---
    with st.expander("5. Technical deep dive (optional)"):
        st.markdown(
            """
**For technically inclined users and developers.**

- 📘 **Mastering Bitcoin - Andreas M. Antonopoulos** (free online):
  - [Mastering Bitcoin (GitHub)](https://github.com/bitcoinbook/bitcoinbook)
- 🧩 **Bitcoin Optech - Technical insights & updates:**
  - [Bitcoin Optech](https://bitcoinops.org/)
- ⚙️ **Advanced mining concepts - Braiins:**
  - [Braiins - Advanced Mining Topics](https://braiins.com/blog)

> Optional, but useful if you or your technical team want to verify
> protocol-level behaviours behind the economics shown in this app.
"""
        )

    # --- Suggested learning path summary ---
    with st.expander("Suggested learning path for energy site operators"):
        st.markdown(
            """
**Recommended order if you're evaluating a Bitcoin mining project:**

1. 👉 **Start** with:
   - [Sats vs Fiat](https://www.satsvsfiat.com/)
   - [River - What is Bitcoin?](https://river.com/learn/what-is-bitcoin/)
2. ⚡ **Then understand energy use & security**:
   - Bitcoin Mining Council reports
   - River - Mining basics
3. 🧮 **Then connect it to your site economics**:
   - HashrateIndex (ASIC and revenue data)
   - Mining guides from Braiins
4. 🧠 **Finally, zoom out to the investment logic**:
   - The Bitcoin Standard
   - Parker Lewis
   - Lyn Alden

> This mirrors how this app is structured:
> you can go from *"What is Bitcoin?"* -> *"Why energy?"* -> *"How mining works?"* ->
> *"Does this make sense for my site?"*.
"""
        )
