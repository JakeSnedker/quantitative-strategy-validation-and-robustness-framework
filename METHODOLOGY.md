# Research Methodology

This document outlines the quantitative approach used for strategy development, testing, and validation.

## The Overfitting Problem

The primary challenge in algorithmic trading is **overfitting** - finding parameters that perform well on historical data but fail on live markets.

### Common Overfitting Patterns

```
❌ Settings that only work on specific date ranges
❌ Parameters that require frequent re-optimization
❌ High sensitivity to small parameter changes
❌ Exceptional backtest results that don't replicate
```

### Our Approach

```
✓ Test each component in isolation before combining
✓ Measure filter impact on EXPECTANCY, not just win rate
✓ Validate on multiple time periods
✓ Require parameter stability (not knife-edge optimization)
```

## Statistical Framework

### Expectancy Calculation

```
E = (Win% × Avg_Win) - (Loss% × Avg_Loss)

Where:
- E > 0 required for profitable system
- Higher E = more robust edge
```

### Minimum Sample Size

For statistical significance at 95% confidence:

| Win Rate | Min Trades Required |
|----------|---------------------|
| 30% | ~150 trades |
| 40% | ~100 trades |
| 50% | ~80 trades |

*We target minimum 100 trades per test period.*

### Key Metrics

| Metric | Target | FTMO Limit | Purpose |
|--------|--------|------------|---------|
| Profit Factor | > 1.5 | N/A | Edge strength |
| Max Drawdown | < 5% | 5% daily | Risk control |
| Win Rate | 30-50% | N/A | Informational |
| Avg R:R | > 2.0 | N/A | Reward per unit risk |
| Sharpe Ratio | > 1.0 | N/A | Risk-adjusted returns |
| Recovery Factor | > 3.0 | N/A | Profit / Max DD |

## Testing Protocol

### Phase 1: Baseline Testing

**Objective:** Measure raw signal quality without enhancements.

```python
baseline_config = {
    "filters": "ALL_OFF",
    "break_even": "DISABLED",
    "trailing": "DISABLED",
    "take_profit": "2x_STOP_LOSS",
    "stop_loss": "2x_ATR"
}
```

**Success Criteria:**
- Profit Factor > 1.0 (proves basic edge exists)
- Sufficient trade count (>100)
- Drawdown within tolerance

### Phase 2: Filter Impact Analysis

**Objective:** Determine which filters improve expectancy.

For each filter:
1. Run backtest WITH filter
2. Compare to baseline:
   - Trade reduction %
   - Profit factor change %
   - Expectancy change

**Decision Matrix:**

| PF Change | Trade Reduction | Action |
|-----------|-----------------|--------|
| +10% | -20% | KEEP (improves efficiency) |
| +5% | -30% | TEST FURTHER |
| 0% | -25% | REMOVE (reduces trades only) |
| -5% | -10% | REMOVE (hurts performance) |

### Phase 3: Trade Management

**Objective:** Optimize exit strategy.

Test matrix:
```
Break-Even Methods: [None, ATR-based, Fixed points, R-multiple]
Trailing Methods: [None, ATR trail, PSAR, Chandelier]
```

**Key Insight:** Trade management cannot create edge - it can only preserve or reduce it. If baseline has no edge, no amount of trail/BE optimization will fix it.

### Phase 4: Walk-Forward Validation

**Objective:** Confirm parameters generalize to unseen data.

```
Training Period:    2024-01 to 2024-06 (6 months)
Validation Period:  2024-07 to 2024-12 (6 months)
Out-of-Sample:      2023-01 to 2023-12 (12 months)
```

**Validation Criteria:**
- Performance degradation < 30% from training
- Same parameters work (no re-optimization)
- Drawdown stays within limits

### Parameter Stability Test

Good parameters work across a range, not just at exact values:

```
If optimal ATR_Multiplier = 1.5:
  - Test at 1.3 → Should still be profitable
  - Test at 1.7 → Should still be profitable

If profitable ONLY at 1.5 → Likely overfit
```

## Risk Management Framework

### Position Sizing

```python
def calculate_position_size(account_balance, risk_percent, stop_loss_points):
    risk_amount = account_balance * (risk_percent / 100)
    position_size = risk_amount / stop_loss_points
    return position_size
```

### FTMO Compliance

| Rule | Limit | Our Target | Buffer |
|------|-------|------------|--------|
| Daily Loss | 5% | 3% | 2% |
| Max Drawdown | 10% | 6% | 4% |
| Min Trading Days | 4 | 10+ | 6+ |

### Correlation Management

When running multiple entry patterns:
- Track correlation between entries
- Reduce position size when entries align
- Avoid compounding risk in same direction

## Reporting Standards

### Required Metrics Per Test

```json
{
  "test_period": "2024-01-01 to 2024-06-30",
  "symbol": "US30",
  "timeframe": "M1",
  "total_trades": 142,
  "winning_trades": 52,
  "losing_trades": 90,
  "win_rate": 36.6,
  "profit_factor": 1.45,
  "total_profit": 4250.00,
  "max_drawdown_percent": 4.2,
  "max_drawdown_absolute": 2100.00,
  "average_win": 185.50,
  "average_loss": 78.25,
  "largest_win": 520.00,
  "largest_loss": 245.00,
  "avg_trade_duration_minutes": 45,
  "sharpe_ratio": 1.2,
  "recovery_factor": 2.02
}
```

### Visual Requirements

Each optimization run should include:
1. Equity curve chart
2. Drawdown chart
3. Monthly returns heatmap
4. Trade distribution by hour/day

## Known Limitations

1. **Backtesting ≠ Live Trading**
   - Slippage not fully modeled
   - Spread variations
   - Execution delays

2. **Market Regime Changes**
   - Parameters optimized for trending markets may fail in ranging
   - Requires ongoing monitoring

3. **Data Quality**
   - M1 data quality varies by broker
   - Gaps and errors possible

## Future Enhancements

- [ ] Monte Carlo simulation for confidence intervals
- [ ] Machine learning for regime detection
- [ ] Automated walk-forward optimization
- [ ] Real-time performance monitoring dashboard
