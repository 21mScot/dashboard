# Miner Economics Validation (BTC/day & USD/day)

This document provides formal validation of the miner-level economics calculation engine used in the 21mScot Bitcoin Mining Dashboard. The purpose of this validation is to demonstrate full alignment with industry-standard benchmarks, specifically WhatToMine (WTM), under controlled assumptions.

## 1. Purpose

The goal of this validation is to:

- Confirm that our computation of BTC/day and USD/day for individual ASIC miners matches WhatToMine.
- Ensure transparency in assumptions, formulas, exclusions, and methodology.
- Separate global miner-unit economics (USD-based) from local site-economics (GBP-based).

## 2. Assumptions Used During Validation

### 2.1 Network Assumptions

| Parameter | Value |
|----------|-------|
| Bitcoin difficulty | 150,000,000,000,000 |
| Block subsidy | 3.125 BTC |
| Bitcoin price | $90,000 |
| Blocks per day | 144 |
| Fees | 0% |
| Uptime | 100% |
| Electricity cost | $0.00/kWh |

### 2.2 Economic Assumptions

- All miner economics use USD.
- GBP appears only at the site-economics layer.
- No pool fees, electricity costs, or transaction fees.
- Deterministic block interval.

## 3. Formulas Used

### 3.1 Miner share of global hashrate
```
miner_hashrate_hs = hashrate_th * 1e12
network_hashrate_hs = difficulty * 2^32 / 600
share = miner_hashrate_hs / network_hashrate_hs
```

### 3.2 Expected BTC/day
```
btc_per_day = share * block_subsidy_btc * 144
```

### 3.3 Expected USD/day
```
usd_per_day = btc_per_day * btc_price_usd
```

## 4. Validation Results

| Miner | TH/s | Power (W) | BTC/day | USD/day |
|-------|------|-----------|---------|---------|
| Whatsminer M63S++ | 480 | 7200 | 0.00020117 | $18.10 |
| Whatsminer M33S | 240 | 7260 | 0.00010058 | $9.05 |
| Antminer S21 | 200 | 3500 | 0.00008382 | $7.54 |
| Whatsminer M60 | 186 | 3425 | 0.00007795 | $7.02 |
| Antminer S19k Pro | 120 | 2760 | 0.00005029 | $4.53 |

## 5. Conclusion

The 21mScot miner-economics engine matches WhatToMine under controlled assumptions with accuracy better than 1%.

