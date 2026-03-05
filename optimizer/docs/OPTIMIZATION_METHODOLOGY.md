# JJC Bot Optimization Methodology

## Overview

This document defines the automated optimization framework for the JJC Bot trading system. The goal is to find **robust parameters** that demonstrate genuine edge, not curve-fitted results.

---

## Chosen Method: Walk-Forward Optimization

### Why Walk-Forward?

We evaluated four approaches:

| Method | Description | Verdict |
|--------|-------------|---------|
| **Method 1** | Multiple forward-tested optimizations, cross-reference params | Good, but requires manual comparison |
| **Method 2** | Iterate on single period until good, then validate | **REJECTED** - Classic overfitting trap |
| **Method 3** | Optimize without forward, cross-reference, then forward test | Risky - finds params good at fitting, not generalizing |
| **Method 4** | Walk-Forward Optimization | **SELECTED** - Gold standard for automation |

### Walk-Forward Optimization Explained

Walk-forward tests whether the **optimization process itself** consistently produces profitable out-of-sample results.

```
Data: 12 months of price data

Window 1: [Optimize: Month 1-4 ] → [Test: Month 5-6 ] → Record OOS
Window 2: [Optimize: Month 3-6 ] → [Test: Month 7-8 ] → Record OOS
Window 3: [Optimize: Month 5-8 ] → [Test: Month 9-10] → Record OOS
Window 4: [Optimize: Month 7-10] → [Test: Month 11-12] → Record OOS

Result: 8 months of pure out-of-sample performance
```

**Key insight:** If the combined OOS equity curve is profitable, the strategy has demonstrated edge. If not, no amount of parameter tweaking will create real edge.

### Why Not Method 2?

Method 2 ("iterate until good results") is dangerous because:

1. Each iteration implicitly uses forward test data as feedback
2. By iteration N, you've seen forward data N times through parameter choices
3. You're fitting to your own iteration history, not finding real edge
4. The walk-forward at the end validates your overfitting, not robustness

---

## Pass/Fail Criteria

Parameters must meet ALL criteria to pass.

### Primary Criteria (Hard Requirements)

| Metric | Minimum | Ideal | Reasoning |
|--------|---------|-------|-----------|
| **Forward Profit Factor** | > 1.0 | > 1.3 | Must be profitable out-of-sample |
| **Max Drawdown** | < 10% | < 5% | FTMO compliance (5% daily, 10% max) |
| **Trade Count (per window)** | >= 20 | >= 40 | Statistical significance |
| **Walk-Forward Efficiency** | > 0.5 | > 0.7 | OOS performance / In-sample performance |

### Secondary Criteria (Quality Indicators)

| Metric | Minimum | Ideal | Reasoning |
|--------|---------|-------|-----------|
| **Win Rate** | > 25% | > 35% | Sanity check for momentum strategies |
| **Monte Carlo P(Ruin)** | < 15% | < 5% | Survival probability at 10% drawdown |
| **Sharpe Ratio** | > 0.5 | > 1.0 | Risk-adjusted returns |
| **Recovery Factor** | > 1.0 | > 2.0 | Profit relative to max drawdown |

### Parameter Stability Criteria

| Test | Requirement | Reasoning |
|------|-------------|-----------|
| **Adjacent Values** | Params at +/- 1 step must also be profitable | Not on cliff edge |
| **Consistency** | Same params should win in >50% of walk-forward windows | Not regime-dependent noise |
| **Range Sensitivity** | PF variance < 30% across +/- 2 steps | Smooth optimization surface |

---

## Optimization Configuration

### Walk-Forward Settings

```python
WALK_FORWARD_CONFIG = {
    # Window sizes
    "optimization_months": 4,      # In-sample optimization period
    "forward_months": 2,           # Out-of-sample test period
    "step_months": 2,              # How far to slide window each iteration

    # Data range
    "total_data_months": 18,       # Minimum data required

    # This produces approximately:
    # - 6-7 walk-forward windows
    # - 12-14 months of OOS data
}
```

### Optimization Parameters by Entry Type

Each entry type is treated as a separate model with its own optimization cycle.

| Entry Type | BOSSTESTENUMORATOR | Magic Number |
|------------|-------------------|--------------|
| TrendEng | 1 | 3 |
| TrendEngWick | 2 | 4 |
| TrendingGray | 5 | 7 |
| TrueShift | 8 | 10 |
| TDIBnR | 9 | 11 |

### Parameters to Optimize

**Core Risk/Reward Parameters:**
```python
OPTIMIZATION_PARAMS = {
    "ATRStopLossMultiplier": {
        "start": 1.0,
        "stop": 3.5,
        "step": 0.5,
        "description": "ATR multiplier for stop loss distance"
    },
    "TakeProfitStopMultiplier": {
        "start": 1.5,
        "stop": 4.0,
        "step": 0.5,
        "description": "R:R multiplier (TP = SL * this value)"
    },
    "ATRTrailMultiplier": {
        "start": 1.0,
        "stop": 2.5,
        "step": 0.5,
        "description": "ATR multiplier for trailing stop"
    },
}
```

**Filter Parameters (Phase 2):**
Only optimize filters AFTER core R:R parameters are validated.
```python
FILTER_PARAMS = {
    "TrailMethod": [0, 1, 2],           # Trailing stop method
    "BreakEvenMethod": [0, 1, 2],       # Break-even method
    "TrendMethod": [0, 1, 2],           # Trend filter method
    # Add more as needed
}
```

---

## Automated Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    WALK-FORWARD OPTIMIZER                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT: Entry Type, Parameter Ranges, Date Range                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 1: Generate Walk-Forward Windows                     │   │
│  │   - Calculate optimization/forward periods                │   │
│  │   - Create window schedule                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 2: For Each Window                                   │   │
│  │   - Run MT5 optimization (genetic algorithm)              │   │
│  │   - Use forward testing mode                              │   │
│  │   - Record best params and forward performance            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 3: Aggregate Results                                 │   │
│  │   - Combine all OOS equity curves                         │   │
│  │   - Calculate walk-forward efficiency                     │   │
│  │   - Identify most consistent params                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 4: Validation                                        │   │
│  │   - Check pass/fail criteria                              │   │
│  │   - Run Monte Carlo on combined trades                    │   │
│  │   - Test parameter stability                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ STEP 5: Report Generation                                 │   │
│  │   - Pass/Fail determination                               │   │
│  │   - Recommended parameters (if passed)                    │   │
│  │   - Detailed metrics and visualizations                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  OUTPUT: Optimization Report, Validated Parameters (or FAIL)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Walk-Forward Efficiency (WFE)

The key metric for determining if an optimization is "real" vs curve-fitted.

```
WFE = (Out-of-Sample Performance) / (In-Sample Performance)

Example:
  In-sample PF: 1.8
  Out-of-sample PF: 1.2
  WFE = 1.2 / 1.8 = 0.67 (67%)

Interpretation:
  WFE > 0.7  → Excellent, minimal degradation
  WFE 0.5-0.7 → Good, acceptable degradation
  WFE 0.3-0.5 → Marginal, some curve-fitting present
  WFE < 0.3  → Poor, likely overfit
```

---

## FTMO Compliance Requirements

All optimizations must respect prop firm constraints:

| Constraint | Limit | Implementation |
|------------|-------|----------------|
| Daily Loss Limit | 5% | MaxDailyLossPercent = 4% (buffer) |
| Max Drawdown | 10% | Target DD < 8% in optimization |
| Profit Target | 10% | Not enforced in optimization |
| Min Trading Days | 4 | Ensure sufficient trade distribution |

---

## Anti-Overfitting Safeguards

1. **No iteration on results** - Run once, accept outcome
2. **Forward testing always on** - Never optimize without OOS validation
3. **Minimum trade count** - Reject results with < 20 trades per window
4. **Parameter stability required** - Adjacent values must also work
5. **Multiple windows** - Single good window is insufficient
6. **WFE threshold** - Reject if degradation > 50%

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-04 | Initial methodology document |

