# Entry Models

Each entry pattern is treated as an independent trading model with its own optimization lifecycle.

## Model Overview

| Entry | Type | Style | Expected Win Rate | Target R:R |
|-------|------|-------|-------------------|------------|
| [TrendEng](./TrendEng/) | EMA Cloud | Breakout | 35-45% | 2.0:1 |
| [TrendEngWick](./TrendEngWick/) | EMA Cloud | Early Breakout | 30-40% | 2.5:1 |
| [TrendingGray](./TrendingGray/) | 377 EMA | Pullback | 40-50% | 2.0:1 |
| [TrueShift](./TrueShift/) | TDI | Momentum | 30-45% | 2.0:1 |
| [TDIBnR](./TDIBnR/) | TDI | Mean Reversion | 45-55% | 1.5:1 |

## Model Classification

### Structure-Based Entries
- **TrendEng** - Price breaks through EMA cloud with engulfing confirmation
- **TrendEngWick** - Wick pierces cloud, earlier entry than TrendEng
- **TrendingGray** - Bounce off 377 EMA (long-term trend support)

### Momentum-Based Entries
- **TrueShift** - TDI cross signals momentum shift
- **TDIBnR** - TDI bounce and retest from extremes

## Optimization Philosophy

Each model is optimized independently following a 4-phase process:

```
Phase 1: Baseline Test
├── All filters OFF
├── No trade management (BE/Trail)
├── Fixed 2:1 R:R
└── Goal: Measure raw signal quality

Phase 2: Filter Impact Analysis
├── Test each filter individually
├── Measure: Trades reduced vs PF improvement
└── Keep only filters that improve EXPECTANCY

Phase 3: Trade Management
├── Test break-even methods
├── Test trailing stop methods
└── Optimize for risk-adjusted returns

Phase 4: Walk-Forward Validation
├── Test on unseen time periods
├── Verify parameter stability
└── Confirm no overfitting
```

## File Structure

Each entry folder contains:

```
EntryName/
├── MODEL.md        # Strategy documentation
├── config.json     # Parameters and targets
├── results/        # Backtest results (gitignored)
└── optimization/   # Optimization run outputs (gitignored)
```

## Cross-Entry Analysis (Future)

Once individual models are optimized:
- Correlation analysis between entries
- Portfolio-level position sizing
- Entry conflict resolution rules
- Combined equity curve analysis
