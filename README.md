# JJC Trading Bot - Automated Futures Scalping System

An automated trading system for scalping US index futures (DOW/NAS100) on the 1-minute timeframe, built for MetaTrader 5 with an LLM-guided optimization framework.

## Overview

This project demonstrates end-to-end quantitative trading system development:

1. **Strategy Development** - MQL5 Expert Advisor with multiple entry patterns
2. **Risk Management** - FTMO prop firm compliant (5% daily loss, 10% max DD)
3. **Automated Optimization** - Python framework using LLM for intelligent parameter tuning
4. **Systematic Testing** - Multi-phase validation to combat overfitting

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         JJC TRADING SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────┐              │
│  │   MQL5 Expert Advisor│         │  Python Optimizer    │              │
│  │   ─────────────────  │         │  ─────────────────   │              │
│  │   • 5 Entry Patterns │◄───────►│  • MT5 Controller    │              │
│  │   • EMA Stack Filter │  .set   │  • Results Parser    │              │
│  │   • TDI Indicator    │  files  │  • LLM Analyzer      │              │
│  │   • ATR-based Stops  │         │  • Optimization Loop │              │
│  │   • Trade Management │         │                      │              │
│  └──────────────────────┘         └──────────────────────┘              │
│           │                                  │                           │
│           ▼                                  ▼                           │
│  ┌──────────────────────┐         ┌──────────────────────┐              │
│  │   MetaTrader 5       │         │   LLM Provider       │              │
│  │   Strategy Tester    │         │   (Claude/GPT/Local) │              │
│  └──────────────────────┘         └──────────────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Trading Strategy

### Entry Patterns

| Pattern | Description | Trigger |
|---------|-------------|---------|
| TrendEng | Engulfing through EMA cloud | Price breaks cloud with engulfing candle |
| TrendEngWick | Engulfing with wick confirmation | Wick pierces cloud, body confirms |
| TrendingGray | 377 EMA bounce | Engulfing off long-term EMA |
| TrueShift | TDI momentum shift | TDI cross + Yellow/Red confirmation |
| TDIBnR | TDI bounce & retest | TDI level test with confirmation |

### Indicators Used

- **EMA Stack**: 5/13/21/55/377/987 for trend structure
- **TDI (Traders Dynamic Index)**: RSI-based momentum with Bollinger Bands
- **ATR**: Dynamic stop loss and take profit calculation
- **Bollinger Bands**: Volatility filter
- **PSAR**: Trend confirmation

### Risk Management

- ATR-based stop loss (configurable multiplier)
- R-multiple take profit targets
- Break-even activation
- Trailing stop options (ATR, PSAR, Chandelier)
- Position sizing for prop firm compliance

## Optimization Framework

The Python optimizer automates the parameter tuning process using LLM intelligence:

```python
from optimizer import run_optimization

# Run LLM-guided optimization
summary = run_optimization(
    entry_type="TrendEng",
    goal="Maximize profit factor while keeping max drawdown below 5%"
)
```

### Features

- **Multi-provider LLM support**: Claude, GPT-4, or local Ollama models
- **Automated backtesting**: MT5 command-line integration
- **Intelligent stopping**: Stagnation detection, target achievement
- **State persistence**: Resume interrupted optimizations
- **Structured analysis**: JSON response parsing for reliability

### Optimization Philosophy

The framework is designed to combat **overfitting** - the primary challenge in algo trading:

1. **Baseline Testing**: Establish raw expectancy without filters
2. **Filter Impact Analysis**: Test each filter's contribution to expectancy (not just win rate)
3. **Trade Management Optimization**: Fine-tune exits after entries are validated
4. **Walk-Forward Validation**: Verify robustness across unseen time periods

## Project Structure

```
JJC BOT V13/
├── optimizer/                    # Python optimization framework
│   ├── config.py                # Configuration management
│   ├── set_file_generator.py    # MT5 .set file creation
│   ├── mt5_controller.py        # MT5 automation
│   ├── results_parser.py        # Backtest result parsing
│   ├── llm_analyzer.py          # LLM integration
│   ├── optimization_loop.py     # Main orchestrator
│   └── README.md                # Optimizer documentation
│
├── optimization_docs/           # Testing methodology
│   ├── PROJECT_CONTEXT.md       # Full project context
│   └── TESTING_LOG.md           # Test tracking
│
└── ARCHITECTURE.md              # System design documentation
```

## Technical Skills Demonstrated

### Quantitative Finance
- Strategy development and backtesting
- Risk-adjusted performance metrics (Profit Factor, Sharpe, Max DD)
- Overfitting identification and mitigation
- Walk-forward analysis methodology

### Software Engineering
- MQL5 Expert Advisor development (~10k lines)
- Python automation and tooling
- Multi-provider API integration (Anthropic, OpenAI, Ollama)
- Command-line automation and process management
- Structured data parsing (XML, HTML)

### System Design
- Modular architecture with clear separation of concerns
- Configuration management with environment variables
- State persistence for long-running processes
- Error handling and graceful degradation

## Quick Start

```bash
# 1. Clone and install dependencies
cd optimizer
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with MT5 path and LLM API key

# 3. Run baseline test
python optimization_loop.py TrendEng --baseline

# 4. Run optimization
python optimization_loop.py TrendEng --goal "Maximize PF, keep DD < 5%"
```

## Performance Targets

| Metric | Target | FTMO Requirement |
|--------|--------|------------------|
| Profit Factor | > 1.5 | N/A |
| Max Daily Drawdown | < 5% | 5% |
| Max Total Drawdown | < 10% | 10% |
| Win Rate | 30-40% | N/A |
| Average R:R | 2:1+ | N/A |

## License

Proprietary - Trading logic not included in public repository.

## Contact

For inquiries about this project or quantitative trading positions, please reach out via GitHub.
