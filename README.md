# Quantitative Strategy Validation Framework

A production-grade Python framework for **walk-forward optimization** and **Monte Carlo validation** of algorithmic trading strategies. Built to combat overfitting through rigorous out-of-sample testing methodology.

## The Problem

Most algorithmic trading strategies fail in live trading because they are **overfit** to historical data. Traditional backtesting optimizes parameters to maximize past performance, producing strategies that look profitable but have no predictive edge.

**Common overfitting indicators:**
- Parameters that work at 1.47 but fail at 1.3 or 1.5
- Strategies that require different settings for different time periods
- High in-sample performance with poor out-of-sample results

## The Solution

This framework implements **anchored walk-forward analysis** with Monte Carlo validation - the gold standard for strategy robustness testing in quantitative finance.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WALK-FORWARD OPTIMIZATION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Window 1:  [====IN-SAMPLE====][OUT]                                        │
│  Window 2:       [====IN-SAMPLE====][OUT]                                   │
│  Window 3:            [====IN-SAMPLE====][OUT]                              │
│  Window 4:                 [====IN-SAMPLE====][OUT]                         │
│  Window 5:                      [====IN-SAMPLE====][OUT]                    │
│  Window 6:                           [====IN-SAMPLE====][OUT]               │
│                                                                              │
│  IN-SAMPLE:  Optimize parameters (4 months)                                 │
│  OUT-OF-SAMPLE: Validate on unseen data (2 months)                          │
│  SLIDE: 2 months between windows                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key metrics calculated:**
- **Walk-Forward Efficiency (WFE):** Ratio of out-of-sample to in-sample performance
- **Forward Profit Factor:** Out-of-sample profit factor across all windows
- **Monte Carlo P(Ruin):** Probability of account ruin via 10,000 trade sequence simulations
- **Parameter Stability:** Performance variance across adjacent parameter values

## Architecture

### 5-Stage Validation Pipeline

The framework uses a staged approach that tests parameter clusters in logical order, compounding winners at each stage:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: FOUNDATION                                                          │
│ Establish core risk/reward structure (SL/TP methods)                         │
│ Output: BASELINE                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: ENTRY REFINEMENT                                                    │
│ Test 8 filter clusters vs BASELINE                                           │
│ GATE: PF > 1.0 or STOP (no edge found)                                       │
│ Output: ENTRY SYSTEM                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: TIME & CONTEXT                                                      │
│ Session filters, market open behavior, news avoidance                        │
│ Output: TIMED SYSTEM                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: TRADE MANAGEMENT                                                    │
│ Break-even methods (11), trailing stops (15), exit timing                    │
│ Output: MANAGED SYSTEM                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: FINAL VALIDATION                                                    │
│ Monte Carlo simulation, parameter stability, prop firm compliance            │
│ Output: VALIDATED PARAMETERS or "No robust edge found"                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why staged testing matters:**
- Trade management only makes sense on a winning entry system
- Stage gates prevent wasted computation on non-viable strategies
- Logical ordering prevents spurious correlations
- Reduces search space from billions of combinations to ~36 walk-forwards per strategy

## Key Features

### Walk-Forward Optimization
- Configurable in-sample/out-of-sample windows
- Sliding window with customizable step size
- Automatic walk-forward efficiency calculation
- Multi-window aggregation

### Monte Carlo Analysis
- 10,000 trade sequence simulations
- Probability of profit/ruin calculation
- 95% confidence intervals
- Drawdown distribution analysis

### Parameter Stability Testing
- Adjacent parameter profitability verification
- Cross-step variance analysis
- Robustness scoring

### MT5 Automation
- Batch mode optimization via command-line
- Automatic .set file generation (UTF-16 encoded)
- Results parsing from XML/HTML reports
- Clean baseline reset between runs

## Pass/Fail Criteria

| Metric | Minimum | Ideal | Description |
|--------|---------|-------|-------------|
| Forward Profit Factor | > 1.0 | > 1.3 | Out-of-sample profitability |
| Walk-Forward Efficiency | > 50% | > 70% | OOS/IS performance ratio |
| Max Drawdown | < 10% | < 5% | FTMO compliance |
| Trades per Window | >= 20 | >= 40 | Statistical significance |
| Monte Carlo P(Ruin) | < 15% | < 5% | Account survival probability |
| Parameter Stability | Adjacent profitable | +/-1 step profitable | Robustness indicator |

## Usage

### Quick Start

```bash
# Install dependencies
cd optimizer
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with MT5 path

# Run walk-forward optimization
python cli.py walk-forward TrendEng --start-date 2024.07.01 --end-date 2025.12.31

# Run specific stage
python walk_forward_optimizer.py TrendEng --phase 1  # ATR SL baseline
python walk_forward_optimizer.py TrendEng --phase 2  # L_O_TH SL baseline
```

### Programmatic Usage

```python
from walk_forward_config import WalkForwardConfig, WalkForwardSettings, PassFailCriteria
from walk_forward_optimizer import WalkForwardOptimizer

# Configure walk-forward settings
config = WalkForwardConfig(
    entry_type="TrendEng",
    start_date="2024.07.01",
    end_date="2025.12.31",
    walk_forward=WalkForwardSettings(
        optimization_months=4,
        forward_months=2,
        step_months=2,
    ),
    criteria=PassFailCriteria(
        min_forward_profit_factor=1.0,
        max_drawdown_percent=10.0,
        min_walk_forward_efficiency=0.5,
        max_monte_carlo_ruin_probability=0.15,
    ),
)

# Run optimization
optimizer = WalkForwardOptimizer(config)
report = optimizer.run()

# Check results
print(f"Status: {report.status}")
print(f"Forward PF: {report.aggregate_results['combined_forward_pf']:.3f}")
print(f"WFE: {report.aggregate_results['walk_forward_efficiency']:.1%}")
print(f"P(Ruin): {report.monte_carlo_results['probability_of_ruin']:.1%}")
```

## Project Structure

```
quantitative-strategy-validation-framework/
├── optimizer/
│   ├── walk_forward_optimizer.py   # Main WFO engine
│   ├── walk_forward_config.py      # Configuration & criteria
│   ├── mt5_optimization.py         # MT5 batch mode automation
│   ├── monte_carlo.py              # Monte Carlo simulation
│   ├── staged_optimizer.py         # 5-stage pipeline orchestrator
│   ├── cluster_config.py           # Parameter cluster definitions
│   ├── results_parser.py           # MT5 report parsing
│   └── config.py                   # Environment configuration
│
├── entries/                        # Strategy model documentation
│   ├── TrendEng/
│   ├── TrendEngWick/
│   ├── TrendingGray/
│   ├── TrueShift/
│   └── TDIBnR/
│
├── docs/
│   ├── OPTIMIZATION_SYSTEM_V2.md   # Full methodology documentation
│   └── OPTIMIZATION_METHODOLOGY.md # Academic background
│
└── ARCHITECTURE.md                 # System design documentation
```

## Technical Implementation

### Walk-Forward Window Calculation

```python
def calculate_windows(start_date: str, end_date: str) -> List[Dict]:
    """
    Generate sliding optimization windows.

    Example with 4-month IS, 2-month OOS, 2-month step:

    Window 0: Optimize Jul-Oct 2024, Forward Nov-Dec 2024
    Window 1: Optimize Sep-Dec 2024, Forward Jan-Feb 2025
    Window 2: Optimize Nov-Feb 2025, Forward Mar-Apr 2025
    ...
    """
```

### Monte Carlo Simulation

```python
def monte_carlo_analysis(trades: List[float], simulations: int = 10000) -> Dict:
    """
    Shuffle trade sequence to estimate:
    - Probability of profit
    - Probability of ruin (hitting max drawdown)
    - 95% confidence interval for final equity
    - Maximum drawdown distribution
    """
```

### MT5 Batch Integration

```python
def run_optimization(config: WalkForwardConfig) -> OptimizationResult:
    """
    1. Reset .set file to clean baseline
    2. Generate config.ini with optimization parameters
    3. Launch MT5 with /config: flag
    4. Monitor process completion
    5. Parse optimization results
    6. Extract forward test performance
    """
```

## Skills Demonstrated

### Quantitative Finance
- Walk-forward analysis methodology
- Monte Carlo simulation for risk assessment
- Parameter stability and robustness testing
- Overfitting detection and mitigation
- Profit factor, Sharpe ratio, drawdown analysis
- Prop firm compliance (FTMO rules)

### Software Engineering
- Clean architecture with separation of concerns
- Configuration management via dataclasses
- Process automation and monitoring
- Structured data parsing (XML, HTML)
- State persistence for long-running jobs
- UTF-16 file encoding for MT5 compatibility

### System Design
- Staged pipeline with gate checks
- Modular cluster-based testing
- Compound winner architecture
- Resume capability for interrupted runs

## Sample Output

```
============================================================
WALK-FORWARD OPTIMIZATION REPORT: TrendEng
============================================================

Status: PASS
Duration: 32.7 minutes

AGGREGATE RESULTS:
  Windows: 6/6 successful
  Combined Forward PF: 1.342
  Combined Forward Profit: $8,234.50
  Max Forward Drawdown: 4.21%
  Total Forward Trades: 1,680
  Walk-Forward Efficiency: 78.3%

MONTE CARLO RESULTS:
  P(Profit): 94.2%
  P(Ruin): 2.1%
  95% CI: [$4,120.30, $12,890.40]

CRITERIA RESULTS:
  [PASS] forward_profit_factor: 1.342 (min: 1.0)
  [PASS] max_drawdown: 4.21% (max: 10.0%)
  [PASS] trades_per_window: 280 (min: 20)
  [PASS] walk_forward_efficiency: 78.3% (min: 50%)
  [PASS] monte_carlo_ruin: 2.1% (max: 15%)
  [PASS] parameter_stability: Adjacent params profitable

============================================================
```

## References

- Pardo, R. (2008). *The Evaluation and Optimization of Trading Strategies*. Wiley.
- Tomasini, E. & Jaekle, U. (2009). *Trading Systems: A New Approach to System Development*. Harriman House.
- Bailey, D. H., Borwein, J. M., Lopez de Prado, M., & Zhu, Q. J. (2014). "The Probability of Backtest Overfitting." *Journal of Computational Finance*.

## License

MIT License - Framework code is open source.

**Note:** Trading strategy logic (EA source code) is proprietary and not included in this repository.

## Contact

For inquiries about this project or quantitative development positions, please reach out via GitHub.
