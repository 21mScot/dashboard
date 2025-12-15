# src/config/settings.py

import os
from datetime import date

from src.config.env import APP_ENV

# Development / production settings for Bitcoin mining economics dashboard
DEV_DEFAULT_SITE_POWER_KW = 1000
DEV_DEFAULT_POWER_PRICE_GBP_PER_KWH = 0.045
DEV_DEFAULT_UPTIME_PCT = 98
# Dev-only miner catalogue selector: "legacy_wtm", "chatgpt_test", or "prod"
DEV_MINER_SET = os.getenv("DEV_MINER_SET", "prod").lower()

# --- Live data / network constants ---
# Blockchain.info - est. 2011, Ben Reeves (UK), now Blockchain.com (not FOSS)
# Mempool.space - est. 2020, Self-hostable open-source Bitcoin explorer, Wiz, Asia
# Blockstream.com - est. 2014, Adam Back, (not fully FOSS, but Blockstream.Espora is)
# Bitcoinlib (Python): FOSS lib, Rene Hartevelt (Amsterdam)
MEMPOOL_BLOCKTIP_URL = "https://mempool.space/api/v1/blocks/tip-height"
BLOCKCHAIN_DIFFICULTY_URL = "https://blockchain.info/q/getdifficulty"
BLOCKCHAIN_HASHRATE_URL = "https://blockchain.info/q/hashrate"
BLOCKCHAIN_HASHRATE_7D_URL = (
    "https://blockchain.info/charts/hash-rate?timespan=7days&format=json"
)
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
# Only available through paid subscription
# HASHRATEINDEX_HASHPRICE_URL = "https://api.hashrateindex.com/api/v1/public/hashprice"
DEFAULT_HASHPRICE_USD_PER_PH_DAY = 40.0

# Requests / caching config
LIVE_DATA_REQUEST_TIMEOUT_S = 10
LIVE_DATA_CACHE_TTL_S = (
    60 * 60 * 24 if APP_ENV == "dev" else 10 * 60
)  # 24h in dev, 10m in prod

# Optional: identify yourself nicely to public APIs
LIVE_DATA_USER_AGENT = "21mScotDashboard/0.1 (contact: you@example.com)"

# --- Fallback static assumptions (used when live data fails) ---

# Hard-coded post-2024 halving subsidy
BLOCK_SUBSIDY_BTC = 3.125

DEFAULT_BTC_PRICE_USD = 90000.0
DEFAULT_NETWORK_DIFFICULTY = 150_000_000_000_000
DEFAULT_BLOCK_SUBSIDY_BTC = BLOCK_SUBSIDY_BTC
FORECAST_START_DATE = date(2024, 1, 1)

# --- Local currency / FX assumptions ---

DEFAULT_USD_TO_GBP = 0.75

# --- Scenario modelling defaults ---

# Revenue share: fraction of gross BTC revenue going to the AD operator (client).
SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE = 0.90

# Price shocks (% change)
SCENARIO_BASE_PRICE_PCT = 0.00
SCENARIO_BEST_PRICE_PCT = 0.20
SCENARIO_WORST_PRICE_PCT = -0.20

# Network difficulty level shocks (percentage applied to difficulty level, not growth)
# e.g. +20.0 = difficulty 20% harder -> BTC / 1.20; -10.0 = 10% easier -> BTC / 0.90
SCENARIO_BASE_DIFFICULTY_LEVEL_SHOCK_PCT = 0.0
SCENARIO_BEST_DIFFICULTY_LEVEL_SHOCK_PCT = -10.0
SCENARIO_WORST_DIFFICULTY_LEVEL_SHOCK_PCT = 20.0

# Electricity cost shocks
SCENARIO_BASE_ELECTRICITY_PCT = 0.00
SCENARIO_BEST_ELECTRICITY_PCT = -0.10
SCENARIO_WORST_ELECTRICITY_PCT = 0.20

# Fallback project duration (years)
SCENARIO_FALLBACK_PROJECT_YEARS = 4

# Projected network dynamics (base case)
# Expressed as annual percentages (e.g. 50.0 = +50%/year)
DEFAULT_ANNUAL_DIFFICULTY_GROWTH_PCT = 0.0
HALVING_INTERVAL_YEARS = 4
# Stored as tuple to avoid datetime import in settings
NEXT_HALVING_DATE = (2028, 4, 1)  # YYYY, M, D

# Block fees (base) for forward projections
DEFAULT_FEE_BTC_PER_BLOCK = 0.025

# UI defaults for forecast sliders (expressed as %)
DEFAULT_HASHRATE_GROWTH_PCT = 5
DEFAULT_FEE_GROWTH_PCT = 10
DEFAULT_BTC_PRICE_GROWTH_PCT = 20
DATE_DISPLAY_FMT = "%d/%m/%Y"
BITCOIN_ORANGE_HEX = "#F7931A"
FIAT_NEUTRAL_BLUE_HEX = "#1f77b4"
BTC_BAR_GREY_HEX = "#cfd2d6"
LINE_STYLE_ACTUAL = []  # actual/observed series
LINE_STYLE_FORECAST = [6, 3]  # dashed/broken for projections

# UI defaults
PROJECT_GO_LIVE_INCREMENT_WEEKS = 4
DEV_DEFAULT_SITE_POWER_KW = 1000
DEV_DEFAULT_POWER_PRICE_GBP_PER_KWH = 0.045
DEV_DEFAULT_UPTIME_PCT = 98

# Streamlit metric styling (default theme)
METRIC_FONT_FAMILY = "Source Sans Pro, sans-serif"
METRIC_FONT_WEIGHT = 700  # bold weight used for metric values
METRIC_FONT_SIZE_REM = 1.0  # metric value size in rem (≈32px at 16px root)
METRIC_LABEL_FONT_WEIGHT = 600
METRIC_LABEL_FONT_SIZE_REM = 0.875  # label size in rem (≈14px at 16px root)

# --- CapEx assumptions (client – AD operator) ---
# Phase 1: constant values; later made configurable.

# ASIC miner cost components
ASIC_PRICE_USD = 3000.0  # Base miner unit price
ASIC_SHIPPING_USD = 150.0  # Per miner shipping
ASIC_IMPORT_DUTY_RATE = 0.05  # %, applied to miner price
ASIC_SPARES_RATE = 0.03  # %, spare parts allocation

# Infrastructure / ancillary CapEx (site-level)
RACKING_COST_PER_MINER_USD = 80.0
CABLES_COST_PER_MINER_USD = 25.0
SWITCHGEAR_TOTAL_USD = 3000.0
NETWORKING_TOTAL_USD = 1500.0

# Installation / commissioning
INSTALL_LABOUR_HOURS = 50
INSTALL_LABOUR_RATE_USD = 60.0
CERTIFICATION_COST_USD = 500.0

# --- Opex assumptions (annual) ---

MAINTENANCE_COST_PER_MINER_PA_USD = 50.0
FIRMWARE_LICENSE_PER_MINER_PA_USD = 20.0
ANNUAL_FAILURE_RATE = 0.02  # placeholder for future modelling

# --- Tax assumptions ---

CLIENT_CORPORATION_TAX_RATE = 0.25  # UK corp tax
CLIENT_CAPEX_FIRST_YEAR_ALLOWANCE_PCT = 1.0  # 100% full expensing
MINER_ACCOUNTING_LIFETIME_YEARS = 4

# --- Chart styling ---

SCENARIO_BTC_BAR_OPACITY = 1.0
SCENARIO_BTC_BAR_COLOR = "#E9ECF1"
SCENARIO_BTC_BAR_STROKE_WIDTH = 0
SCENARIO_REVENUE_LINE_COLOR = "#1f77b4"
SCENARIO_EBITDA_LINE_COLOR = "#2ca02c"
SCENARIO_EBITDA_LINE_DASH = [4, 2]
SCENARIO_BTC_BAR_MAX_FRACTION = 0.6

# Histogram defaults (shared)
# Controls how tall the tallest histogram bar appears relative to its axis.
HISTOGRAM_HEIGHT_RATIO = 0.6  # e.g. 0.8 = top bar reaches 80% of right axis

# Controls the bar colour for the histogram (any Plotly-compatible colour string).
HISTOGRAM_COLOR = "rgba(128,128,128,0.5)"  # semi-transparent light grey
HISTOGRAM_Y_PAD_PCT = 0.30  # y-axis extends 30% above max by default
LINE_Y_PAD_PCT = 0.30  # y-axis pad for line charts
