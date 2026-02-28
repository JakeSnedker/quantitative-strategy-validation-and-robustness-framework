# TrueShift Model

**BOSSTESTENUMORATOR:** 8
**Magic Number:** 10 (TrueShiftMagic)
**Status:** Baseline Testing

## Signal Logic

TDI cross combined with Yellow/Red line cross - momentum shift confirmation.

### Entry Conditions
- TDI Green line crosses above/below Red line (momentum)
- Yellow line crosses Red line in same direction (confirmation)
- Price action aligns with TDI direction
- Optional: TDI in oversold/overbought zone for reversal trades

### Typical Characteristics
- Momentum-based entry (not structure-based like EMA patterns)
- Can catch both trend continuations AND reversals
- More signals than EMA-cloud entries
- Requires careful stop placement (no natural structure level)

## TDI Components

- **Green Line:** RSI smoothed (momentum)
- **Red Line:** Signal line (trigger)
- **Yellow Line:** Secondary signal
- **Blue Bands:** Bollinger Bands on RSI (volatility)
- **50 Level:** Neutral zone

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

- ATR stop may be more important here (no structure reference)
- May benefit from tighter stops due to momentum nature
- Consider testing with TDI zone filters (>68 overbought, <32 oversold)

## Notes

-
