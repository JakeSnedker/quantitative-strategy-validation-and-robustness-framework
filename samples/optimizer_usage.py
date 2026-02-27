"""
JJC Bot Optimizer - Usage Examples

Demonstrates the Python optimization framework capabilities.
"""

from optimizer import (
    run_optimization,
    run_baseline_test,
    SetFileGenerator,
    ENTRY_TYPES,
    MT5Controller,
    parse_results,
    OptimizationAnalyzer,
    get_config
)


def example_baseline_test():
    """
    Run a baseline test for an entry pattern.

    Baseline tests disable all filters and trade management
    to measure the raw signal quality (pure expectancy).
    """
    print("=" * 60)
    print("BASELINE TEST EXAMPLE")
    print("=" * 60)

    # Run baseline for TrendEng pattern
    results = run_baseline_test("TrendEng")

    if results:
        print("\nBaseline Results:")
        print(results.to_summary())

        # Key insight: Win rate alone doesn't matter
        # What matters is: (Win% * AvgWin) - (Loss% * AvgLoss) > 0
        expectancy = (
            (results.win_rate / 100 * results.average_win) -
            ((100 - results.win_rate) / 100 * results.average_loss)
        )
        print(f"\nExpectancy per trade: ${expectancy:.2f}")
    else:
        print("Baseline test failed")


def example_filter_impact():
    """
    Compare results with and without a specific filter.

    This is how we test whether a filter actually improves
    expectancy, not just win rate.
    """
    print("=" * 60)
    print("FILTER IMPACT ANALYSIS")
    print("=" * 60)

    gen = SetFileGenerator()
    mt5 = MT5Controller()

    # Test 1: Without BB expansion filter
    gen.create_baseline_config(ENTRY_TYPES["TrendEng"])
    gen.set_param("BBexpand", False)
    gen.generate("test_no_bb.set")

    result1 = mt5.run_backtest("test_no_bb.set")
    if result1["success"]:
        results_no_bb = parse_results(result1["report_path"])
        print("\nWithout BB Filter:")
        print(f"  Trades: {results_no_bb.total_trades}")
        print(f"  Win Rate: {results_no_bb.win_rate:.1f}%")
        print(f"  Profit Factor: {results_no_bb.profit_factor:.2f}")

    # Test 2: With BB expansion filter
    gen.set_param("BBexpand", True)
    gen.generate("test_with_bb.set")

    result2 = mt5.run_backtest("test_with_bb.set")
    if result2["success"]:
        results_with_bb = parse_results(result2["report_path"])
        print("\nWith BB Filter:")
        print(f"  Trades: {results_with_bb.total_trades}")
        print(f"  Win Rate: {results_with_bb.win_rate:.1f}%")
        print(f"  Profit Factor: {results_with_bb.profit_factor:.2f}")

        # Compare expectancy, not just win rate
        print("\n--- ANALYSIS ---")
        trade_reduction = (
            (results_no_bb.total_trades - results_with_bb.total_trades) /
            results_no_bb.total_trades * 100
        )
        pf_change = (
            (results_with_bb.profit_factor - results_no_bb.profit_factor) /
            results_no_bb.profit_factor * 100
        )
        print(f"Trade reduction: {trade_reduction:.1f}%")
        print(f"PF change: {pf_change:+.1f}%")

        if pf_change > 0 and pf_change > trade_reduction * 0.5:
            print("Filter IMPROVES expectancy - KEEP")
        else:
            print("Filter REDUCES trades without improving expectancy - REMOVE")


def example_llm_optimization():
    """
    Run LLM-guided optimization.

    The LLM analyzes results and suggests parameter changes,
    balancing exploration (trying new values) with exploitation
    (refining what works).
    """
    print("=" * 60)
    print("LLM-GUIDED OPTIMIZATION")
    print("=" * 60)

    # Define optimization goal
    # Be specific about what you want to optimize for
    goal = """
    Maximize profit factor while keeping:
    - Max drawdown below 5% (FTMO daily limit)
    - Minimum 100 trades for statistical significance
    - Win rate can be 30-40% if R:R is maintained at 2:1+
    """

    # Optional: Start with custom initial parameters
    initial_params = {
        "ATRStopLossMultiplier": 2.0,
        "TakeProfitStopMultiplier": 2.0,
        "BreakEvenMethod": 0,  # Disabled for baseline
        "TrailMethod": 0,      # Disabled for baseline
    }

    # Run optimization
    print(f"\nStarting optimization for TrendEng...")
    print(f"Goal: {goal.strip()}")

    summary = run_optimization(
        entry_type="TrendEng",
        goal=goal,
        initial_params=initial_params
    )

    # Report results
    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"Total iterations: {summary['total_iterations']}")
    print(f"Stop reason: {summary['stop_reason']}")

    if summary['best_result']:
        print(f"\nBest Result (Iteration {summary['best_iteration']}):")
        print(f"  Profit Factor: {summary['best_result']['profit_factor']:.2f}")
        print(f"  Win Rate: {summary['best_result']['win_rate']:.1f}%")
        print(f"  Max Drawdown: {summary['best_result']['max_drawdown_percent']:.1f}%")
        print(f"  Total Trades: {summary['best_result']['total_trades']}")

        print("\nBest Parameters:")
        for key, value in summary['best_params'].items():
            if key in ['ATRStopLossMultiplier', 'TakeProfitStopMultiplier',
                      'BreakEvenMethod', 'TrailMethod']:
                print(f"  {key}: {value}")

        if summary['improvement']:
            pf_improvement = summary['improvement']['profit_factor']
            print(f"\nImprovement: {pf_improvement['initial']:.2f} -> "
                  f"{pf_improvement['final']:.2f} "
                  f"({pf_improvement['change_percent']:+.1f}%)")


def example_manual_analysis():
    """
    Use the LLM analyzer for manual analysis of results.

    Useful when you want to understand why results are
    what they are, or get suggestions without full automation.
    """
    print("=" * 60)
    print("MANUAL LLM ANALYSIS")
    print("=" * 60)

    # Create analyzer with goal
    analyzer = OptimizationAnalyzer(
        goal="Maximize profit factor while keeping drawdown below 5%"
    )

    # Run a backtest
    gen = SetFileGenerator()
    gen.create_baseline_config(ENTRY_TYPES["TrendEng"])
    gen.set_param("ATRStopLossMultiplier", 1.5)
    gen.generate("manual_test.set")

    mt5 = MT5Controller()
    result = mt5.run_backtest("manual_test.set")

    if result["success"]:
        results = parse_results(result["report_path"])
        print("\nCurrent Results:")
        print(results.to_summary())

        # Get LLM analysis
        current_params = {
            "ATRStopLossMultiplier": 1.5,
            "TakeProfitStopMultiplier": 2.0,
            "BreakEvenMethod": 0,
        }

        print("\nAsking LLM for analysis...")
        suggestion = analyzer.analyze(results, current_params)

        print(f"\nLLM Reasoning:")
        print(f"  {suggestion.reasoning}")
        print(f"\nSuggested Changes:")
        for param, value in suggestion.parameter_changes.items():
            print(f"  {param}: {value}")
        print(f"\nConfidence: {suggestion.confidence:.1%}")
        print(f"Exploration Type: {suggestion.exploration_type}")
        print(f"Continue Optimizing: {suggestion.should_continue}")


def example_custom_workflow():
    """
    Build a custom optimization workflow.

    For advanced users who want fine-grained control
    over the optimization process.
    """
    print("=" * 60)
    print("CUSTOM WORKFLOW EXAMPLE")
    print("=" * 60)

    config = get_config()
    gen = SetFileGenerator()
    mt5 = MT5Controller(config.mt5)

    # Define parameter ranges to test
    atr_multipliers = [1.0, 1.5, 2.0, 2.5, 3.0]
    results_table = []

    for atr_mult in atr_multipliers:
        # Generate config
        gen.create_baseline_config(ENTRY_TYPES["TrendEng"])
        gen.set_param("ATRStopLossMultiplier", atr_mult)
        gen.generate(f"sweep_atr_{atr_mult}.set")

        # Run backtest
        result = mt5.run_backtest(f"sweep_atr_{atr_mult}.set")

        if result["success"]:
            r = parse_results(result["report_path"])
            results_table.append({
                "atr_mult": atr_mult,
                "trades": r.total_trades,
                "win_rate": r.win_rate,
                "profit_factor": r.profit_factor,
                "max_dd": r.max_drawdown_percent
            })
            print(f"ATR {atr_mult}: PF={r.profit_factor:.2f}, DD={r.max_drawdown_percent:.1f}%")

    # Find optimal (maximize PF where DD < 5%)
    valid_results = [r for r in results_table if r["max_dd"] < 5.0]
    if valid_results:
        best = max(valid_results, key=lambda x: x["profit_factor"])
        print(f"\nOptimal ATR Multiplier: {best['atr_mult']}")
        print(f"  Profit Factor: {best['profit_factor']:.2f}")
        print(f"  Max Drawdown: {best['max_dd']:.1f}%")


if __name__ == "__main__":
    import sys

    examples = {
        "baseline": example_baseline_test,
        "filter": example_filter_impact,
        "optimize": example_llm_optimization,
        "analyze": example_manual_analysis,
        "sweep": example_custom_workflow,
    }

    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("JJC Bot Optimizer - Usage Examples")
        print("=" * 40)
        print("\nAvailable examples:")
        print("  python optimizer_usage.py baseline  - Run baseline test")
        print("  python optimizer_usage.py filter    - Filter impact analysis")
        print("  python optimizer_usage.py optimize  - LLM-guided optimization")
        print("  python optimizer_usage.py analyze   - Manual LLM analysis")
        print("  python optimizer_usage.py sweep     - Parameter sweep")
        print("\nOr import and use functions directly:")
        print("  from samples.optimizer_usage import example_baseline_test")
