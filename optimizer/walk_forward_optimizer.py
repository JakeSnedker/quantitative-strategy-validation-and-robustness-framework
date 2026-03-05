"""
Walk-Forward Optimizer.

Automated walk-forward optimization system that:
1. Runs multiple MT5 optimizations across sliding time windows
2. Aggregates out-of-sample results
3. Validates against pass/fail criteria
4. Runs Monte Carlo simulation
5. Tests parameter stability
6. Generates comprehensive reports
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple

from walk_forward_config import (
    WalkForwardConfig,
    PassFailCriteria,
    PassFailStatus,
    ENTRY_TYPES,
    get_default_config,
)
from mt5_optimization import (
    MT5OptimizationRunner,
    OptimizationParam,
    OptimizationResult,
)
from monte_carlo import MonteCarloSimulator


@dataclass
class WindowResult:
    """Results from a single walk-forward window"""
    window_num: int
    optimization_start: str
    optimization_end: str
    forward_start: str
    forward_end: str

    # Best result from this window
    best_params: Dict[str, float] = field(default_factory=dict)
    in_sample_pf: float = 0.0
    forward_pf: float = 0.0
    forward_profit: float = 0.0
    forward_drawdown: float = 0.0
    forward_trades: int = 0

    # All results for analysis
    all_results: List[Dict] = field(default_factory=list)

    # Execution metadata
    duration_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None


@dataclass
class WalkForwardReport:
    """Complete walk-forward optimization report"""
    entry_type: str
    config: Dict[str, Any] = field(default_factory=dict)

    # Window results
    windows: List[WindowResult] = field(default_factory=list)

    # Aggregated metrics
    total_windows: int = 0
    successful_windows: int = 0
    total_forward_trades: int = 0
    combined_forward_pf: float = 0.0
    combined_forward_profit: float = 0.0
    max_forward_drawdown: float = 0.0
    walk_forward_efficiency: float = 0.0

    # Parameter analysis
    most_common_params: Dict[str, float] = field(default_factory=dict)
    param_consistency: float = 0.0  # % of windows with same params

    # Monte Carlo results
    monte_carlo_p_profit: float = 0.0
    monte_carlo_p_ruin: float = 0.0
    monte_carlo_95_ci: Tuple[float, float] = (0.0, 0.0)

    # Pass/Fail determination
    status: PassFailStatus = PassFailStatus.FAIL
    criteria_results: Dict[str, Dict] = field(default_factory=dict)
    failure_reasons: List[str] = field(default_factory=list)

    # Recommendations
    recommended_params: Optional[Dict[str, float]] = None

    # Execution metadata
    started_at: str = ""
    completed_at: str = ""
    total_duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['windows'] = [asdict(w) for w in self.windows]
        return result

    def to_summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            "=" * 60,
            f"WALK-FORWARD OPTIMIZATION REPORT: {self.entry_type}",
            "=" * 60,
            "",
            f"Status: {self.status.value}",
            f"Duration: {self.total_duration_seconds / 60:.1f} minutes",
            "",
            "AGGREGATE RESULTS:",
            f"  Windows: {self.successful_windows}/{self.total_windows} successful",
            f"  Combined Forward PF: {self.combined_forward_pf:.3f}",
            f"  Combined Forward Profit: ${self.combined_forward_profit:.2f}",
            f"  Max Forward Drawdown: {self.max_forward_drawdown:.2f}%",
            f"  Total Forward Trades: {self.total_forward_trades}",
            f"  Walk-Forward Efficiency: {self.walk_forward_efficiency:.1%}",
            "",
            "MONTE CARLO RESULTS:",
            f"  P(Profit): {self.monte_carlo_p_profit:.1%}",
            f"  P(Ruin): {self.monte_carlo_p_ruin:.1%}",
            f"  95% CI: [${self.monte_carlo_95_ci[0]:.2f}, ${self.monte_carlo_95_ci[1]:.2f}]",
            "",
        ]

        if self.recommended_params:
            lines.append("RECOMMENDED PARAMETERS:")
            for name, value in self.recommended_params.items():
                lines.append(f"  {name}: {value}")
            lines.append("")

        if self.failure_reasons:
            lines.append("FAILURE REASONS:")
            for reason in self.failure_reasons:
                lines.append(f"  - {reason}")
            lines.append("")

        lines.append("CRITERIA RESULTS:")
        for criterion, result in self.criteria_results.items():
            status_icon = "[PASS]" if result.get('passed') else "[FAIL]"
            lines.append(f"  {status_icon} {criterion}: {result.get('value', 'N/A')} "
                        f"(min: {result.get('minimum', 'N/A')})")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


class WalkForwardOptimizer:
    """
    Automated walk-forward optimization engine.
    """

    def __init__(self, config: WalkForwardConfig):
        """
        Initialize the optimizer.

        Args:
            config: WalkForwardConfig with all settings
        """
        self.config = config
        self.mt5_runner = MT5OptimizationRunner()
        self.report = WalkForwardReport(entry_type=config.entry_type)

    def run(self) -> WalkForwardReport:
        """
        Execute the full walk-forward optimization.

        Returns:
            WalkForwardReport with all results and analysis
        """
        start_time = time.time()
        self.report.started_at = datetime.now().isoformat()
        self.report.config = {
            "entry_type": self.config.entry_type,
            "start_date": self.config.start_date,
            "end_date": self.config.end_date,
            "optimization_months": self.config.walk_forward.optimization_months,
            "forward_months": self.config.walk_forward.forward_months,
            "step_months": self.config.walk_forward.step_months,
            "params": [{"name": p.name, "start": p.start, "stop": p.stop, "step": p.step}
                      for p in self.config.params],
        }

        # Validate config
        errors = self.config.validate()
        if errors:
            self.report.status = PassFailStatus.FAIL
            self.report.failure_reasons = errors
            return self.report

        # Calculate windows
        windows = self.config.walk_forward.calculate_windows(
            self.config.start_date, self.config.end_date
        )
        self.report.total_windows = len(windows)

        print(f"\nWalk-Forward Optimization: {self.config.entry_type}")
        print(f"Period: {self.config.start_date} to {self.config.end_date}")
        print(f"Windows: {len(windows)}")
        print("=" * 60)

        # Run optimization for each window
        for window in windows:
            print(f"\n--- Window {window['window']} ---")
            print(f"Optimize: {window['optimization_start']} to {window['optimization_end']}")
            print(f"Forward:  {window['forward_start']} to {window['forward_end']}")

            result = self._run_window(window)
            self.report.windows.append(result)

            if result.success:
                self.report.successful_windows += 1
                print(f"Result: Forward PF = {result.forward_pf:.3f}, "
                      f"Trades = {result.forward_trades}")
            else:
                print(f"Result: FAILED - {result.error}")

        # Aggregate results
        self._aggregate_results()

        # Run Monte Carlo
        self._run_monte_carlo()

        # Analyze parameter consistency
        self._analyze_parameters()

        # Check pass/fail criteria
        self._evaluate_criteria()

        # Finalize report
        self.report.completed_at = datetime.now().isoformat()
        self.report.total_duration_seconds = time.time() - start_time

        print("\n" + self.report.to_summary())

        return self.report

    def _run_window(self, window: Dict) -> WindowResult:
        """Run optimization for a single window"""
        result = WindowResult(
            window_num=window["window"],
            optimization_start=window["optimization_start"],
            optimization_end=window["optimization_end"],
            forward_start=window["forward_start"],
            forward_end=window["forward_end"],
        )

        window_start = time.time()

        try:
            # Convert params to OptimizationParam list
            opt_params = []
            for param in self.config.params:
                opt_params.append(OptimizationParam(
                    name=param.name,
                    start=param.start,
                    step=param.step,
                    stop=param.stop,
                    current=param.start,
                    optimize=param.optimize,
                ))

            # Run MT5 optimization with forward testing
            # Note: mt5_optimization.run_optimization() adds BOSSTESTENUMORATOR automatically
            mt5_result = self.mt5_runner.run_optimization(
                entry_type=self.config.entry_type,
                params=opt_params,
                start_date=window["optimization_start"],
                end_date=window["forward_end"],  # End at forward end
                optimization_mode=2 if self.config.genetic else 1,
                criterion=self.config.criterion,
                timeout=self.config.timeout_per_window,
                forward_mode="custom",
                forward_date=window["forward_start"],
            )

            result.duration_seconds = time.time() - window_start

            if mt5_result["success"] and mt5_result["results"]:
                result.success = True

                # Get best result (sorted by forward PF in MT5)
                best = mt5_result["results"][0]
                result.best_params = best.params.copy()

                # Extract forward and back results
                result.forward_pf = best.params.get("Forward Result", best.profit_factor)
                result.in_sample_pf = best.params.get("Back Result", best.profit_factor)
                result.forward_profit = best.profit
                result.forward_drawdown = best.drawdown_percent
                result.forward_trades = best.trades

                # Store all results for analysis
                result.all_results = [
                    {
                        "pass": r.pass_number,
                        "profit_factor": r.profit_factor,
                        "profit": r.profit,
                        "drawdown": r.drawdown_percent,
                        "trades": r.trades,
                        "params": r.params,
                    }
                    for r in mt5_result["results"][:20]  # Top 20
                ]
            else:
                result.error = mt5_result.get("error", "No results returned")

        except Exception as e:
            result.error = str(e)
            result.duration_seconds = time.time() - window_start

        return result

    def _aggregate_results(self):
        """Aggregate results across all windows"""
        if not self.report.windows:
            return

        successful = [w for w in self.report.windows if w.success]
        if not successful:
            return

        # Sum forward trades and profit
        self.report.total_forward_trades = sum(w.forward_trades for w in successful)
        self.report.combined_forward_profit = sum(w.forward_profit for w in successful)

        # Max drawdown across windows
        self.report.max_forward_drawdown = max(w.forward_drawdown for w in successful)

        # Average forward PF (weighted by trades would be more accurate)
        if successful:
            total_weighted_pf = sum(w.forward_pf * w.forward_trades for w in successful)
            if self.report.total_forward_trades > 0:
                self.report.combined_forward_pf = total_weighted_pf / self.report.total_forward_trades
            else:
                self.report.combined_forward_pf = sum(w.forward_pf for w in successful) / len(successful)

        # Walk-forward efficiency
        avg_in_sample = sum(w.in_sample_pf for w in successful) / len(successful)
        avg_forward = sum(w.forward_pf for w in successful) / len(successful)
        if avg_in_sample > 0:
            self.report.walk_forward_efficiency = avg_forward / avg_in_sample

    def _run_monte_carlo(self):
        """Run Monte Carlo simulation on combined forward results"""
        # Create synthetic trade list from forward results
        # This is approximate - ideally we'd have actual trade-by-trade data
        successful = [w for w in self.report.windows if w.success]
        if not successful:
            return

        # Estimate individual trade P&L from aggregate data
        trades = []
        for window in successful:
            if window.forward_trades > 0:
                # Estimate average trade
                avg_trade = window.forward_profit / window.forward_trades

                # Approximate individual trades (simplified)
                # In reality, would need actual trade data from MT5
                for _ in range(window.forward_trades):
                    trades.append(avg_trade)

        if len(trades) < 10:
            return

        # Run Monte Carlo
        sim = MonteCarloSimulator(
            trades=trades,
            initial_balance=10000,
            risk_of_ruin_threshold=self.config.criteria.max_drawdown_percent,
        )

        mc_result = sim.run_shuffle_simulation(num_simulations=5000)

        self.report.monte_carlo_p_profit = mc_result.probability_of_profit
        self.report.monte_carlo_p_ruin = mc_result.probability_of_ruin
        self.report.monte_carlo_95_ci = (
            mc_result.profit_5th_percentile,
            mc_result.profit_95th_percentile,
        )

    def _analyze_parameters(self):
        """Analyze parameter consistency across windows"""
        successful = [w for w in self.report.windows if w.success]
        if not successful:
            return

        # Count parameter occurrences
        param_counts: Dict[str, Dict[float, int]] = {}

        for window in successful:
            for name, value in window.best_params.items():
                if name in ["Forward Result", "Back Result"]:
                    continue
                if name not in param_counts:
                    param_counts[name] = {}
                if value not in param_counts[name]:
                    param_counts[name][value] = 0
                param_counts[name][value] += 1

        # Find most common value for each param
        for name, counts in param_counts.items():
            most_common_value = max(counts.keys(), key=lambda v: counts[v])
            self.report.most_common_params[name] = most_common_value

        # Calculate consistency (what % of windows used the most common params)
        if successful:
            matching_windows = 0
            for window in successful:
                all_match = True
                for name, value in self.report.most_common_params.items():
                    if window.best_params.get(name) != value:
                        all_match = False
                        break
                if all_match:
                    matching_windows += 1

            self.report.param_consistency = matching_windows / len(successful)

    def _evaluate_criteria(self):
        """Evaluate pass/fail criteria"""
        criteria = self.config.criteria
        results = {}
        failures = []

        # Forward Profit Factor
        results["forward_profit_factor"] = {
            "value": self.report.combined_forward_pf,
            "minimum": criteria.min_forward_profit_factor,
            "ideal": criteria.ideal_forward_profit_factor,
            "passed": self.report.combined_forward_pf >= criteria.min_forward_profit_factor,
        }
        if not results["forward_profit_factor"]["passed"]:
            failures.append(
                f"Forward PF {self.report.combined_forward_pf:.3f} < "
                f"minimum {criteria.min_forward_profit_factor}"
            )

        # Max Drawdown
        results["max_drawdown"] = {
            "value": self.report.max_forward_drawdown,
            "minimum": criteria.max_drawdown_percent,
            "passed": self.report.max_forward_drawdown <= criteria.max_drawdown_percent,
        }
        if not results["max_drawdown"]["passed"]:
            failures.append(
                f"Max DD {self.report.max_forward_drawdown:.2f}% > "
                f"limit {criteria.max_drawdown_percent}%"
            )

        # Trade Count
        avg_trades_per_window = (
            self.report.total_forward_trades / self.report.successful_windows
            if self.report.successful_windows > 0 else 0
        )
        results["trades_per_window"] = {
            "value": avg_trades_per_window,
            "minimum": criteria.min_trades_per_window,
            "passed": avg_trades_per_window >= criteria.min_trades_per_window,
        }
        if not results["trades_per_window"]["passed"]:
            failures.append(
                f"Avg trades/window {avg_trades_per_window:.0f} < "
                f"minimum {criteria.min_trades_per_window}"
            )

        # Walk-Forward Efficiency
        results["walk_forward_efficiency"] = {
            "value": self.report.walk_forward_efficiency,
            "minimum": criteria.min_walk_forward_efficiency,
            "ideal": criteria.ideal_walk_forward_efficiency,
            "passed": self.report.walk_forward_efficiency >= criteria.min_walk_forward_efficiency,
        }
        if not results["walk_forward_efficiency"]["passed"]:
            failures.append(
                f"WFE {self.report.walk_forward_efficiency:.1%} < "
                f"minimum {criteria.min_walk_forward_efficiency:.1%}"
            )

        # Monte Carlo P(Ruin)
        results["monte_carlo_ruin"] = {
            "value": self.report.monte_carlo_p_ruin,
            "maximum": criteria.max_monte_carlo_ruin_probability,
            "passed": self.report.monte_carlo_p_ruin <= criteria.max_monte_carlo_ruin_probability,
        }
        if not results["monte_carlo_ruin"]["passed"]:
            failures.append(
                f"P(Ruin) {self.report.monte_carlo_p_ruin:.1%} > "
                f"limit {criteria.max_monte_carlo_ruin_probability:.1%}"
            )

        # Window Success Rate
        success_rate = (
            self.report.successful_windows / self.report.total_windows
            if self.report.total_windows > 0 else 0
        )
        results["window_success_rate"] = {
            "value": success_rate,
            "minimum": 0.5,  # At least 50% of windows must succeed
            "passed": success_rate >= 0.5,
        }
        if not results["window_success_rate"]["passed"]:
            failures.append(
                f"Window success rate {success_rate:.1%} < 50%"
            )

        self.report.criteria_results = results
        self.report.failure_reasons = failures

        # Determine overall status
        all_passed = all(r["passed"] for r in results.values())

        if all_passed:
            # Check if we hit ideal thresholds for PASS vs MARGINAL
            ideals_met = (
                self.report.combined_forward_pf >= criteria.ideal_forward_profit_factor and
                self.report.max_forward_drawdown <= criteria.ideal_drawdown_percent and
                self.report.walk_forward_efficiency >= criteria.ideal_walk_forward_efficiency
            )

            if ideals_met:
                self.report.status = PassFailStatus.PASS
            else:
                self.report.status = PassFailStatus.MARGINAL

            # Set recommended params if passed/marginal
            self.report.recommended_params = self.report.most_common_params.copy()
        else:
            self.report.status = PassFailStatus.FAIL

    def save_report(self, output_dir: str = "results") -> str:
        """
        Save the report to disk.

        Args:
            output_dir: Directory to save reports

        Returns:
            Path to saved report
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wf_report_{self.config.entry_type}_{timestamp}.json"
        filepath = output_path / filename

        with open(filepath, 'w') as f:
            json.dump(self.report.to_dict(), f, indent=2)

        print(f"\nReport saved to: {filepath}")
        return str(filepath)


def run_walk_forward(
    entry_type: str,
    start_date: str = "2024.07.01",
    end_date: str = "2025.12.31",
    output_dir: str = "results",
) -> WalkForwardReport:
    """
    Convenience function to run walk-forward optimization.

    Args:
        entry_type: Entry pattern name
        start_date: Overall data start date
        end_date: Overall data end date
        output_dir: Directory to save report

    Returns:
        WalkForwardReport with results
    """
    config = get_default_config(entry_type)
    config.start_date = start_date
    config.end_date = end_date

    optimizer = WalkForwardOptimizer(config)
    report = optimizer.run()
    optimizer.save_report(output_dir)

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Walk-Forward Optimizer")
    parser.add_argument("entry", choices=list(ENTRY_TYPES.keys()),
                       help="Entry type to optimize")
    parser.add_argument("--start", default="2024.07.01",
                       help="Start date (YYYY.MM.DD)")
    parser.add_argument("--end", default="2025.12.31",
                       help="End date (YYYY.MM.DD)")
    parser.add_argument("-o", "--output", default="results",
                       help="Output directory")

    args = parser.parse_args()

    report = run_walk_forward(
        entry_type=args.entry,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output,
    )

    print(f"\nFinal Status: {report.status.value}")
