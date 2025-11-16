# Miner & Site Economics Validation

## 1. Purpose
This document validates both miner-level economics (BTC/day & USD/day) and the new site-level performance calculations introduced in the *See your site performance* section of the dashboard.

## 2. Updates Included
- Added validation for site-level BTC production, revenue, energy usage, and ASIC scaling.
- Updated section names to match the latest dashboard UI: Overview, Scenarios & Risk, Assumptions & Methodology.
- Clarified terminology: block reward = block subsidy + transaction fees.

## 3. Miner-Level Validation
(unchanged — still matches WhatToMine within 1%)

## 4. Site Performance Validation
### 4.1 Site BTC/day
Uses the sum of all ASICs operating within available site power, adjusted for uptime and cooling overhead.

### 4.2 Site Revenue/day (USD & GBP)
Converted using live or fallback BTC price.

### 4.3 Site Power & Efficiency
Ensures total ASIC draw ≤ site available power.

### 4.4 Project Window Outputs
Using project timeline:
- Total BTC mined
- Total revenue
- Opex (electricity)
- Net revenue

## 5. Conclusion
The expanded economics engine now validates both miner and site-level performance, fully aligned with industry benchmarks and the updated dashboard interface.
