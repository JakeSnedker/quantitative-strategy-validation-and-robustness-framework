#!/usr/bin/env python
"""
JJC Bot Optimizer CLI

Main entry point for the optimization framework.

Usage:
    python cli.py baseline TrendEng
    python cli.py optimize TrendEng --goal "Maximize PF, keep DD < 5%"
    python cli.py monte-carlo results.json --simulations 10000
    python cli.py test
"""

import argparse
import sys
import json
from pathlib import Path


def cmd_baseline(args):
    """Run baseline test for an entry."""
    from optimization_loop import run_baseline_test

    print(f"Running baseline test for {args.entry}...")
    results = run_baseline_test(args.entry)

    if results:
        print("\nBaseline Results:")
        print(results.to_summary())

        # Save results
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(results.to_dict(), f, indent=2)
            print(f"\nResults saved to: {output_path}")
    else:
        print("Baseline test failed")
        return 1

    return 0


def cmd_optimize(args):
    """Run LLM-guided optimization."""
    from optimization_loop import run_optimization

    print(f"Starting optimization for {args.entry}...")
    print(f"Goal: {args.goal}")

    summary = run_optimization(
        entry_type=args.entry,
        goal=args.goal,
    )

    print("\nOptimization Complete!")
    print(json.dumps(summary, indent=2))

    return 0


def cmd_monte_carlo(args):
    """Run Monte Carlo simulation on results."""
    from monte_carlo import MonteCarloSimulator

    # Load trades from file
    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: File not found: {results_path}")
        return 1

    with open(results_path) as f:
        data = json.load(f)

    # Extract trades
    if "trades" in data:
        trades = data["trades"]
    elif "individual_trades" in data:
        trades = [t.get("profit", t.get("pnl", 0)) for t in data["individual_trades"]]
    else:
        print("Error: Results file must contain 'trades' or 'individual_trades'")
        return 1

    print(f"Loaded {len(trades)} trades from {results_path}")

    # Run simulation
    sim = MonteCarloSimulator(
        trades,
        initial_balance=args.balance,
        risk_of_ruin_threshold=args.ruin_threshold
    )

    if args.method == "shuffle":
        result = sim.run_shuffle_simulation(args.simulations)
    elif args.method == "bootstrap":
        result = sim.run_bootstrap_simulation(args.simulations)
    else:
        result = sim.run_block_bootstrap(args.simulations)

    print(result.to_summary())

    # Save if requested
    if args.output:
        sim.save_results(result, args.output)

    return 0


def cmd_test(args):
    """Run system tests."""
    from tests.test_system import run_all_tests

    success = run_all_tests()
    return 0 if success else 1


def cmd_generate_set(args):
    """Generate a .set file for testing."""
    from set_file_generator import SetFileGenerator, ENTRY_TYPES

    gen = SetFileGenerator()

    if args.baseline:
        gen.create_baseline_config(ENTRY_TYPES[args.entry])
        print(f"Created baseline config for {args.entry}")
    else:
        gen.set_param("BOSSTESTENUMORATOR", ENTRY_TYPES[args.entry])

    # Apply any custom params
    if args.params:
        for param in args.params:
            key, value = param.split("=")
            # Try to convert to appropriate type
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    if value.lower() in ("true", "false"):
                        value = value.lower() == "true"
            gen.set_param(key, value)
            print(f"Set {key} = {value}")

    gen.generate(args.output)
    print(f"Generated: {args.output}")

    return 0


def cmd_status(args):
    """Show system status and configuration."""
    from config import get_config

    print("JJC Bot Optimizer - System Status")
    print("=" * 50)

    config = get_config()

    print(f"\nMT5 Configuration:")
    print(f"  Terminal Path: {config.mt5.terminal_path}")
    print(f"  Data Path:     {config.mt5.data_path}")
    print(f"  EA Name:       {config.mt5.ea_name}")

    print(f"\nBacktest Configuration:")
    print(f"  Symbol:        {config.backtest.symbol}")
    print(f"  Timeframe:     {config.backtest.timeframe}")
    print(f"  Period:        {config.backtest.start_date} to {config.backtest.end_date}")

    print(f"\nLLM Configuration:")
    print(f"  Provider:      {config.llm.provider}")
    has_key = bool(config.llm.anthropic_api_key or config.llm.openai_api_key)
    print(f"  API Key:       {'[SET]' if has_key else '[NOT SET]'}")

    print(f"\nOptimization Targets:")
    print(f"  Max Iterations:  {config.optimization.max_iterations}")
    print(f"  Target PF:       {config.optimization.target_profit_factor}")
    print(f"  Target Max DD:   {config.optimization.target_max_drawdown}%")

    # Check MT5 path exists
    mt5_path = Path(config.mt5.terminal_path)
    print(f"\nPath Validation:")
    print(f"  MT5 Path Exists: {'Yes' if mt5_path.exists() else 'NO - CHECK CONFIG'}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="JJC Bot Optimizer - Automated trading strategy optimization"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Baseline command
    baseline_parser = subparsers.add_parser("baseline", help="Run baseline test")
    baseline_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    baseline_parser.add_argument("-o", "--output", help="Save results to JSON file")
    baseline_parser.set_defaults(func=cmd_baseline)

    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Run LLM-guided optimization")
    optimize_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    optimize_parser.add_argument("--goal", default="Maximize profit factor while keeping max drawdown below 5%")
    optimize_parser.set_defaults(func=cmd_optimize)

    # Monte Carlo command
    mc_parser = subparsers.add_parser("monte-carlo", help="Run Monte Carlo simulation")
    mc_parser.add_argument("results_file", help="JSON file with trade results")
    mc_parser.add_argument("-n", "--simulations", type=int, default=10000)
    mc_parser.add_argument("-m", "--method", choices=["shuffle", "bootstrap", "block"], default="shuffle")
    mc_parser.add_argument("-b", "--balance", type=float, default=10000.0)
    mc_parser.add_argument("-r", "--ruin-threshold", type=float, default=10.0)
    mc_parser.add_argument("-o", "--output", help="Save results to JSON file")
    mc_parser.set_defaults(func=cmd_monte_carlo)

    # Generate .set file command
    gen_parser = subparsers.add_parser("generate-set", help="Generate a .set file")
    gen_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    gen_parser.add_argument("-o", "--output", default="test.set", help="Output file path")
    gen_parser.add_argument("--baseline", action="store_true", help="Use baseline config (all filters off)")
    gen_parser.add_argument("-p", "--params", nargs="*", help="Custom params (KEY=VALUE)")
    gen_parser.set_defaults(func=cmd_generate_set)

    # Test command
    test_parser = subparsers.add_parser("test", help="Run system tests")
    test_parser.set_defaults(func=cmd_test)

    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
