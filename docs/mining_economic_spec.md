# Mining economics – model spec
## 0.fetch live data - FOSS first sources
0.1 load_network_data(use_live) 
    if use_live = False
        Load static defaults - constants
    else    
        Get endpoins for 
            CoinGeck - BTC price (Coinbase fall back)
            Blockchain.info - difficulty
            mempool.space - block height
            Frankfurter - exchange rate
0.2 TTL - 'Time To Live' 24 hours, LIVE_DATA_CACHE_TTL_S (60*60*24)
0.2 cache locally for 24 hours
0.3 LIVE_DATA_USER_AGENT (e.g via env var) - stored in 'secrets' not in repo
In practice, each fetch cycle looks something like:
	1.	User opens the app or changes an input
	•	e.g. they tick “Use live BTC network data”.
	2.	App checks the cache
	•	“Do I already have fresh-enough BTC price / difficulty / mempool data?”
	3.	If cache is fresh → use it
	•	No outbound API calls, super fast.
	4.	If cache is stale or missing → make API call(s)
	•	Call CoinGecko, Blockchain.com, Mempool.space etc.
	•	Parse JSON responses into your own internal dataclasses / models.
	5.	Store the result in cache + return it
	•	So the next user interaction can reuse it, until it expires.
	6.	UI renders using those values
	•	BTC price, difficulty, block height, maybe FX rate.

Example: LIVE_DATA_CACHE_TTL_S = 300
	•	Means: once we fetch BTC price, we reuse it for 300 seconds (5 min).
	•	After that, the next request will trigger a fresh API call.

So TTL is your freshness vs load trade-off:
	•	Short TTL → fresher data, more API calls.
	•	Long TTL → fewer calls, but data can be a bit stale.

For mining economics, 1–10 minutes TTL for price/difficulty is usually absolutely fine.    

What else are you missing?

You’re already thinking smartly about caching and credentials. Here are the other big rocks I’d add to your mental model.

✅ a) Rate limiting & politeness

Most crypto APIs have rate limits.

You should:
	•	Respect rate limits → TTL + consolidated calls.
	•	Maybe add backoff & retry logic:
	•	e.g. if CoinGecko fails, wait a bit, try again once, then fall back to last known cache + show a “using cached data” message.

✅ b) Fallbacks & offline behaviour

What if:
	•	API is down?
	•	You lose internet at the site demo?

Have:
	•	A “Use static data only” toggle you already partly have.
	•	Graceful message: “Live data temporarily unavailable, using last cached data from [timestamp].”

✅ c) Logging & monitoring (server-side)

You’ll want basic insight into:
	•	How often live data is fetched
	•	API errors over time
	•	Which scenarios users run a lot

At minimum:
	•	Log API errors with enough info to debug, but no secrets.
	•	Maybe later: simple metrics (requests/min, error rate).

✅ d) Testing with mocks

When you move to proper unit tests:
	•	Don’t hit live APIs.
	•	Mock your fetch functions or use test doubles that return fixed JSON.
	•	This keeps tests fast, deterministic, and not dependent on network/third-party uptime.

✅ e) Versioning & determinism for “what-if” runs

For client work, it’s useful to be able to say:
	•	“This forecast was generated with BTC price X, difficulty Y, on date Z.”

That means:
	•	Log / store the inputs used for a given run (e.g. scenario config + snapshot of live data).
	•	Maybe later: write out a tiny JSON summary you can stash alongside PDFs / decks.

✅ f) Cost control (if APIs become paid)

If you upgrade to paid APIs later:
	•	TTL + caching + combined calls will save money.
	•	You can add:
	•	Daily call limits
	•	Graceful degradation: “Live data limit reached for today, using static assumptions.”

✅ g) What if you cannot access the API, how long and many times to we keep trying?

What you might add/change:

Shorten the TTL or add a “Refresh data” button if you want fresher prices/difficulty than 24h, or keep 24h to limit outgoing calls.
No - leave as 24 hours

Add retries/backoff and logging around the requests to handle transient failures and observe uptime/rate limits.
???

Capture and display the actual data timestamp (from providers) separate from “now” so users know data age.
Yes - please implement - underway Fri 21 1921

Add health checks or monitoring around the fetch endpoints to detect provider outages.
Yes - please implement (how to verify?)

Document/parameterize the user-agent and any future secrets via env vars to keep personal info out of production builds.
Yes - get this in early, so we can push MVP to friends to test
How to avoid leaking your personal credentials on the web

This is a big one, and you’re right to be thinking about it now.

Principle 1: Never hard-code secrets in code
Good patterns:
	•	Use environment variables, e.g. os.environ["COINGECKO_API_KEY"]
	•	Or Streamlit secrets (.streamlit/secrets.toml in deployment)

Principle 2: Use app-level keys, not personal keys

For production:
	•	Create dedicated API keys for 21mScot (or the project),
not keys tied to your personal login if you can help it.
	•	Use least privilege & sensible quotas.

So even if a key leaked, it’s:
	•	limited in scope,
	•	revocable,
	•	not bound to your entire personal account.

Principle 3: Never send secrets to the browser

Remember: in a hosted Streamlit app, all Python code runs server-side. That’s good.

Just be careful to:
	•	Don’t expose API keys in:
	•	st.write()
	•	error messages
	•	logs that are user-visible
	•	Don’t include secrets in:
	•	query params
	•	URLs
	•	JSON returned to any front-end JS, if you later add one

The pattern should always be:

Browser → talks to your app backend → backend talks to external APIs using secrets → backend returns data only.

Principle 4: Config separation

Have a clear separation:
	•	config/settings.py – contains names of env vars / switches, not secrets themselves.
	•	Environment / secrets store – contains actual keys.
	•	settings.py might expose things like:
	•	USE_LIVE_DATA: bool
	•	LIVE_DATA_CACHE_TTL_S: int
	•	DEFAULT_DISCOUNT_RATE: float

But never the actual API key strings.

You could describe the app (fetch) like this:

“The app fetches live BTC and network data from public APIs, but we cache that data for a few minutes (TTL) so we’re not hammering providers or exposing you to jitter.
Your data and our API keys never leave the server – the browser only sees processed results.
When we publish this on the web we use dedicated app-level credentials stored in a secure secrets store, not anything personal or hard-coded.
If live data is down, we gracefully fall back to the last good values or to static assumptions, and we’re transparent about that in the UI.”

## 1. User inputs (site-level)

- `site_power_kw` (float): max site electrical capacity.
- `load_factor` (float 0–1): average fraction of power available for mining.
- `power_price_gbp_per_kwh` (float): electricity price in £/kWh.

Derived:
- `effective_power_kw = site_power_kw * load_factor`.

## 2. Miner catalogue

Each `Miner` has:
- `name: str`
- `hashrate_ths: float`
- `power_w: float`
- `price_gbp: float`

Derived:
- `efficiency_j_per_th = power_w / hashrate_ths`
- `power_kw = power_w / 1000`
- `kwh_per_day = power_kw * 24`

## 3. Miner selection

Goal: choose a **default miner** for the site at the given £/kWh.

Steps:

1. For each miner, compute:
   - `cost_per_kwh_per_day = kwh_per_day * power_price_gbp_per_kwh`
   - Given `rev_per_th_per_day_y1` from the scenario engine,
     - `revenue_per_day = hashrate_ths * rev_per_th_per_day_y1`
     - `profit_per_day = revenue_per_day - cost_per_kwh_per_day`
2. Filter out miners with `profit_per_day <= 0` (not viable at this site).
3. Compute simple payback per miner:
   - `simple_payback_days = price_gbp / profit_per_day`
4. Default choice:
   - select the miner with **minimum simple_payback_days**.

This miner is the **“chosen miner”** used for further site and project economics.

## 4. Site build from chosen miner

Given chosen miner and site inputs:

- `effective_power_kw = site_power_kw * load_factor`
- `miner_power_kw = miner.power_w / 1000`
- `n_miners = floor(effective_power_kw / miner_power_kw)`
- `unused_power_kw = effective_power_kw - n_miners * miner_power_kw`

Site-level:

- `site_hashrate_ths = n_miners * miner.hashrate_ths`
- `site_kwh_per_day = n_miners * miner.kwh_per_day`
- `site_power_cost_per_day = site_kwh_per_day * power_price_gbp_per_kwh`
- `capex_miners_gbp = n_miners * miner.price_gbp`

Year-1 economics using scenario engine:

- Scenario engine provides `rev_per_th_per_day_y1` (base case).
- `site_revenue_per_day = site_hashrate_ths * rev_per_th_per_day_y1`
- `site_gross_profit_per_day = site_revenue_per_day - site_power_cost_per_day`.

## 5. Multi-year cashflows

For each scenario (e.g. Base, Bearish, Bullish), scenario engine provides a **path** for revenue-per-TH per day:

- `rev_per_th_per_day(year)` – this should already encode BTC price, difficulty, halvings, fees, etc.

For year `t`:

- `daily_revenue_t = site_hashrate_ths * rev_per_th_per_day(t)`
- `annual_revenue_t = daily_revenue_t * 365`
- `annual_power_cost_t = site_power_cost_per_day * 365`  (or scenario-driven if power price changes)
- `annual_profit_t = annual_revenue_t - annual_power_cost_t`

Cashflows:

- At `t = 0`: `CF_0 = -capex_miners_gbp`
- For `t = 1..T`: `CF_t = annual_profit_t`

## 6. Investment metrics

Given cashflows `[CF_0, CF_1, ..., CF_T]` and discount rate `r` (e.g. 8%):

- **NPV**:
  - `NPV = sum(CF_t / (1 + r)^t for t in 0..T)`
- **IRR**:
  - discount rate such that `NPV = 0` (solve numerically).
- **ROIC**:
  - `ROIC = average(annual_profit_t) / capex_miners_gbp`
- **Simple payback**:
  - cumulative sum of `CF_t` (undiscounted) until it crosses 0; interpolate within that year.
- **Discounted payback**:
  - cumulative sum of `CF_t / (1 + r)^t` until it crosses 0; interpolate.

## 7. UI hooks (for Streamlit)

- “Your site daily performance”:
  - Uses **chosen miner** + `n_miners` + Year-1 economics.
- Expander: “How we chose your miner”:
  - Shows:
    - cost per TH/day vs £/kWh for each miner,
    - breakeven £/kWh,
    - payback vs £/kWh.
- “Scenarios & Risk” tab:
  - Shows:
    - annual cashflows table per scenario,
    - cumulative and discounted cashflow charts,
    - investment metrics table (NPV, IRR, ROIC, payback).

## 8. Alternaitve Investment metrics
- “Other bitcoin plays”:
  - CapEx to BTC price today and ongoing DCA with OpEx to end of project?
  - Blockwaresolutions.com hosted mining with the CapEx.
  - Uses **chosen miner** + `n_miners` + Year-1 economics.
- Other TradFi plays”:
  - Open to suggestions
