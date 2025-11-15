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
