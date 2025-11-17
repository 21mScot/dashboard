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

DEFAULT_BTC_PRICE_USD = 90000.0
DEFAULT_NETWORK_DIFFICULTY = 150_000_000_000_000
DEFAULT_BLOCK_SUBSIDY_BTC = BLOCK_SUBSIDY_BTC

# --- Local currency / FX assumptions ---

DEFAULT_USD_TO_GBP = 0.75

# --- Scenario modelling defaults ---

# Revenue share: fraction of gross BTC revenue going to the AD operator (client).
SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE = 0.90

# Price shocks (% change)
SCENARIO_BASE_PRICE_PCT = 0.00
SCENARIO_BEST_PRICE_PCT = 0.20
SCENARIO_WORST_PRICE_PCT = -0.20

# Network difficulty shocks
SCENARIO_BASE_DIFFICULTY_PCT = 0.00
SCENARIO_BEST_DIFFICULTY_PCT = -0.10
SCENARIO_WORST_DIFFICULTY_PCT = 0.20

# Electricity cost shocks
SCENARIO_BASE_ELECTRICITY_PCT = 0.00
SCENARIO_BEST_ELECTRICITY_PCT = -0.10
SCENARIO_WORST_ELECTRICITY_PCT = 0.20

# Fallback project duration (years)
SCENARIO_FALLBACK_PROJECT_YEARS = 4

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
