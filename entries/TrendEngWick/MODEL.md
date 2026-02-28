# TrendEngWick Model

**BOSSTESTENUMORATOR:** 2
**Magic Number:** 4 (TrendEngWickMagic)
**Status:** Baseline Testing

## Signal Logic

Engulfing candle with wick piercing through EMA cloud, body confirms direction.

### Entry Conditions
- EMA stack aligned in trend direction
- Candle wick pierces through EMA cloud (21/55 zone)
- Body closes in direction of trend (doesn't need to close beyond cloud)
- Engulfing pattern confirms momentum

### Typical Characteristics
- Earlier entries than TrendEng (wick vs body confirmation)
- Slightly lower win rate but better R:R potential
- More aggressive - catches moves earlier
- More false signals in choppy conditions

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

## Comparison vs TrendEng

| Metric | TrendEng | TrendEngWick | Notes |
|--------|----------|--------------|-------|
| Entry Timing | Later | Earlier | Wick vs Body |
| Win Rate | - | - | Pending |
| Avg R:R | - | - | Pending |
| Trade Count | - | - | Pending |

## Notes

-
