# TrendingGray Model

**BOSSTESTENUMORATOR:** 5
**Magic Number:** 7 (TrendingGrayMagic)
**Status:** Baseline Testing

## Signal Logic

Engulfing candle off the 377 EMA (long-term trend support/resistance).

### Entry Conditions
- Price pulls back to 377 EMA
- 377 EMA is sloping in trend direction
- Engulfing candle forms off 377 EMA
- Shorter EMAs still stacked in trend direction

### Typical Characteristics
- Higher timeframe confluence (377 EMA = ~6hr trend on M1)
- Fewer signals but higher probability
- Better for trending days, poor in range-bound markets
- Natural stop loss level (beyond 377 EMA)

## Current Best Parameters

```
ATRStopLossMultiplier = [pending baseline]
TakeProfitStopMultiplier = [pending baseline]
BreakEvenMethod = [pending optimization]
TrailMethod = [pending optimization]
```

## Optimization History

| Date | Phase | PF | Win% | DD% | Trades | Notes |
|------|-------|-----|------|-----|--------|-------|
| - | Baseline | - | - | - | - | Pending |

## Filter Impact Analysis

| Filter | Trades Before | Trades After | PF Before | PF After | Verdict |
|--------|---------------|--------------|-----------|----------|---------|
| BBexpand | - | - | - | - | Pending |
| CheckRoom | - | - | - | - | Pending |
| TrendMethod | - | - | - | - | Pending |
| Tradescore | - | - | - | - | Pending |

## Special Considerations

- 377 EMA touch detection tolerance may need tuning
- Works best when price hasn't touched 377 in a while (fresh level)
- May benefit from higher R:R targets due to lower frequency

## Notes

-
