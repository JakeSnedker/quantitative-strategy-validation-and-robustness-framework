# TrendEng Model

**BOSSTESTENUMORATOR:** 1
**Magic Number:** 3 (TrendEngMagic)
**Status:** Baseline Testing

## Signal Logic

Engulfing candle through EMA cloud in direction of trend.

### Entry Conditions
- EMA stack aligned (bullish: 5 > 13 > 21 > 55, bearish: inverse)
- Price breaks through EMA cloud (21/55 zone)
- Engulfing candlestick pattern confirms direction
- Body of engulfing candle closes beyond cloud

### Typical Characteristics
- Higher probability when cloud is tight
- Works best in trending markets
- False signals common in ranging/choppy conditions

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

## Notes

-
