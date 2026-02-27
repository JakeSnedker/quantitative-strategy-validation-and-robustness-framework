# JJC Bot Optimizer

Automated LLM-guided optimization framework for MT5 Expert Advisors.

## Overview

This framework automates the process of optimizing trading strategy parameters by:

1. **Generating** MT5 .set files with test parameters
2. **Running** backtests via MT5 command-line interface
3. **Parsing** XML/HTML results into structured data
4. **Analyzing** results using LLM (Claude, GPT-4, or local models)
5. **Iterating** based on intelligent suggestions until targets are met

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPTIMIZATION LOOP                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  SetFile     │───►│     MT5      │───►│   Results    │  │
│  │  Generator   │    │  Controller  │    │   Parser     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         ▲                                       │          │
│         │                                       ▼          │
│  ┌──────────────┐                      ┌──────────────┐    │
│  │   Decision   │◄─────────────────────│     LLM      │    │
│  │   Engine     │                      │   Analyzer   │    │
│  └──────────────┘                      └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd optimizer
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings
notepad .env  # or your preferred editor
```

Required settings:
- `MT5_TERMINAL_PATH`: Path to your MT5 terminal folder
- `MT5_DATA_PATH`: Path to MT5 MQL5 data folder
- `LLM_PROVIDER`: Choose `anthropic`, `openai`, or `ollama`
- API key for your chosen provider

### 3. Run Baseline Test

Test a single entry pattern with default settings:

```bash
python optimization_loop.py TrendEng --baseline
```

### 4. Run Optimization

```bash
python optimization_loop.py TrendEng --goal "Maximize profit factor, keep DD < 5%"
```

## Module Reference

### `config.py`
Configuration management with environment variable loading and auto-detection.

```python
from optimizer import get_config

config = get_config()
print(config.mt5.terminal_path)
print(config.llm.provider)
```

### `set_file_generator.py`
Creates and modifies MT5 .set preset files.

```python
from optimizer import SetFileGenerator, ENTRY_TYPES

gen = SetFileGenerator()
gen.create_baseline_config(ENTRY_TYPES["TrendEng"])
gen.set_param("ATRStopLossMultiplier", 1.5)
gen.generate("my_test.set")
```

### `mt5_controller.py`
Controls MT5 terminal for automated backtesting.

```python
from optimizer import MT5Controller

mt5 = MT5Controller()
result = mt5.run_backtest("my_test.set")
if result["success"]:
    print(f"Report: {result['report_path']}")
```

### `results_parser.py`
Parses MT5 XML/HTML reports into structured data.

```python
from optimizer import parse_results

results = parse_results("report.xml")
print(results.to_summary())
print(f"Profit Factor: {results.profit_factor}")
```

### `llm_analyzer.py`
Integrates with LLM APIs for intelligent analysis.

```python
from optimizer import OptimizationAnalyzer

analyzer = OptimizationAnalyzer("Maximize PF, keep DD < 5%")
suggestion = analyzer.analyze(results, current_params)
print(suggestion.reasoning)
print(suggestion.parameter_changes)
```

### `optimization_loop.py`
Main orchestrator that ties everything together.

```python
from optimizer import run_optimization

summary = run_optimization(
    entry_type="TrendEng",
    goal="Maximize profit factor while keeping max drawdown below 5%",
    initial_params={"ATRStopLossMultiplier": 2.0}
)
```

## Entry Types

| Name | BOSSTESTENUMORATOR | Description |
|------|-------------------|-------------|
| TrendEng | 1 | Engulfing through cloud |
| TrendEngWick | 2 | Engulfing with wick through cloud |
| TrendingGray | 5 | Engulfing off 377 EMA |
| TrueShift | 8 | TDI cross + Yellow/Red cross |
| TDIBnR | 9 | TDI Bounce and Retest |

## LLM Providers

### Anthropic (Claude)
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### OpenAI (GPT-4)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4-turbo
```

### Ollama (Local)
```env
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Output Files

Each optimization run creates a directory under `optimization_results/`:

```
run_TrendEng_20240215_143022/
├── optimization_state.json    # Full state (can resume)
├── optimization_summary.json  # Final results
├── best_params.set            # Best parameters found
├── test_0001.set              # Individual test configs
├── test_0002.set
└── ...
```

## Stopping Criteria

The optimization loop stops when:

1. **Max iterations reached** (default: 50)
2. **Targets met** (e.g., PF > 1.5 AND DD < 5%)
3. **LLM recommends stopping** (e.g., results are stable)
4. **Stagnation detected** (no improvement in 5 iterations)

## Tips

### Reduce LLM Token Usage
- Only key metrics are sent to LLM (not individual trades)
- History is compressed to last 5 tests
- Response format is structured JSON

### For Long Backtests
- Set `BACKTEST_TIMEOUT` higher in .env (default: 600s)
- Use `MODELING_MODE=1` (1-minute OHLC) for faster tests during exploration
- Switch to `MODELING_MODE=0` (every tick) for final validation

### Parallel Optimization
For multiple entries, run separate processes:
```bash
python optimization_loop.py TrendEng --goal "..." &
python optimization_loop.py TrendEngWick --goal "..." &
```

## Troubleshooting

### "MT5 is already running"
Close any existing MT5 instances before running optimization.

### "No report file found"
- Check MT5 is installed correctly
- Verify EA is compiled (.ex5 file exists)
- Check `MT5_TERMINAL_PATH` in .env

### LLM parsing errors
- Ensure API key is valid
- Check model name is correct
- For Ollama, ensure server is running

## License

Proprietary - Internal use only.
