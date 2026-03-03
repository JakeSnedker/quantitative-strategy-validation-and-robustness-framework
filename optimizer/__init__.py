"""
JJC Bot Optimizer

Automated optimization framework for MT5 Expert Advisors.
Uses LLM-guided parameter optimization with systematic backtesting.
"""

from .config import get_config, reload_config, Config
from .set_file_generator import SetFileGenerator, ENTRY_TYPES, create_test_set_file
from .mt5_controller import MT5Controller
from .results_parser import parse_results, BacktestResults
from .llm_analyzer import OptimizationAnalyzer, OptimizationSuggestion, get_llm_provider
from .optimization_loop import OptimizationLoop, run_optimization, run_baseline_test
from .monte_carlo import MonteCarloSimulator, MonteCarloResult, run_monte_carlo_analysis

__version__ = "1.0.0"
__author__ = "JJC Trading"

__all__ = [
    # Config
    "get_config",
    "reload_config",
    "Config",
    # Set files
    "SetFileGenerator",
    "ENTRY_TYPES",
    "create_test_set_file",
    # MT5 control
    "MT5Controller",
    # Results
    "parse_results",
    "BacktestResults",
    # LLM
    "OptimizationAnalyzer",
    "OptimizationSuggestion",
    "get_llm_provider",
    # Main loop
    "OptimizationLoop",
    "run_optimization",
    "run_baseline_test",
    # Monte Carlo
    "MonteCarloSimulator",
    "MonteCarloResult",
    "run_monte_carlo_analysis",
]
