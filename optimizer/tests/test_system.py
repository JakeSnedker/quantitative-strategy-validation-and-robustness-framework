"""
System Tests for JJC Bot Optimizer

Run with: python -m pytest tests/ -v
Or standalone: python tests/test_system.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import tempfile
from pathlib import Path

# Test imports
def test_imports():
    """Test all modules can be imported."""
    print("Testing imports...")

    from config import get_config, Config
    from set_file_generator import SetFileGenerator, ENTRY_TYPES
    from mt5_controller import MT5Controller
    from results_parser import parse_results, BacktestResults
    from llm_analyzer import OptimizationAnalyzer, OptimizationSuggestion
    from monte_carlo import MonteCarloSimulator, run_monte_carlo_analysis

    print("  [OK] All imports successful")
    return True


def test_config_loading():
    """Test configuration loading."""
    print("\nTesting config loading...")

    from config import get_config

    config = get_config()

    assert config.mt5.terminal_path, "MT5 terminal path should be set"
    assert config.mt5.ea_name, "EA name should be set"
    assert config.backtest.symbol, "Symbol should be set"

    print(f"  [OK] MT5 Path: {config.mt5.terminal_path[:50]}...")
    print(f"  [OK] EA Name: {config.mt5.ea_name}")
    print(f"  [OK] Symbol: {config.backtest.symbol}")
    print(f"  [OK] LLM Provider: {config.llm.provider}")

    return True


def test_set_file_generation():
    """Test .set file generation."""
    print("\nTesting .set file generation...")

    from set_file_generator import SetFileGenerator, ENTRY_TYPES

    gen = SetFileGenerator()

    # Test baseline config
    gen.create_baseline_config(ENTRY_TYPES["TrendEng"])

    assert gen.params.get("BOSSTESTENUMORATOR") == 1
    assert gen.params.get("BreakEvenMethod") == 0
    assert gen.params.get("TrailMethod") == 0

    print("  [OK] Baseline config created correctly")

    # Test param setting
    gen.set_param("ATRStopLossMultiplier", 2.5)
    assert gen.params.get("ATRStopLossMultiplier") == 2.5

    print("  [OK] Parameter setting works")

    # Test file generation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.set', delete=False) as f:
        temp_path = f.name

    gen.generate(temp_path)

    assert Path(temp_path).exists()
    content = Path(temp_path).read_text()
    assert "BOSSTESTENUMORATOR=1" in content

    print(f"  [OK] .set file generated: {temp_path}")

    # Cleanup
    Path(temp_path).unlink()

    return True


def test_monte_carlo():
    """Test Monte Carlo simulation."""
    print("\nTesting Monte Carlo simulation...")

    from monte_carlo import MonteCarloSimulator, run_monte_carlo_analysis
    import random

    # Create sample trades (40% win rate, 2:1 R:R)
    random.seed(42)
    trades = []
    for _ in range(100):
        if random.random() < 0.40:
            trades.append(random.uniform(150, 250))  # Winners
        else:
            trades.append(random.uniform(-80, -120))  # Losers

    print(f"  Sample trades: {len(trades)}, Total P&L: ${sum(trades):,.2f}")

    # Run shuffle simulation
    sim = MonteCarloSimulator(trades, initial_balance=10000.0, risk_of_ruin_threshold=10.0)
    result = sim.run_shuffle_simulation(num_simulations=1000)

    assert result.num_simulations == 1000
    assert result.num_trades == 100
    assert 0 <= result.probability_of_profit <= 1
    assert 0 <= result.probability_of_ruin <= 1

    print(f"  [OK] Shuffle simulation completed")
    print(f"    P(Profit): {result.probability_of_profit:.1%}")
    print(f"    P(Ruin):   {result.probability_of_ruin:.1%}")
    print(f"    95% CI:    [${result.profit_ci_lower:,.0f}, ${result.profit_ci_upper:,.0f}]")

    # Run bootstrap simulation
    result_bootstrap = sim.run_bootstrap_simulation(num_simulations=1000)
    assert result_bootstrap.num_simulations == 1000

    print(f"  [OK] Bootstrap simulation completed")

    return True


def test_backtest_results_parsing():
    """Test backtest results parsing with mock data."""
    print("\nTesting results parsing...")

    from results_parser import BacktestResults

    # Create mock results
    results = BacktestResults(
        total_trades=100,
        winning_trades=40,
        losing_trades=60,
        win_rate=40.0,
        profit_factor=1.45,
        total_net_profit=2500.0,
        max_drawdown_percent=4.5,
        average_win=180.0,
        average_loss=85.0,
    )

    assert results.total_trades == 100
    assert results.profit_factor == 1.45

    summary = results.to_summary()
    assert "Profit Factor" in summary
    assert "1.45" in summary

    print("  [OK] BacktestResults dataclass works")
    print("  [OK] to_summary() generates output")

    return True


def test_entry_types():
    """Test all entry types are defined."""
    print("\nTesting entry types...")

    from set_file_generator import ENTRY_TYPES

    expected_entries = ["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"]

    for entry in expected_entries:
        assert entry in ENTRY_TYPES, f"Missing entry type: {entry}"
        print(f"  [OK] {entry} = {ENTRY_TYPES[entry]}")

    return True


def test_llm_response_parsing():
    """Test LLM response parsing."""
    print("\nTesting LLM response parsing...")

    from llm_analyzer import parse_llm_response

    # Test valid JSON response
    valid_response = '''
    {
        "reasoning": "Profit factor is below target, suggesting tighter stops",
        "parameter_changes": {"ATRStopLossMultiplier": 1.5},
        "exploration_type": "exploit",
        "confidence": 0.75,
        "should_continue": true,
        "stop_reason": null
    }
    '''

    result = parse_llm_response(valid_response)
    assert result.reasoning == "Profit factor is below target, suggesting tighter stops"
    assert result.parameter_changes.get("ATRStopLossMultiplier") == 1.5
    assert result.confidence == 0.75
    assert result.should_continue == True

    print("  [OK] Valid JSON parsing works")

    # Test JSON in markdown code block
    markdown_response = '''
    Here's my analysis:
    ```json
    {
        "reasoning": "Test from markdown",
        "parameter_changes": {},
        "exploration_type": "explore",
        "confidence": 0.5,
        "should_continue": true
    }
    ```
    '''

    result2 = parse_llm_response(markdown_response)
    assert result2.reasoning == "Test from markdown"

    print("  [OK] Markdown code block parsing works")

    return True


def run_all_tests():
    """Run all system tests."""
    print("=" * 60)
    print("JJC Bot Optimizer - System Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_config_loading,
        test_set_file_generation,
        test_entry_types,
        test_backtest_results_parsing,
        test_llm_response_parsing,
        test_monte_carlo,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
