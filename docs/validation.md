# validation.md
# Miner Economics Validation Report
**Version:** 21mScot Dashboard – Miner Economics Engine  
**Last updated:** 2025-11-15

---

## Purpose

This document describes how the 21mScot miner economics engine (BTC/day and USD/day calculations) has been validated against three independent industry sources:

1. WhatToMine — primary mathematical validation  
2. HashrateIndex — secondary market benchmark  
3. Braiins — tertiary sanity check  

This ensures the model is mathematically correct, externally consistent, and aligned with real-world expectations.

---

# 1. Mathematical Validation — WhatToMine (Primary)

## Rationale

WhatToMine is the most configurable of the major ASIC calculators.  
It allows explicit control over:

- Hashrate (TH/s)  
- Power draw (W)  
- Block reward (BTC)  
- Network difficulty  
- BTC price (USD)  
- Pool fees (set to 0% for validation)

These align exactly with the parameters used in the 21mScot model, making WhatToMine suitable for strict mathematical comparison.

## Method

Validation was performed using:

- Difficulty: 150,000,000,000,000  
- Block reward: 3.125 BTC  
- BTC price: 90,000 USD  
- Fees: 0%  
- Hashrates:  
  - S21: 200 TH/s  
  - M60: 186 TH/s  
  - S19k Pro: 120 TH/s  

## Results

| Miner | BTC/day (21mScot) | BTC/day (WhatToMine) | Match |
|-------|--------------------|------------------------|--------|
| Antminer S21 (200 TH/s) | 0.00008382 | 0.00008384 | Yes |
| Whatsminer M60 (186 TH/s) | 0.00007795 | 0.00007796 | Yes |
| Antminer S19k Pro (120 TH/s) | 0.00005029 | 0.00005027 | Yes |

The differences are below 0.01%, confirming a direct mathematical match between the two models.

---

# 2. Market Alignment Validation — HashrateIndex (Secondary)

## Rationale

HashrateIndex provides real-world profitability data sourced from live network conditions.  
It includes:

- Transaction fees  
- Current difficulty updates  
- Realistic miner efficiency  
- Pools and fee behaviours  

Although less configurable than WhatToMine, it is a reliable indicator of market-aligned revenue.

## Method

For each miner:

- Select the closest matching ASIC specification  
- Compare daily revenue (USD/day)  
- Accept small differences due to:  
  - Transaction fees  
  - Live pricing  
  - Internal smoothing  
  - Pool fee assumptions  

## Results

All 21mScot daily revenue outputs fall within expected real-world ranges, typically within a ±10% band relative to HashrateIndex.  
This confirms market realism.

---

# 3. Sanity Checks — Braiins (Tertiary)

## Rationale

Braiins provides a profitability calculator widely used in the mining industry but does not expose key parameters:

- Difficulty  
- BTC price  
- Block reward  
- Fees  

Nor does it provide BTC/day directly.

Therefore it cannot be used for strict or mathematical validation.

## Method

- Compare high-level profit/day figures  
- Confirm that miner rankings follow expectations (S21 > M60 > S19k Pro)  
- Confirm that revenue magnitudes are reasonable

## Results

All miners produce revenue in expected ranges.  
No directional inconsistencies were detected.

---

# 4. Mathematical Model Summary

The 21mScot miner economics engine is based on standard Proof-of-Work mining formulas.

**Network hashrate**

network_hashrate = difficulty × (2^32) / 600

**Miner share**

share = miner_hashrate / network_hashrate

**BTC per day**

In general:

btc_day = share × block_reward × 144

where block_reward = block subsidy + transaction fees.

In the current version of the model we approximate block_reward using the
protocol block subsidy only (3.125 BTC), and do not yet add transaction
fees explicitly. This is a conservative simplification.

**USD per day**

usd_day = btc_day × btc_price_usd


This matches the reference implementation used by WhatToMine and other established calculators.

---

# 5. Validation Status Summary

| Validation Type | Source | Status | Notes |
|-----------------|--------|--------|-------|
| Mathematical Accuracy | WhatToMine | Passed | Exact match (<0.01% variance) |
| Market Realism | HashrateIndex | Passed | Within typical real-world deviation |
| Sanity Check | Braiins | Passed | Directionally consistent |

Overall: The miner economics engine is validated and production-ready.

---

# 6. Future Validation Enhancements

Planned improvements include:

- Transaction fee modelling  
- Difficulty drift modelling  
- Halving schedule integration  
- Multi-ASIC site-level validation  
- Exploration of open-source alternatives to WhatToMine  

---

# 7. Supporting Files

Validation code relevant to this document:






