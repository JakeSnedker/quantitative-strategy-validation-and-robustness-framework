# JJC BOT V13 - Optimization Project Context

**Last Updated:** 2026-02-06
**Status:** Phase 1 - Baseline Testing

---

## Project Overview

**Goal:** Systematically optimize JJC BOT V13.3 to achieve consistently profitable results that adhere to FTMO prop firm trading rules.

**Instruments:** NAS100, US30 (DOW) - Primary testing on DOW
**Timeframe:** M1 (1-minute scalping)
**Target:** FTMO Challenge compliance (5% daily loss limit, 10% max drawdown)

---

## Bot Summary

### Active Entry Patterns (5 total)
| Entry | Magic Number | BOSSTESTENUMORATOR Value | Description |
|-------|--------------|--------------------------|-------------|
| TrendEng | 3 | 1 | Engulfing through cloud, basic |
| TrendEngWick | 4 | 2 | Engulfing with wick through cloud |
| TrendingGray | 12 | 5 | Engulfing off 377 EMA |
| TrueShift | 15 | 8 | TDI cross + Yellow/Red cross |
| TDI BnR | 16 | 9 | TDI Bounce and Retest |

### Key Indicators Used
- EMA Stack: 5 (Yellow), 13 (Red), 21 (Cloud Fast), 55 (Cloud Slow/Aqua), 377 (Gray), 987 (Blue)
- TDI: Traders Dynamic Index (RSI smoothed with bands)
- Bollinger Bands: 34 period, 2 StdDev
- PSAR: Default settings
- ATR: Currently 50 period (recommend testing 14)

---

## Current Problem Statement

1. **Overfitting:** Settings optimized for one period don't work on others (3mo vs 6mo vs 2yr)
2. **Low Win Rate:** 30-40% across entries
3. **Too Many Variables:** 25+ parameters per entry creating optimization complexity
4. **Unclear Filter Value:** Unknown which filters (BBexpand, Tradescore, angles, etc.) actually improve expectancy vs just reduce trades
5. **Trade Management Inconsistency:** Trail/BE results are "hit or miss"

---

## Key Insight from Analysis

**The 30-40% win rate is NOT the core problem.**

Adding more entry filters to increase win rate is likely counterproductive because:
- Filters reduce trade frequency
- May filter out winners AND losers equally
- Each filter adds overfitting risk

**Hypothesis:** The edge exists in the raw engulfing-through-cloud pattern. Filters and trade management need to be tested for actual expectancy improvement, not just win rate improvement.

---

## Optimization Philosophy

### Principles
1. **If a setting needs optimization, question if it's necessary**
2. **Fewer filters = More robust**
3. **Dynamic (ATR-based) > Fixed point values**
4. **Test for expectancy improvement, not just win rate**
5. **Settings should work at neighboring values (parameter stability)**

### Filter Evaluation Criteria
A filter is worth keeping ONLY if:
- Expectancy improves (not just win rate)
- Results are stable across multiple time periods
- Parameter values show stability (works at 1.3, 1.5, AND 1.7, not just 1.47)

---

## Testing Plan

### Phase 1: Baseline Testing (CURRENT)
Establish raw edge for each entry WITHOUT filters or trade management.

**Settings for Baseline:**
```
BOSSTESTENUMORATOR = [1, 2, 5, 8, 9] (test each separately)
BreakEvenMethod = 0 (No BE)
TrailMethod = 0 (No Trail)
TakeProfitMethod = 3 (SL Multiplied)
TakeProfitStopMultiplier = 2
CheckRoom = false
AngleOf13 = false
AngleOf21 = false
AngleOf55 = false
AngleOfL50 = false
AngleOfFastRSI = false
BBexpand = false
UsePSAR = false
UseCloudColor = false
UseBBLine = false
Tradescore = 0
TrendMethod = 0 (None)
```

**Data to Collect:**
- Total trades
- Win rate
- Profit factor
- Net P/L
- Max drawdown
- Average win (in R)
- Average loss (in R)
- Largest win / Largest loss

### Phase 2: Filter Impact Testing
Add ONE filter at a time to baseline, measure impact.

**Filters to Test (in order):**
1. TrendMethod (HTF confirmation) - values 1, 2, 3, 4
2. BBexpand (Bollinger expanding)
3. Tradescore / BuyCount threshold - values 1, 2, 3
4. Angle filters (test as group on/off)
5. UsePSAR
6. UseCloudColor
7. UseBBLine
8. CheckRoom with different RewardMultiplierForRoom values

### Phase 3: Trade Management Optimization
With best entry filter combination, test trade management.

**Variables to Test:**
1. Stop Loss: ATRStopLossMultiplier (1.0, 1.5, 2.0, 2.5)
2. Stop Loss: ATRPeriod (14, 21, 50)
3. Take Profit: TakeProfitStopMultiplier (1.5, 2, 2.5, 3)
4. Break Even: Method (0, 1, 5, 6, 10)
5. Break Even: Points in profit before BE
6. Trail: Method (0, 1, 3, 9, 10, 12)
7. Trail: ATRTrailMultiplier

### Phase 4: Robustness Validation
Test final settings across multiple time periods:
- 3 months (recent)
- 6 months
- 12 months
- 2 years (if data available)

Settings that work across ALL periods are kept. Settings that only work on some periods are discarded.

### Phase 5: Per-Entry Hardcoding
Hardcode optimal values into Predifenedsettings() for each magic number.

---

## Results Tracking

### Folder Structure
```
JJC BOT V13/
├── backtest_results/
│   ├── phase1_baseline/
│   ├── phase2_filters/
│   ├── phase3_trade_management/
│   └── phase4_validation/
├── optimization_docs/
│   ├── PROJECT_CONTEXT.md (this file)
│   └── TESTING_LOG.md
└── JJC_Bot-V13.3 (OTN Added).mq5
```

### Excel Template Columns
For each backtest, record:
- Test ID
- Date Range
- Entry Type (Magic#)
- Settings Changed
- Total Trades
- Wins / Losses
- Win Rate %
- Gross Profit
- Gross Loss
- Net Profit
- Profit Factor
- Max Drawdown %
- Avg Win (R)
- Avg Loss (R)
- Expectancy per trade
- Notes

---

## Current Status

**Phase:** 1 - Baseline Testing
**Next Action:** Run baseline test for TrendEng (BOSSTESTENUMORATOR = 1) on DOW M1, 6 months data

---

## Session Notes

### 2026-02-06 - Initial Analysis Session
- Reviewed full bot code (~10,000 lines)
- Identified 5 active entry patterns
- Diagnosed overfitting as core problem
- Established that 30-40% win rate is acceptable if R:R is managed
- Agreed to systematic strip-back approach
- Created testing plan framework
- User will run baseline tests and store results in Excel

---

## Questions to Resolve

1. What time window is being traded? (London, NY, full session?)
2. Distribution of wins - how many 1R, 2R, 3R+ winners?
3. What % of trades get stopped at BE vs full stop vs TP?
4. Current trade frequency (trades per day/week)?

---

## FTMO Compliance Checklist

- [x] Max Daily Loss: 4% (set in bot, under 5% limit)
- [ ] Max Total Drawdown: NOT IMPLEMENTED (need to add)
- [x] News Filter: Implemented (3 min buffer, recommend 10)
- [x] Weekend Close: CloseAllTradesAtTime enabled
- [ ] Consistency Rules: Not tracked
- [ ] Lot Size Consistency: Not enforced
