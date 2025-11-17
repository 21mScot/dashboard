# src/config/settings.py

# --- Live data / network constants ---

MEMPOOL_BLOCKTIP_URL = "https://mempool.space/api/v1/blocks/tip-height"
BLOCKCHAIN_DIFFICULTY_URL = "https://blockchain.info/q/getdifficulty"
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Requests / caching config
LIVE_DATA_REQUEST_TIMEOUT_S = 10
LIVE_DATA_CACHE_TTL_S = 60 * 60 * 24  # 24h during dev

# Optional: identify yourself nicely to public APIs
LIVE_DATA_USER_AGENT = "21mScotDashboard/0.1 (contact: you@example.com)"

# --- Fallback static assumptions (used when live data fails) ---

# Hard-coded post-2024 halving subsidy
BLOCK_SUBSIDY_BTC = 3.125

# Feel free to tweak these to whatever you want to assume in the POC
DEFAULT_BTC_PRICE_USD = 90000.0
DEFAULT_NETWORK_DIFFICULTY = 150_000_000_000_000  # placeholder example
DEFAULT_BLOCK_SUBSIDY_BTC = BLOCK_SUBSIDY_BTC

# --- Local currency / FX assumptions (used at site-economics layer) ---

# Canonical engine works in USD; we convert to GBP at the site layer.
# This is a static assumption for now and can later be replaced by a live FX feed.
DEFAULT_USD_TO_GBP = 0.75

# --- Scenario modelling defaults ---

# Revenue share:
# Fraction of *gross BTC revenue* going to the AD plant operator (client).
# The remaining share (1 - SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE)
# goes to 21mScot as the operating / optimisation partner.
SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE = 0.90

# Best / base / worst case shocks.
# These are *relative changes* (e.g. +0.20 = +20%) that will be applied
# on top of the "base" assumptions for BTC price, network difficulty,
# and electricity cost when building scenarios.
#
# You can adjust these numbers here without touching any UI or engine code.

# BTC price shocks
SCENARIO_BASE_PRICE_PCT = 0.00  # 0% change (anchor)
SCENARIO_BEST_PRICE_PCT = 0.20  # +20% bullish case
SCENARIO_WORST_PRICE_PCT = -0.20  # -20% bearish case

# Network difficulty shocks
SCENARIO_BASE_DIFFICULTY_PCT = 0.00  # 0% change
SCENARIO_BEST_DIFFICULTY_PCT = -0.10  # -10% easier network
SCENARIO_WORST_DIFFICULTY_PCT = 0.20  # +20% more competition

# Electricity cost shocks
SCENARIO_BASE_ELECTRICITY_PCT = 0.00  # 0% change
SCENARIO_BEST_ELECTRICITY_PCT = -0.10  # -10% cheaper power
SCENARIO_WORST_ELECTRICITY_PCT = 0.20  # +20% more expensive power

# Optional: default project length to fall back on if the UI
# does not provide a project duration for some reason.
# The main source of truth is the Overview tab's "Project duration".
SCENARIO_FALLBACK_PROJECT_YEARS = 4

# --- CapEx & tax assumptions (client side – AD plant operator) ---

# Approximate UK corporation tax rate for the AD plant operator.
CLIENT_CORPORATION_TAX_RATE = 0.25  # 25%

# Capital allowance: fraction of qualifying CapEx that can be
# offset against profits in year 1. Simple POC: full expensing.
CLIENT_CAPEX_FIRST_YEAR_ALLOWANCE_PCT = 1.0  # 100% of CapEx

# Accounting lifetime of mining equipment for economic wear & tear.
MINER_ACCOUNTING_LIFETIME_YEARS = 4

# ---------------------------------------------------------
# Chart styling (histogram / BTC bars)
# ---------------------------------------------------------

# Opacity for BTC mined histogram bars (0.0 – 1.0)
SCENARIO_BTC_BAR_OPACITY = 0.25

# Colour for BTC mined bars (Hex or named)
SCENARIO_BTC_BAR_COLOR = "#E9ECF1"

# Should BTC bar borders be shown?
SCENARIO_BTC_BAR_STROKE_WIDTH = 0

# Histogram / BTC mined bar style
SCENARIO_BTC_BAR_OPACITY = 1.0  # Looks like the bars are fully opaque

# Revenue line colour (if you want centralised control)
SCENARIO_REVENUE_LINE_COLOR = "#1f77b4"  # streamlit default blue

# EBITDA line colour
SCENARIO_EBITDA_LINE_COLOR = "#2ca02c"  # greenish

# EBITDA line style (solid/dashed)
SCENARIO_EBITDA_LINE_DASH = [4, 2]  # dashed

# How tall the highest BTC bar should be as a fraction of its axis height
# e.g. 0.6 = tallest bar reaches 60% of the BTC axis
SCENARIO_BTC_BAR_MAX_FRACTION = 0.6
