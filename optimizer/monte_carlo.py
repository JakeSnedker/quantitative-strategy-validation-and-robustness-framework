"""
Monte Carlo Simulation for Strategy Validation.

Provides statistical confidence intervals for backtest results
by simulating thousands of possible trade sequences.
"""

import random
import statistics
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""

    # Input stats
    num_simulations: int
    num_trades: int
    original_profit: float
    original_max_dd: float

    # Profit distribution
    profit_mean: float
    profit_median: float
    profit_std: float
    profit_5th_percentile: float
    profit_25th_percentile: float
    profit_75th_percentile: float
    profit_95th_percentile: float

    # Drawdown distribution
    max_dd_mean: float
    max_dd_median: float
    max_dd_worst: float
    max_dd_95th_percentile: float

    # Risk metrics
    probability_of_profit: float
    probability_of_ruin: float  # DD > threshold
    risk_of_ruin_threshold: float

    # Confidence intervals
    profit_ci_lower: float  # 95% CI
    profit_ci_upper: float

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_summary(self) -> str:
        return f"""
Monte Carlo Simulation Results ({self.num_simulations:,} simulations)
{'=' * 60}

Original Results:
  Total Profit:     ${self.original_profit:,.2f}
  Max Drawdown:     {self.original_max_dd:.2f}%

Profit Distribution:
  Mean:             ${self.profit_mean:,.2f}
  Median:           ${self.profit_median:,.2f}
  Std Dev:          ${self.profit_std:,.2f}
  5th Percentile:   ${self.profit_5th_percentile:,.2f}  (worst 5%)
  95th Percentile:  ${self.profit_95th_percentile:,.2f} (best 5%)
  95% CI:           [${self.profit_ci_lower:,.2f}, ${self.profit_ci_upper:,.2f}]

Drawdown Distribution:
  Mean Max DD:      {self.max_dd_mean:.2f}%
  Median Max DD:    {self.max_dd_median:.2f}%
  95th Percentile:  {self.max_dd_95th_percentile:.2f}%
  Worst Case:       {self.max_dd_worst:.2f}%

Risk Assessment:
  P(Profit > 0):    {self.probability_of_profit:.1%}
  P(Ruin):          {self.probability_of_ruin:.1%} (DD > {self.risk_of_ruin_threshold}%)

{'=' * 60}
"""


class MonteCarloSimulator:
    """
    Monte Carlo simulator for trading strategy validation.

    Methods:
    - Trade Shuffling: Randomize order of actual trades
    - Bootstrap Resampling: Sample trades with replacement
    - Equity Curve Simulation: Generate confidence bands
    """

    def __init__(
        self,
        trades: List[float],
        initial_balance: float = 10000.0,
        risk_of_ruin_threshold: float = 10.0
    ):
        """
        Initialize simulator.

        Args:
            trades: List of trade P&L values (positive = win, negative = loss)
            initial_balance: Starting account balance
            risk_of_ruin_threshold: Max DD % considered "ruin"
        """
        self.trades = trades
        self.initial_balance = initial_balance
        self.risk_of_ruin_threshold = risk_of_ruin_threshold

        if not trades:
            raise ValueError("Trade list cannot be empty")

        logger.info(f"Initialized MC simulator with {len(trades)} trades")

    @classmethod
    def from_backtest_results(cls, results: Dict, initial_balance: float = 10000.0):
        """
        Create simulator from backtest results dict.

        Expected format:
        {
            "trades": [100.0, -50.0, 75.0, ...] or
            "individual_trades": [{"profit": 100.0}, {"profit": -50.0}, ...]
        }
        """
        if "trades" in results:
            trades = results["trades"]
        elif "individual_trades" in results:
            trades = [t.get("profit", t.get("pnl", 0)) for t in results["individual_trades"]]
        else:
            raise ValueError("Results must contain 'trades' or 'individual_trades' key")

        return cls(trades, initial_balance)

    def _calculate_equity_curve(self, trade_sequence: List[float]) -> Tuple[List[float], float, float]:
        """
        Calculate equity curve and max drawdown for a trade sequence.

        Returns:
            Tuple of (equity_curve, final_profit, max_drawdown_percent)
        """
        equity = [self.initial_balance]
        peak = self.initial_balance
        max_dd_pct = 0.0

        for pnl in trade_sequence:
            new_equity = equity[-1] + pnl
            equity.append(new_equity)

            if new_equity > peak:
                peak = new_equity

            if peak > 0:
                dd_pct = (peak - new_equity) / peak * 100
                max_dd_pct = max(max_dd_pct, dd_pct)

        final_profit = equity[-1] - self.initial_balance
        return equity, final_profit, max_dd_pct

    def run_shuffle_simulation(self, num_simulations: int = 10000) -> MonteCarloResult:
        """
        Run Monte Carlo simulation by shuffling trade order.

        This tests: "What if trades occurred in a different order?"
        Same trades, different sequence = different equity curve and drawdown.
        """
        logger.info(f"Running {num_simulations} shuffle simulations...")

        profits = []
        max_dds = []

        # Calculate original results first
        orig_equity, orig_profit, orig_dd = self._calculate_equity_curve(self.trades)

        for i in range(num_simulations):
            # Shuffle trade order
            shuffled = self.trades.copy()
            random.shuffle(shuffled)

            # Calculate metrics
            _, profit, max_dd = self._calculate_equity_curve(shuffled)
            profits.append(profit)
            max_dds.append(max_dd)

            if (i + 1) % 1000 == 0:
                logger.debug(f"Completed {i + 1}/{num_simulations} simulations")

        return self._compile_results(
            profits, max_dds, orig_profit, orig_dd, num_simulations
        )

    def run_bootstrap_simulation(self, num_simulations: int = 10000) -> MonteCarloResult:
        """
        Run Monte Carlo simulation with bootstrap resampling.

        This tests: "What if we had a different sample of similar trades?"
        Samples trades with replacement to create new synthetic histories.
        """
        logger.info(f"Running {num_simulations} bootstrap simulations...")

        profits = []
        max_dds = []
        n_trades = len(self.trades)

        # Calculate original results
        _, orig_profit, orig_dd = self._calculate_equity_curve(self.trades)

        for i in range(num_simulations):
            # Sample with replacement
            resampled = random.choices(self.trades, k=n_trades)

            # Calculate metrics
            _, profit, max_dd = self._calculate_equity_curve(resampled)
            profits.append(profit)
            max_dds.append(max_dd)

        return self._compile_results(
            profits, max_dds, orig_profit, orig_dd, num_simulations
        )

    def run_block_bootstrap(
        self,
        num_simulations: int = 10000,
        block_size: int = 5
    ) -> MonteCarloResult:
        """
        Run block bootstrap to preserve some trade clustering.

        This is more realistic as it maintains some autocorrelation
        (winning/losing streaks) from the original data.
        """
        logger.info(f"Running {num_simulations} block bootstrap simulations (block_size={block_size})...")

        profits = []
        max_dds = []
        n_trades = len(self.trades)

        # Create blocks
        blocks = []
        for i in range(0, n_trades, block_size):
            blocks.append(self.trades[i:i + block_size])

        # Calculate original results
        _, orig_profit, orig_dd = self._calculate_equity_curve(self.trades)

        for _ in range(num_simulations):
            # Sample blocks with replacement
            num_blocks_needed = (n_trades // block_size) + 1
            sampled_blocks = random.choices(blocks, k=num_blocks_needed)

            # Flatten and trim to original length
            resampled = []
            for block in sampled_blocks:
                resampled.extend(block)
            resampled = resampled[:n_trades]

            # Calculate metrics
            _, profit, max_dd = self._calculate_equity_curve(resampled)
            profits.append(profit)
            max_dds.append(max_dd)

        return self._compile_results(
            profits, max_dds, orig_profit, orig_dd, num_simulations
        )

    def _compile_results(
        self,
        profits: List[float],
        max_dds: List[float],
        orig_profit: float,
        orig_dd: float,
        num_simulations: int
    ) -> MonteCarloResult:
        """Compile simulation results into MonteCarloResult."""

        profits_sorted = sorted(profits)
        dds_sorted = sorted(max_dds)

        # Percentile indices
        idx_5 = int(0.05 * num_simulations)
        idx_25 = int(0.25 * num_simulations)
        idx_75 = int(0.75 * num_simulations)
        idx_95 = int(0.95 * num_simulations)

        # Probability calculations
        p_profit = sum(1 for p in profits if p > 0) / num_simulations
        p_ruin = sum(1 for dd in max_dds if dd > self.risk_of_ruin_threshold) / num_simulations

        # 95% Confidence Interval
        ci_lower = profits_sorted[int(0.025 * num_simulations)]
        ci_upper = profits_sorted[int(0.975 * num_simulations)]

        return MonteCarloResult(
            num_simulations=num_simulations,
            num_trades=len(self.trades),
            original_profit=orig_profit,
            original_max_dd=orig_dd,

            profit_mean=statistics.mean(profits),
            profit_median=statistics.median(profits),
            profit_std=statistics.stdev(profits),
            profit_5th_percentile=profits_sorted[idx_5],
            profit_25th_percentile=profits_sorted[idx_25],
            profit_75th_percentile=profits_sorted[idx_75],
            profit_95th_percentile=profits_sorted[idx_95],

            max_dd_mean=statistics.mean(max_dds),
            max_dd_median=statistics.median(max_dds),
            max_dd_worst=max(max_dds),
            max_dd_95th_percentile=dds_sorted[idx_95],

            probability_of_profit=p_profit,
            probability_of_ruin=p_ruin,
            risk_of_ruin_threshold=self.risk_of_ruin_threshold,

            profit_ci_lower=ci_lower,
            profit_ci_upper=ci_upper
        )

    def generate_confidence_bands(
        self,
        num_simulations: int = 1000,
        percentiles: List[int] = [5, 25, 50, 75, 95]
    ) -> Dict[int, List[float]]:
        """
        Generate equity curve confidence bands.

        Returns dict mapping percentile -> equity curve values.
        Useful for visualization.
        """
        n_trades = len(self.trades)
        all_curves = []

        for _ in range(num_simulations):
            shuffled = self.trades.copy()
            random.shuffle(shuffled)
            equity, _, _ = self._calculate_equity_curve(shuffled)
            all_curves.append(equity)

        # Calculate percentiles at each point
        bands = {p: [] for p in percentiles}

        for i in range(n_trades + 1):
            values_at_i = [curve[i] for curve in all_curves]
            values_at_i.sort()

            for p in percentiles:
                idx = int(p / 100 * num_simulations)
                bands[p].append(values_at_i[idx])

        return bands

    def save_results(self, result: MonteCarloResult, filepath: str) -> None:
        """Save Monte Carlo results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"Results saved to {filepath}")


def run_monte_carlo_analysis(
    trades: List[float],
    initial_balance: float = 10000.0,
    num_simulations: int = 10000,
    method: str = "shuffle",
    ruin_threshold: float = 10.0
) -> MonteCarloResult:
    """
    Convenience function to run Monte Carlo analysis.

    Args:
        trades: List of trade P&L values
        initial_balance: Starting balance
        num_simulations: Number of simulations to run
        method: "shuffle", "bootstrap", or "block_bootstrap"
        ruin_threshold: Max DD % considered ruin

    Returns:
        MonteCarloResult with full statistics
    """
    sim = MonteCarloSimulator(trades, initial_balance, ruin_threshold)

    if method == "shuffle":
        return sim.run_shuffle_simulation(num_simulations)
    elif method == "bootstrap":
        return sim.run_bootstrap_simulation(num_simulations)
    elif method == "block_bootstrap":
        return sim.run_block_bootstrap(num_simulations)
    else:
        raise ValueError(f"Unknown method: {method}")


if __name__ == "__main__":
    # Example usage with synthetic trades
    print("Monte Carlo Simulation Demo")
    print("=" * 60)

    # Simulate a strategy with 40% win rate, 2:1 R:R
    random.seed(42)
    sample_trades = []
    for _ in range(100):
        if random.random() < 0.40:  # 40% win rate
            sample_trades.append(random.uniform(150, 250))  # Winners: $150-250
        else:
            sample_trades.append(random.uniform(-80, -120))  # Losers: $80-120

    print(f"Sample trades: {len(sample_trades)}")
    print(f"Total P&L: ${sum(sample_trades):,.2f}")
    print(f"Avg trade: ${statistics.mean(sample_trades):,.2f}")

    # Run simulation
    sim = MonteCarloSimulator(sample_trades, initial_balance=10000, risk_of_ruin_threshold=10.0)

    print("\n--- Shuffle Simulation ---")
    result_shuffle = sim.run_shuffle_simulation(10000)
    print(result_shuffle.to_summary())

    print("\n--- Bootstrap Simulation ---")
    result_bootstrap = sim.run_bootstrap_simulation(10000)
    print(result_bootstrap.to_summary())
