"""
Main Optimization Loop.
Orchestrates the automated optimization process.
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from config import get_config, Config
from set_file_generator import SetFileGenerator, ENTRY_TYPES
from mt5_controller import MT5Controller
from results_parser import parse_results, BacktestResults
from llm_analyzer import OptimizationAnalyzer, OptimizationSuggestion, get_llm_provider


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationRun:
    """Record of a single optimization iteration"""
    iteration: int
    timestamp: str
    params: Dict[str, Any]
    results: Dict[str, Any]
    suggestion: Dict[str, Any]
    set_file: str
    report_file: str


class OptimizationLoop:
    """
    Main optimization orchestrator.

    Workflow:
    1. Generate .set file with current parameters
    2. Run MT5 backtest
    3. Parse results
    4. Send to LLM for analysis
    5. Apply suggested changes
    6. Repeat until stopping criteria met
    """

    def __init__(
        self,
        entry_type: str,
        goal: str,
        config: Optional[Config] = None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize the optimization loop.

        Args:
            entry_type: Entry pattern to optimize ("TrendEng", "TrendEngWick", etc.)
            goal: Optimization goal description
            config: Configuration object. Loads from env if not provided.
            output_dir: Directory for output files. Uses config default if not provided.
        """
        self.entry_type = entry_type
        self.entry_num = ENTRY_TYPES.get(entry_type, 0)
        self.goal = goal

        if config is None:
            config = get_config()
        self.config = config

        # Initialize components
        self.set_generator = SetFileGenerator()
        self.mt5 = MT5Controller(config.mt5)
        self.analyzer = OptimizationAnalyzer(goal)

        # Output directory
        if output_dir is None:
            output_dir = config.optimization.results_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Run tracking
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.entry_type}_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # History
        self.iterations: List[OptimizationRun] = []
        self.best_result: Optional[OptimizationRun] = None

        logger.info(f"Optimization loop initialized for {entry_type}")
        logger.info(f"Output directory: {self.run_dir}")

    def _save_state(self) -> None:
        """Save current optimization state to disk"""
        state = {
            "entry_type": self.entry_type,
            "goal": self.goal,
            "run_id": self.run_id,
            "iterations": [asdict(i) for i in self.iterations],
            "best_iteration": self.iterations.index(self.best_result) if self.best_result else None,
        }

        state_file = self.run_dir / "optimization_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _should_stop(
        self,
        iteration: int,
        results: BacktestResults,
        suggestion: OptimizationSuggestion
    ) -> tuple[bool, str]:
        """
        Check if optimization should stop.

        Returns:
            Tuple of (should_stop, reason)
        """
        opt_config = self.config.optimization

        # Check iteration limit
        if iteration >= opt_config.max_iterations:
            return True, f"Reached max iterations ({opt_config.max_iterations})"

        # Check if LLM says to stop
        if not suggestion.should_continue:
            return True, f"LLM recommended stop: {suggestion.stop_reason}"

        # Check target profit factor
        if results.profit_factor >= opt_config.target_profit_factor:
            if results.max_drawdown_percent <= opt_config.target_max_drawdown:
                return True, f"Targets met: PF={results.profit_factor:.2f}, DD={results.max_drawdown_percent:.1f}%"

        # Check for stagnation (no improvement in last 5 iterations)
        if len(self.iterations) >= 5:
            recent_pfs = [i.results.get("profit_factor", 0) for i in self.iterations[-5:]]
            if max(recent_pfs) - min(recent_pfs) < opt_config.min_improvement_rate:
                return True, "Optimization stagnated (no improvement in last 5 iterations)"

        return False, ""

    def run_single_test(self, params: Dict[str, Any]) -> Optional[BacktestResults]:
        """
        Run a single backtest with given parameters.

        Args:
            params: EA parameters to test

        Returns:
            BacktestResults or None if test failed
        """
        # Update generator with params
        self.set_generator.update_params(params)
        self.set_generator.set_param("BOSSTESTENUMORATOR", self.entry_num)

        # Generate .set file
        iteration = len(self.iterations) + 1
        set_filename = f"test_{iteration:04d}.set"
        set_path = str(self.run_dir / set_filename)

        self.set_generator.generate(
            set_path,
            comment=f"Optimization iteration {iteration} for {self.entry_type}"
        )
        logger.info(f"Generated .set file: {set_path}")

        # Run backtest
        logger.info("Running MT5 backtest...")
        result = self.mt5.run_backtest(
            set_file_path=set_path,
            backtest_config=self.config.backtest,
            timeout=self.config.backtest.timeout
        )

        if not result["success"]:
            logger.error(f"Backtest failed: {result['error']}")
            return None

        # Parse results
        logger.info(f"Parsing results from: {result['report_path']}")
        return parse_results(result["report_path"])

    def run(self, initial_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the full optimization loop.

        Args:
            initial_params: Starting parameters. Uses defaults if not provided.

        Returns:
            Dictionary with optimization results summary
        """
        logger.info(f"Starting optimization for {self.entry_type}")
        logger.info(f"Goal: {self.goal}")

        # Initialize parameters
        if initial_params is None:
            initial_params = {}

        current_params = self.set_generator.params.copy()
        current_params.update(initial_params)
        current_params["BOSSTESTENUMORATOR"] = self.entry_num

        iteration = 0
        stop_reason = ""

        while True:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {iteration}")
            logger.info(f"{'='*60}")

            # Run test
            results = self.run_single_test(current_params)

            if results is None:
                logger.error("Test failed, stopping optimization")
                stop_reason = "Test execution failed"
                break

            logger.info(f"\nResults:")
            logger.info(results.to_summary())

            # Analyze with LLM
            logger.info("\nAnalyzing with LLM...")
            suggestion = self.analyzer.analyze(results, current_params)

            logger.info(f"LLM Analysis:")
            logger.info(f"  Reasoning: {suggestion.reasoning}")
            logger.info(f"  Suggested changes: {suggestion.parameter_changes}")
            logger.info(f"  Confidence: {suggestion.confidence:.2f}")
            logger.info(f"  Type: {suggestion.exploration_type}")

            # Record iteration
            run = OptimizationRun(
                iteration=iteration,
                timestamp=datetime.now().isoformat(),
                params=current_params.copy(),
                results=results.to_dict(),
                suggestion={
                    "reasoning": suggestion.reasoning,
                    "changes": suggestion.parameter_changes,
                    "confidence": suggestion.confidence,
                    "exploration_type": suggestion.exploration_type,
                },
                set_file=f"test_{iteration:04d}.set",
                report_file=results.report_path,
            )
            self.iterations.append(run)

            # Track best result
            if self.best_result is None or results.profit_factor > self.best_result.results.get("profit_factor", 0):
                self.best_result = run
                logger.info(f"New best result! PF={results.profit_factor:.2f}")

            # Save state
            self._save_state()

            # Check stopping criteria
            should_stop, stop_reason = self._should_stop(iteration, results, suggestion)
            if should_stop:
                logger.info(f"\nStopping optimization: {stop_reason}")
                break

            # Apply suggested changes
            if suggestion.parameter_changes:
                current_params.update(suggestion.parameter_changes)
                logger.info(f"Applied parameter changes for next iteration")
            else:
                logger.warning("No parameter changes suggested, stopping")
                stop_reason = "No parameter changes suggested"
                break

        # Final summary
        summary = self._generate_summary(stop_reason)
        self._save_summary(summary)

        return summary

    def _generate_summary(self, stop_reason: str) -> Dict[str, Any]:
        """Generate final optimization summary"""
        summary = {
            "entry_type": self.entry_type,
            "goal": self.goal,
            "run_id": self.run_id,
            "total_iterations": len(self.iterations),
            "stop_reason": stop_reason,
            "best_result": None,
            "best_params": None,
            "improvement": None,
        }

        if self.best_result:
            summary["best_result"] = self.best_result.results
            summary["best_params"] = self.best_result.params
            summary["best_iteration"] = self.best_result.iteration

            # Calculate improvement from first to best
            if self.iterations:
                first_pf = self.iterations[0].results.get("profit_factor", 0)
                best_pf = self.best_result.results.get("profit_factor", 0)
                if first_pf > 0:
                    summary["improvement"] = {
                        "profit_factor": {
                            "initial": first_pf,
                            "final": best_pf,
                            "change_percent": ((best_pf - first_pf) / first_pf) * 100
                        }
                    }

        return summary

    def _save_summary(self, summary: Dict[str, Any]) -> None:
        """Save optimization summary to disk"""
        summary_file = self.run_dir / "optimization_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Summary saved to: {summary_file}")

        # Also save best parameters as .set file
        if self.best_result:
            best_set = self.run_dir / "best_params.set"
            self.set_generator.update_params(self.best_result.params)
            self.set_generator.generate(
                str(best_set),
                comment=f"Best parameters from optimization run {self.run_id}"
            )
            logger.info(f"Best parameters saved to: {best_set}")


def run_optimization(
    entry_type: str,
    goal: str,
    initial_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to run optimization.

    Args:
        entry_type: Entry pattern name
        goal: Optimization goal
        initial_params: Optional starting parameters

    Returns:
        Optimization summary
    """
    loop = OptimizationLoop(entry_type, goal)
    return loop.run(initial_params)


def run_baseline_test(entry_type: str) -> Optional[BacktestResults]:
    """
    Run a baseline test for an entry type with all filters disabled.

    Args:
        entry_type: Entry pattern name

    Returns:
        BacktestResults or None if test failed
    """
    config = get_config()

    generator = SetFileGenerator()
    generator.create_baseline_config(ENTRY_TYPES.get(entry_type, 0))

    # Create output directory
    output_dir = Path(config.optimization.results_path) / "baseline_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate set file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    set_path = str(output_dir / f"baseline_{entry_type}_{timestamp}.set")
    generator.generate(set_path, comment=f"Baseline test for {entry_type}")

    # Run test
    mt5 = MT5Controller(config.mt5)
    result = mt5.run_backtest(set_path)

    if result["success"]:
        return parse_results(result["report_path"])
    else:
        logger.error(f"Baseline test failed: {result['error']}")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JJC Bot Optimization Loop")
    parser.add_argument(
        "entry_type",
        choices=list(ENTRY_TYPES.keys()),
        help="Entry type to optimize"
    )
    parser.add_argument(
        "--goal",
        default="Maximize profit factor while keeping max drawdown below 5%",
        help="Optimization goal"
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Run baseline test only (no optimization)"
    )

    args = parser.parse_args()

    if args.baseline:
        print(f"Running baseline test for {args.entry_type}...")
        results = run_baseline_test(args.entry_type)
        if results:
            print("\nBaseline Results:")
            print(results.to_summary())
        else:
            print("Baseline test failed")
    else:
        print(f"Starting optimization for {args.entry_type}...")
        print(f"Goal: {args.goal}")
        summary = run_optimization(args.entry_type, args.goal)
        print("\nOptimization Complete!")
        print(json.dumps(summary, indent=2))
