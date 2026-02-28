# TDIBnR Model (TDI Bounce and Retest)

**BOSSTESTENUMORATOR:** 9
**Magic Number:** 11 (TDIBnRMagic)
**Status:** Baseline Testing

## Signal Logic

TDI bounces off a key level (overbought/oversold or 50 line) and retests for confirmation.

### Entry Conditions
- TDI reaches extreme zone OR 50 neutral line
- Initial bounce/rejection from level
- Retest of the level with confirmation
- Entry on successful retest hold

### Typical Characteristics
- Mean-reversion style entry
- Higher win rate potential (trading from extremes)
- Smaller moves but more consistent
- Works well in ranging markets
- Can struggle in strong trends (level breaks)

## TDI Levels

- **68+ Zone:** Overbought - look for shorts
- **32- Zone:** Oversold - look for longs
- **50 Line:** Neutral - trend continuation signals

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

- May benefit from smaller TP targets (mean reversion)
- Consider 1.5:1 R:R instead of 2:1 for higher win rate
- Strong trends will stop this out - trend filter important
- Works best during London/NY overlap (ranging periods)

## Comparison vs TrueShift

| Aspect | TrueShift | TDIBnR |
|--------|-----------|--------|
| Style | Momentum/Breakout | Mean Reversion |
| Win Rate | Lower | Higher |
| R:R Target | 2:1+ | 1.5:1 |
| Best Market | Trending | Ranging |

## Notes

-
