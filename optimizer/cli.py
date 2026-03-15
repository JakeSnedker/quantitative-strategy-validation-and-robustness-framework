#!/usr/bin/env python
"""
JJC Bot Optimizer CLI

Main entry point for the optimization framework.

Usage:
    python cli.py backtest TrendEng --monte-carlo
    python cli.py backtest TrendEng -p StopLossMethod=6 TakeProfitMethod=3 --monte-carlo
    python cli.py staged TrendEng --start-date 2024.07.01 --end-date 2025.12.31
    python cli.py walk-forward TrendEng --start-date 2024.07.01 --end-date 2025.12.31
    python cli.py mt5-optimize TrendEng -p ATRStopLossMultiplier=1.0,0.5,3.0 --forward third
    python cli.py baseline TrendEng
    python cli.py monte-carlo results.json --simulations 10000 --visualize
    python cli.py test
    python cli.py status

Commands:
    backtest     - Run single backtest with optional Monte Carlo analysis
    staged       - Run the full 5-stage optimization architecture (recommended)
    walk-forward - Run simple walk-forward optimization
    mt5-optimize - Run MT5's native optimization (genetic/sweep)
    baseline     - Run baseline test for an entry
    monte-carlo  - Run Monte Carlo simulation on results file
    test         - Run system tests
    status       - Show system status and configuration
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


def cmd_backtest(args):
    """Run a single backtest and optionally run Monte Carlo."""
    from mt5_optimization import MT5OptimizationRunner, OptimizationParam
    from config import get_config

    config = get_config()
    runner = MT5OptimizationRunner(config.mt5)  # Pass mt5 config, not full config

    print(f"Running single backtest for {args.entry}...")
    print(f"Period: {args.start_date} to {args.end_date}")

    # Build fixed params (no optimization - single values)
    params = []
    if args.params:
        for param in args.params:
            parts = param.split("=")
            if len(parts) == 2:
                name = parts[0]
                value = float(parts[1])
                params.append(OptimizationParam(
                    name=name,
                    start=value,
                    step=0,
                    stop=value,
                    current=value,
                    optimize=False
                ))
                print(f"  {name}: {value}")

    # Run backtest
    result = runner.run_optimization(
        entry_type=args.entry,
        params=params if params else [],
        start_date=args.start_date,
        end_date=args.end_date,
        optimization_mode=1,  # Complete (single run)
        criterion="profit_factor",
        timeout=args.timeout,
        forward_mode="off",
    )

    if result["success"] and result["results"]:
        best = result["results"][0]
        print(f"\nBacktest Result:")
        print(f"  Profit Factor: {best.profit_factor:.3f}")
        print(f"  Net Profit: ${best.profit:.2f}")
        print(f"  Drawdown: {best.drawdown_percent:.2f}%")
        print(f"  Trades: {best.trades}")

        # Try to parse HTML report for individual trades
        trades_pnl = []
        if result.get("report_path"):
            try:
                from results_parser import parse_results, extract_trade_pnl
                parsed = parse_results(result["report_path"])
                trades_pnl = extract_trade_pnl(parsed)
                print(f"  Individual trades extracted: {len(trades_pnl)}")
            except Exception as e:
                print(f"  Could not extract individual trades: {e}")

        # Run Monte Carlo if we have trades and user requested it
        if args.monte_carlo and trades_pnl:
            print(f"\nRunning Monte Carlo analysis ({args.simulations} simulations)...")
            from monte_carlo_viz import create_full_monte_carlo_report

            mc_output = Path(args.output) if args.output else Path("results/backtest_mc")
            create_full_monte_carlo_report(
                trades_pnl,
                output_dir=str(mc_output),
                strategy_name=f"{args.entry}_backtest",
                num_simulations=args.simulations,
                show_plots=not args.no_show
            )
            print(f"\nMonte Carlo charts saved to: {mc_output}")

        # Save results
        if args.output:
            output_data = {
                "entry": args.entry,
                "start_date": args.start_date,
                "end_date": args.end_date,
                "profit_factor": best.profit_factor,
                "profit": best.profit,
                "drawdown_percent": best.drawdown_percent,
                "trades": best.trades,
                "trades_pnl": trades_pnl,  # Individual trade P&L for Monte Carlo
            }
            output_path = Path(args.output) / "backtest_result.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to: {output_path}")

        return 0
    else:
        print(f"\nBacktest failed: {result.get('error', 'Unknown error')}")
        return 1


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
    if "trades_pnl" in data:
        trades = data["trades_pnl"]
    elif "trades" in data:
        trades = data["trades"]
    elif "individual_trades" in data:
        trades = [t.get("profit", t.get("pnl", 0)) for t in data["individual_trades"]]
    else:
        print("Error: Results file must contain 'trades', 'trades_pnl', or 'individual_trades'")
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

    # Generate visualizations if requested
    if args.visualize:
        from monte_carlo_viz import create_full_monte_carlo_report
        output_dir = Path(args.output).parent if args.output else Path("results/monte_carlo")
        create_full_monte_carlo_report(
            trades,
            output_dir=str(output_dir),
            strategy_name=results_path.stem,
            num_simulations=args.simulations,
            show_plots=True
        )

    # Save if requested
    if args.output:
        sim.save_results(result, args.output)

    return 0


def cmd_test(args):
    """Run system tests."""
    from tests.test_system import run_all_tests

    success = run_all_tests()
    return 0 if success else 1


def cmd_mt5_optimize(args):
    """Run MT5's built-in optimization (genetic algorithm or complete sweep)."""
    from mt5_optimization import run_mt5_optimization

    print(f"Starting MT5 optimization for {args.entry}...")
    print(f"Mode: {'Genetic Algorithm' if args.genetic else 'Complete Sweep'}")
    print(f"Criterion: {args.criterion}")
    print(f"Period: {args.start_date} to {args.end_date}")
    if args.forward != "off":
        if args.forward == "custom":
            print(f"Forward Testing: Custom from {args.forward_date}")
        else:
            print(f"Forward Testing: {args.forward} of period")
    print()

    # Build parameter ranges
    params = {}

    if args.params:
        for param in args.params:
            parts = param.split("=")
            if len(parts) != 2:
                print(f"Error: Invalid param format '{param}'. Use NAME=start,step,stop")
                return 1
            name = parts[0]
            values = parts[1].split(",")
            if len(values) != 3:
                print(f"Error: Invalid range format '{param}'. Use NAME=start,step,stop")
                return 1
            try:
                start, step, stop = float(values[0]), float(values[1]), float(values[2])
                params[name] = (start, step, stop)
            except ValueError:
                print(f"Error: Non-numeric values in '{param}'")
                return 1
    else:
        # Default parameters to optimize
        params = {
            "ATRStopLossMultiplier": (1.0, 0.5, 3.0),
            "TakeProfitStopMultiplier": (1.5, 0.5, 4.0),
        }
        print("Using default optimization parameters:")

    for name, (start, step, stop) in params.items():
        print(f"  {name}: {start} to {stop} (step {step})")
    print()

    results = run_mt5_optimization(
        entry_type=args.entry,
        params=params,
        start_date=args.start_date,
        end_date=args.end_date,
        criterion=args.criterion,
        genetic=args.genetic,
        timeout=args.timeout,
        forward_mode=args.forward,
        forward_date=args.forward_date,
    )

    if results["success"]:
        print("\nOptimization Complete!")
        print(f"Duration: {results['duration']:.1f} seconds")
        print(f"Total results: {len(results['results'])}")

        if results["best_result"]:
            best = results["best_result"]
            print(f"\nBest Result:")
            print(f"  Profit Factor: {best.profit_factor:.2f}")
            print(f"  Net Profit: ${best.profit:.2f}")
            print(f"  Drawdown: {best.drawdown_percent:.2f}%")
            print(f"  Trades: {best.trades}")
            print(f"  Parameters:")
            for param_name, value in best.params.items():
                print(f"    {param_name}: {value}")

        # Save results
        if args.output:
            import json
            output_data = {
                "entry": args.entry,
                "criterion": args.criterion,
                "duration": results["duration"],
                "best_result": {
                    "profit_factor": results["best_result"].profit_factor,
                    "profit": results["best_result"].profit,
                    "drawdown_percent": results["best_result"].drawdown_percent,
                    "trades": results["best_result"].trades,
                    "params": results["best_result"].params,
                } if results["best_result"] else None,
                "total_results": len(results["results"]),
            }
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to: {args.output}")
    else:
        print(f"\nOptimization failed: {results.get('error', 'Unknown error')}")
        return 1

    return 0


def cmd_walk_forward(args):
    """Run automated walk-forward optimization."""
    from walk_forward_optimizer import run_walk_forward
    from walk_forward_config import PassFailStatus

    print(f"Starting Walk-Forward Optimization for {args.entry}...")
    print(f"Period: {args.start_date} to {args.end_date}")
    print()

    report = run_walk_forward(
        entry_type=args.entry,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output,
    )

    # Return code based on status
    if report.status == PassFailStatus.PASS:
        return 0
    elif report.status == PassFailStatus.MARGINAL:
        return 0  # Still usable
    else:
        return 1


def cmd_staged(args):
    """Run staged walk-forward optimization (5-stage architecture)."""
    from staged_optimizer import run_staged_optimization
    from walk_forward_config import PassFailStatus

    print(f"Starting Staged Optimization for {args.entry}...")
    print(f"Period: {args.start_date} to {args.end_date}")
    print()
    print("This will run through all 5 stages:")
    print("  Stage 1: Foundation (SL/TP structure)")
    print("  Stage 2: Entry Refinement (filters vs baseline)")
    print("  Stage 3: Time & Context (vs winning system)")
    print("  Stage 4: Trade Management (BreakEven/Trail methods)")
    print("  Stage 5: Exits & Risk (final adjustments)")
    print()

    report = run_staged_optimization(
        entry_type=args.entry,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output,
    )

    # Return code based on status
    if report.final_status == PassFailStatus.PASS:
        return 0
    elif report.final_status == PassFailStatus.MARGINAL:
        return 0  # Still usable
    else:
        return 1


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

    # Backtest command (single run with optional Monte Carlo)
    bt_parser = subparsers.add_parser("backtest", help="Run single backtest with optional Monte Carlo")
    bt_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    bt_parser.add_argument("-p", "--params", nargs="*", help="Fixed parameters (NAME=value)")
    bt_parser.add_argument("--start-date", default="2024.07.01", help="Backtest start date")
    bt_parser.add_argument("--end-date", default="2025.12.31", help="Backtest end date")
    bt_parser.add_argument("-t", "--timeout", type=int, default=600, help="Timeout in seconds")
    bt_parser.add_argument("--monte-carlo", action="store_true", help="Run Monte Carlo analysis")
    bt_parser.add_argument("-n", "--simulations", type=int, default=5000, help="Monte Carlo simulations")
    bt_parser.add_argument("--no-show", action="store_true", help="Don't display plots (just save)")
    bt_parser.add_argument("-o", "--output", default="results/backtest", help="Output directory")
    bt_parser.set_defaults(func=cmd_backtest)

    # Monte Carlo command
    mc_parser = subparsers.add_parser("monte-carlo", help="Run Monte Carlo simulation")
    mc_parser.add_argument("results_file", help="JSON file with trade results")
    mc_parser.add_argument("-n", "--simulations", type=int, default=10000)
    mc_parser.add_argument("-m", "--method", choices=["shuffle", "bootstrap", "block"], default="shuffle")
    mc_parser.add_argument("-b", "--balance", type=float, default=10000.0)
    mc_parser.add_argument("-r", "--ruin-threshold", type=float, default=10.0)
    mc_parser.add_argument("-v", "--visualize", action="store_true", help="Generate visualization charts")
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

    # MT5 Optimization command (native genetic algorithm)
    mt5opt_parser = subparsers.add_parser("mt5-optimize", help="Run MT5 native optimization (genetic/sweep)")
    mt5opt_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    mt5opt_parser.add_argument("-p", "--params", nargs="*", help="Parameters to optimize (NAME=start,step,stop)")
    mt5opt_parser.add_argument("--start-date", default="2025.01.01", help="Backtest start date (YYYY.MM.DD)")
    mt5opt_parser.add_argument("--end-date", default="2025.06.30", help="Backtest end date (YYYY.MM.DD)")
    mt5opt_parser.add_argument("-c", "--criterion", default="profit_factor",
                               choices=["balance", "profit_factor", "expected_payoff", "drawdown", "recovery_factor", "sharpe"],
                               help="Optimization criterion")
    mt5opt_parser.add_argument("--sweep", dest="genetic", action="store_false", default=True,
                               help="Use complete sweep instead of genetic algorithm")
    mt5opt_parser.add_argument("-f", "--forward", default="off",
                               choices=["off", "half", "third", "quarter", "custom"],
                               help="Forward testing mode: off (default), half (1/2), third (1/3), quarter (1/4), or custom")
    mt5opt_parser.add_argument("--forward-date", default=None,
                               help="Custom forward test start date (YYYY.MM.DD) - required if --forward=custom")
    mt5opt_parser.add_argument("-t", "--timeout", type=int, default=3600, help="Max time in seconds (default 3600)")
    mt5opt_parser.add_argument("-o", "--output", help="Save results to JSON file")
    mt5opt_parser.set_defaults(func=cmd_mt5_optimize)

    # Walk-Forward Optimization command
    wf_parser = subparsers.add_parser("walk-forward", help="Run automated walk-forward optimization")
    wf_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    wf_parser.add_argument("--start-date", default="2024.07.01", help="Data start date (YYYY.MM.DD)")
    wf_parser.add_argument("--end-date", default="2025.12.31", help="Data end date (YYYY.MM.DD)")
    wf_parser.add_argument("-o", "--output", default="results", help="Output directory for reports")
    wf_parser.set_defaults(func=cmd_walk_forward)

    # Staged Optimization command (5-stage architecture)
    staged_parser = subparsers.add_parser("staged", help="Run 5-stage walk-forward optimization")
    staged_parser.add_argument("entry", choices=["TrendEng", "TrendEngWick", "TrendingGray", "TrueShift", "TDIBnR"])
    staged_parser.add_argument("--start-date", default="2024.07.01", help="Data start date (YYYY.MM.DD)")
    staged_parser.add_argument("--end-date", default="2025.12.31", help="Data end date (YYYY.MM.DD)")
    staged_parser.add_argument("-o", "--output", default="results", help="Output directory for reports")
    staged_parser.set_defaults(func=cmd_staged)

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
