"""
Monte Carlo Visualization Module.

Generates equity curve confidence bands and distribution charts
for strategy validation.
"""

import random
import statistics
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Check if matplotlib is available
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Install with: pip install matplotlib")


def generate_equity_curves(
    trades: List[float],
    num_simulations: int = 1000,
    initial_balance: float = 10000.0
) -> Tuple[List[List[float]], List[float]]:
    """
    Generate multiple equity curves by shuffling trade order.

    Returns:
        Tuple of (list of equity curves, original equity curve)
    """
    def calc_equity(trade_sequence: List[float]) -> List[float]:
        equity = [initial_balance]
        for pnl in trade_sequence:
            equity.append(equity[-1] + pnl)
        return equity

    # Original curve
    original_curve = calc_equity(trades)

    # Simulated curves
    simulated_curves = []
    for _ in range(num_simulations):
        shuffled = trades.copy()
        random.shuffle(shuffled)
        simulated_curves.append(calc_equity(shuffled))

    return simulated_curves, original_curve


def calculate_percentile_bands(
    curves: List[List[float]],
    percentiles: List[int] = [5, 25, 50, 75, 95]
) -> Dict[int, List[float]]:
    """
    Calculate percentile bands from multiple equity curves.

    Returns:
        Dict mapping percentile -> equity values at each trade
    """
    n_points = len(curves[0])
    bands = {p: [] for p in percentiles}

    for i in range(n_points):
        values_at_i = sorted([curve[i] for curve in curves])
        n = len(values_at_i)

        for p in percentiles:
            idx = int(p / 100 * n)
            idx = min(idx, n - 1)  # Prevent index out of bounds
            bands[p].append(values_at_i[idx])

    return bands


def plot_equity_confidence_bands(
    trades: List[float],
    num_simulations: int = 1000,
    initial_balance: float = 10000.0,
    title: str = "Monte Carlo Equity Curve Confidence Bands",
    save_path: Optional[str] = None,
    show_plot: bool = True
) -> Optional[str]:
    """
    Create equity curve plot with confidence bands.

    Args:
        trades: List of trade P&L values
        num_simulations: Number of Monte Carlo simulations
        initial_balance: Starting account balance
        title: Plot title
        save_path: Path to save the figure (optional)
        show_plot: Whether to display the plot

    Returns:
        Path to saved figure if save_path provided, else None
    """
    if not HAS_MATPLOTLIB:
        print("Cannot create plot - matplotlib not installed")
        return None

    print(f"Running {num_simulations} simulations...")
    curves, original = generate_equity_curves(trades, num_simulations, initial_balance)

    print("Calculating confidence bands...")
    bands = calculate_percentile_bands(curves, [5, 25, 50, 75, 95])

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    x = list(range(len(original)))

    # Plot confidence bands (from outside in for proper layering)
    # 5-95% band (lightest)
    ax.fill_between(x, bands[5], bands[95], alpha=0.2, color='blue', label='5-95% CI')

    # 25-75% band (medium)
    ax.fill_between(x, bands[25], bands[75], alpha=0.3, color='blue', label='25-75% CI')

    # Median line
    ax.plot(x, bands[50], 'b--', linewidth=1.5, alpha=0.7, label='Median')

    # Original equity curve
    ax.plot(x, original, 'g-', linewidth=2.5, label='Original Sequence')

    # Reference lines
    ax.axhline(y=initial_balance, color='gray', linestyle=':', alpha=0.5, label='Starting Balance')
    ax.axhline(y=initial_balance * 0.9, color='red', linestyle='--', alpha=0.5, label='10% DD (Ruin)')

    # Labels and formatting
    ax.set_xlabel('Trade Number', fontsize=12)
    ax.set_ylabel('Account Equity ($)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

    # Format y-axis as currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # Add statistics annotation
    final_values = [curve[-1] for curve in curves]
    stats_text = (
        f"Simulations: {num_simulations:,}\n"
        f"Trades: {len(trades)}\n"
        f"Original Final: ${original[-1]:,.2f}\n"
        f"Median Final: ${bands[50][-1]:,.2f}\n"
        f"5th Pctl: ${bands[5][-1]:,.2f}\n"
        f"95th Pctl: ${bands[95][-1]:,.2f}\n"
        f"P(Profit): {sum(1 for v in final_values if v > initial_balance) / len(final_values):.1%}"
    )

    # Add text box
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', horizontalalignment='right', bbox=props)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {save_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return save_path


def plot_profit_distribution(
    trades: List[float],
    num_simulations: int = 10000,
    initial_balance: float = 10000.0,
    title: str = "Monte Carlo Profit Distribution",
    save_path: Optional[str] = None,
    show_plot: bool = True
) -> Optional[str]:
    """
    Create histogram of final profit outcomes.
    """
    if not HAS_MATPLOTLIB:
        print("Cannot create plot - matplotlib not installed")
        return None

    print(f"Running {num_simulations} bootstrap simulations for distribution...")

    # Calculate final profits for each simulation using BOOTSTRAP (resampling with replacement)
    # Note: Shuffle would give same total every time - bootstrap creates variance
    final_profits = []
    n_trades = len(trades)
    for _ in range(num_simulations):
        # Sample with replacement to create "what if" scenarios
        resampled = random.choices(trades, k=n_trades)
        equity = initial_balance
        for pnl in resampled:
            equity += pnl
        final_profits.append(equity - initial_balance)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Histogram - use 'auto' bins to handle edge cases
    n, bins, patches = ax.hist(final_profits, bins='auto', edgecolor='black', alpha=0.7)

    # Color bars: green for profit, red for loss
    for i, patch in enumerate(patches):
        if bins[i] < 0:
            patch.set_facecolor('red')
        else:
            patch.set_facecolor('green')

    # Add vertical lines for key statistics
    original_profit = sum(trades)
    mean_profit = statistics.mean(final_profits)
    median_profit = statistics.median(final_profits)

    ax.axvline(x=0, color='black', linestyle='-', linewidth=2, label='Breakeven')
    ax.axvline(x=original_profit, color='blue', linestyle='-', linewidth=2, label=f'Original: ${original_profit:,.0f}')
    ax.axvline(x=mean_profit, color='orange', linestyle='--', linewidth=2, label=f'Mean: ${mean_profit:,.0f}')

    # 5th and 95th percentiles
    sorted_profits = sorted(final_profits)
    p5 = sorted_profits[int(0.05 * len(sorted_profits))]
    p95 = sorted_profits[int(0.95 * len(sorted_profits))]

    ax.axvline(x=p5, color='red', linestyle=':', linewidth=1.5, label=f'5th Pctl: ${p5:,.0f}')
    ax.axvline(x=p95, color='green', linestyle=':', linewidth=1.5, label=f'95th Pctl: ${p95:,.0f}')

    # Labels
    ax.set_xlabel('Final Profit ($)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    # Format x-axis as currency
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # Statistics annotation
    p_profit = sum(1 for p in final_profits if p > 0) / len(final_profits)
    stats_text = (
        f"P(Profit > 0): {p_profit:.1%}\n"
        f"Mean: ${mean_profit:,.2f}\n"
        f"Std Dev: ${statistics.stdev(final_profits):,.2f}\n"
        f"95% CI: [${p5:,.0f}, ${p95:,.0f}]"
    )

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='left', bbox=props)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {save_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return save_path


def plot_drawdown_distribution(
    trades: List[float],
    num_simulations: int = 10000,
    initial_balance: float = 10000.0,
    ruin_threshold: float = 10.0,
    title: str = "Monte Carlo Max Drawdown Distribution",
    save_path: Optional[str] = None,
    show_plot: bool = True
) -> Optional[str]:
    """
    Create histogram of maximum drawdown outcomes.
    """
    if not HAS_MATPLOTLIB:
        print("Cannot create plot - matplotlib not installed")
        return None

    print(f"Running {num_simulations} simulations for drawdown distribution...")

    # Calculate max DD for each simulation
    max_dds = []
    original_dd = 0

    for i in range(num_simulations + 1):
        if i == 0:
            sequence = trades  # Original
        else:
            sequence = trades.copy()
            random.shuffle(sequence)

        equity = initial_balance
        peak = initial_balance
        max_dd_pct = 0

        for pnl in sequence:
            equity += pnl
            if equity > peak:
                peak = equity
            if peak > 0:
                dd_pct = (peak - equity) / peak * 100
                max_dd_pct = max(max_dd_pct, dd_pct)

        if i == 0:
            original_dd = max_dd_pct
        else:
            max_dds.append(max_dd_pct)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Histogram - use 'auto' bins to handle edge cases
    n, bins, patches = ax.hist(max_dds, bins='auto', edgecolor='black', alpha=0.7, color='orange')

    # Color bars above ruin threshold red
    for i, patch in enumerate(patches):
        if bins[i] >= ruin_threshold:
            patch.set_facecolor('red')

    # Vertical lines
    ax.axvline(x=ruin_threshold, color='red', linestyle='-', linewidth=2,
               label=f'Ruin Threshold: {ruin_threshold}%')
    ax.axvline(x=original_dd, color='blue', linestyle='-', linewidth=2,
               label=f'Original: {original_dd:.1f}%')
    ax.axvline(x=statistics.mean(max_dds), color='orange', linestyle='--', linewidth=2,
               label=f'Mean: {statistics.mean(max_dds):.1f}%')

    # Labels
    ax.set_xlabel('Maximum Drawdown (%)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    # Statistics
    p_ruin = sum(1 for dd in max_dds if dd >= ruin_threshold) / len(max_dds)
    sorted_dds = sorted(max_dds)
    p95_dd = sorted_dds[int(0.95 * len(sorted_dds))]

    stats_text = (
        f"P(Ruin): {p_ruin:.1%}\n"
        f"Mean DD: {statistics.mean(max_dds):.1f}%\n"
        f"Median DD: {statistics.median(max_dds):.1f}%\n"
        f"95th Pctl: {p95_dd:.1f}%\n"
        f"Worst Case: {max(max_dds):.1f}%"
    )

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {save_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()

    return save_path


def create_full_monte_carlo_report(
    trades: List[float],
    output_dir: str = ".",
    initial_balance: float = 10000.0,
    num_simulations: int = 5000,
    strategy_name: str = "Strategy",
    show_plots: bool = True
) -> Dict[str, str]:
    """
    Generate complete Monte Carlo visual report.

    Returns:
        Dict with paths to generated files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # 1. Equity curve confidence bands
    equity_path = output_path / f"{strategy_name}_equity_bands.png"
    plot_equity_confidence_bands(
        trades,
        num_simulations=min(num_simulations, 1000),  # Fewer for equity curves
        initial_balance=initial_balance,
        title=f"{strategy_name} - Equity Curve Confidence Bands",
        save_path=str(equity_path),
        show_plot=show_plots
    )
    results["equity_bands"] = str(equity_path)

    # 2. Profit distribution
    profit_path = output_path / f"{strategy_name}_profit_distribution.png"
    plot_profit_distribution(
        trades,
        num_simulations=num_simulations,
        initial_balance=initial_balance,
        title=f"{strategy_name} - Profit Distribution",
        save_path=str(profit_path),
        show_plot=show_plots
    )
    results["profit_distribution"] = str(profit_path)

    # 3. Drawdown distribution
    dd_path = output_path / f"{strategy_name}_drawdown_distribution.png"
    plot_drawdown_distribution(
        trades,
        num_simulations=num_simulations,
        initial_balance=initial_balance,
        title=f"{strategy_name} - Max Drawdown Distribution",
        save_path=str(dd_path),
        show_plot=show_plots
    )
    results["drawdown_distribution"] = str(dd_path)

    print(f"\nGenerated {len(results)} visualizations in {output_dir}")
    return results


# Demo with synthetic data
if __name__ == "__main__":
    print("=" * 60)
    print("MONTE CARLO VISUALIZATION DEMO")
    print("=" * 60)

    # Generate synthetic trades: 35% win rate, ~2:1 R:R
    random.seed(42)
    sample_trades = []
    for _ in range(150):
        if random.random() < 0.35:  # 35% win rate
            sample_trades.append(random.uniform(180, 280))  # Winners
        else:
            sample_trades.append(random.uniform(-80, -130))  # Losers

    total_pnl = sum(sample_trades)
    winners = sum(1 for t in sample_trades if t > 0)

    print(f"\nSynthetic Trade Data:")
    print(f"  Total trades: {len(sample_trades)}")
    print(f"  Winners: {winners} ({winners/len(sample_trades):.1%})")
    print(f"  Total P&L: ${total_pnl:,.2f}")
    print(f"  Avg trade: ${total_pnl/len(sample_trades):,.2f}")

    print("\nGenerating visualizations...")
    print("(Close each plot window to continue)\n")

    # Create individual plots
    plot_equity_confidence_bands(
        sample_trades,
        num_simulations=500,
        title="Demo Strategy - Equity Confidence Bands"
    )

    plot_profit_distribution(
        sample_trades,
        num_simulations=5000,
        title="Demo Strategy - Profit Distribution"
    )

    plot_drawdown_distribution(
        sample_trades,
        num_simulations=5000,
        title="Demo Strategy - Drawdown Distribution"
    )

    print("\nDemo complete!")
