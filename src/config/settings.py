# src/config/settings.py

"""
Global configuration and constants for the dashboard.
This file centralises:
- Fallback static assumptions
- API endpoint URLs
- Caching TTLs
- Any future environment-based configuration
"""

# ---------------------------------------------------------
# Live data API endpoints
# ---------------------------------------------------------

# Coingecko simple price endpoint
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Blockchain.info raw difficulty endpoint
BLOCKCHAIN_DIFFICULTY_URL = "https://blockchain.info/q/getdifficulty"

# Mempool.space block tip height (optional)
MEMPOOL_BLOCKTIP_URL = "https://mempool.space/api/v1/blocks/tip-height"


# ---------------------------------------------------------
# Default fallback values (when live data is unavailable)
# ---------------------------------------------------------

DEFAULT_BTC_PRICE_USD = 50000.0
DEFAULT_DIFFICULTY = 150_000_000_000_000_000  # placeholder; update when required
DEFAULT_BLOCK_SUBSIDY_BTC = 3.125  # Post-2024 halving


# ---------------------------------------------------------
# Live data caching configuration
# ---------------------------------------------------------

# Time-to-live (TTL) for the cached network data, in hours
LIVE_DATA_TTL_HOURS = 24


# ---------------------------------------------------------
# Other app-wide settings (extend later)
# ---------------------------------------------------------

# E.g. simulation defaults, cost assumptions, UI constants
