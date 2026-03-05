"""
Walk-Forward Optimization Configuration.

This module defines all parameters, thresholds, and criteria
for the automated walk-forward optimization system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class PassFailStatus(Enum):
    """Optimization result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    MARGINAL = "MARGINAL"  # Passed minimum but not ideal


@dataclass
class PassFailCriteria:
    """
    Pass/Fail criteria for optimization validation.

    All 'minimum' values must be met to pass.
    'ideal' values indicate high-quality results.
    """
    # Primary criteria (hard requirements)
    min_forward_profit_factor: float = 1.0
    ideal_forward_profit_factor: float = 1.3

    max_drawdown_percent: float = 10.0  # FTMO limit
    ideal_drawdown_percent: float = 5.0

    min_trades_per_window: int = 20
    ideal_trades_per_window: int = 40

    min_walk_forward_efficiency: float = 0.5
    ideal_walk_forward_efficiency: float = 0.7

    # Secondary criteria (quality indicators)
    min_win_rate: float = 0.25  # 25%
    ideal_win_rate: float = 0.35  # 35%

    max_monte_carlo_ruin_probability: float = 0.15  # 15%
    ideal_monte_carlo_ruin_probability: float = 0.05  # 5%

    min_sharpe_ratio: float = 0.5
    ideal_sharpe_ratio: float = 1.0

    min_recovery_factor: float = 1.0
    ideal_recovery_factor: float = 2.0

    # Parameter stability
    require_adjacent_profitable: bool = True  # +/- 1 step must be profitable
    max_pf_variance_across_steps: float = 0.30  # 30% variance allowed
    min_window_consistency: float = 0.50  # Params must win in >50% of windows


@dataclass
class WalkForwardSettings:
    """
    Walk-forward window configuration.
    """
    optimization_months: int = 4  # In-sample period
    forward_months: int = 2       # Out-of-sample period
    step_months: int = 2          # Slide distance between windows

    # Minimum data requirements
    min_total_months: int = 12
    min_windows: int = 4

    # MT5 forward mode mapping
    # For custom dates, we calculate and use forward_mode="custom"
    use_custom_forward_date: bool = True

    def calculate_windows(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Calculate walk-forward window schedule.

        Args:
            start_date: Overall start date (YYYY.MM.DD)
            end_date: Overall end date (YYYY.MM.DD)

        Returns:
            List of window definitions with optimization and forward periods
        """
        from datetime import datetime

        def add_months(dt: datetime, months: int) -> datetime:
            """Add months to a datetime, handling year rollover"""
            month = dt.month - 1 + months
            year = dt.year + month // 12
            month = month % 12 + 1
            day = min(dt.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30,
                               31, 31, 30, 31, 30, 31][month - 1])
            return dt.replace(year=year, month=month, day=day)

        start = datetime.strptime(start_date, "%Y.%m.%d")
        end = datetime.strptime(end_date, "%Y.%m.%d")

        windows = []
        current_start = start
        window_num = 0

        while True:
            opt_end = add_months(current_start, self.optimization_months)
            forward_start = opt_end
            forward_end = add_months(forward_start, self.forward_months)

            # Stop if forward end exceeds data
            if forward_end > end:
                break

            windows.append({
                "window": window_num,
                "optimization_start": current_start.strftime("%Y.%m.%d"),
                "optimization_end": opt_end.strftime("%Y.%m.%d"),
                "forward_start": forward_start.strftime("%Y.%m.%d"),
                "forward_end": forward_end.strftime("%Y.%m.%d"),
            })

            window_num += 1
            current_start = add_months(current_start, self.step_months)

        return windows


@dataclass
class OptimizationParameter:
    """Single parameter to optimize"""
    name: str
    start: float
    stop: float
    step: float
    description: str = ""
    optimize: bool = True


# Core parameters to optimize (Phase 1: Risk/Reward)
CORE_OPTIMIZATION_PARAMS: List[OptimizationParameter] = [
    OptimizationParameter(
        name="ATRStopLossMultiplier",
        start=1.0,
        stop=3.5,
        step=0.5,
        description="ATR multiplier for stop loss distance"
    ),
    OptimizationParameter(
        name="TakeProfitStopMultiplier",
        start=1.5,
        stop=4.0,
        step=0.5,
        description="R:R multiplier (TP = SL * this value)"
    ),
]

# Extended parameters (Phase 2: After core is validated)
EXTENDED_OPTIMIZATION_PARAMS: List[OptimizationParameter] = [
    OptimizationParameter(
        name="ATRTrailMultiplier",
        start=1.0,
        stop=2.5,
        step=0.5,
        description="ATR multiplier for trailing stop"
    ),
    OptimizationParameter(
        name="TrailMethod",
        start=0,
        stop=2,
        step=1,
        description="Trailing stop method (0=off, 1=method1, 2=method2)"
    ),
    OptimizationParameter(
        name="BreakEvenMethod",
        start=0,
        stop=2,
        step=1,
        description="Break-even method (0=off, 1=method1, 2=method2)"
    ),
]

# Entry types configuration
ENTRY_TYPES = {
    "TrendEng": {"enum_value": 1, "magic": 3},
    "TrendEngWick": {"enum_value": 2, "magic": 4},
    "TrendingGray": {"enum_value": 5, "magic": 7},
    "TrueShift": {"enum_value": 8, "magic": 10},
    "TDIBnR": {"enum_value": 9, "magic": 11},
}

# FTMO compliance settings
FTMO_CONSTRAINTS = {
    "daily_loss_limit": 0.05,      # 5%
    "max_drawdown_limit": 0.10,    # 10%
    "profit_target": 0.10,         # 10%
    "min_trading_days": 4,

    # Safety buffers (what we target to stay safe)
    "target_daily_loss": 0.04,     # 4% (1% buffer)
    "target_max_drawdown": 0.08,   # 8% (2% buffer)
}

# Default optimization settings
DEFAULT_OPTIMIZATION_SETTINGS = {
    "genetic": True,               # Use genetic algorithm
    "criterion": "profit_factor",  # Optimize for PF
    "timeout": 3600,               # 1 hour max per window
    "monte_carlo_simulations": 10000,
}


@dataclass
class WalkForwardConfig:
    """
    Complete configuration for a walk-forward optimization run.
    """
    entry_type: str
    start_date: str  # Overall data start
    end_date: str    # Overall data end

    walk_forward: WalkForwardSettings = field(default_factory=WalkForwardSettings)
    criteria: PassFailCriteria = field(default_factory=PassFailCriteria)
    params: List[OptimizationParameter] = field(default_factory=lambda: CORE_OPTIMIZATION_PARAMS.copy())

    genetic: bool = True
    criterion: str = "profit_factor"
    timeout_per_window: int = 3600

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []

        if self.entry_type not in ENTRY_TYPES:
            errors.append(f"Unknown entry type: {self.entry_type}")

        if not self.params:
            errors.append("No parameters specified for optimization")

        # Check date range is sufficient
        windows = self.walk_forward.calculate_windows(self.start_date, self.end_date)
        if len(windows) < self.walk_forward.min_windows:
            errors.append(
                f"Insufficient data: {len(windows)} windows, need {self.walk_forward.min_windows}. "
                f"Extend date range or reduce window sizes."
            )

        return errors


def get_default_config(entry_type: str) -> WalkForwardConfig:
    """
    Get default walk-forward configuration for an entry type.

    Args:
        entry_type: One of TrendEng, TrendEngWick, TrendingGray, TrueShift, TDIBnR

    Returns:
        WalkForwardConfig with sensible defaults
    """
    return WalkForwardConfig(
        entry_type=entry_type,
        start_date="2024.07.01",  # 18 months of data
        end_date="2025.12.31",
        walk_forward=WalkForwardSettings(
            optimization_months=4,
            forward_months=2,
            step_months=2,
        ),
        criteria=PassFailCriteria(),
        params=CORE_OPTIMIZATION_PARAMS.copy(),
    )


if __name__ == "__main__":
    # Demo: Show what windows would be generated
    config = get_default_config("TrendEng")

    print("Walk-Forward Configuration Demo")
    print("=" * 50)
    print(f"Entry: {config.entry_type}")
    print(f"Period: {config.start_date} to {config.end_date}")
    print(f"Optimization window: {config.walk_forward.optimization_months} months")
    print(f"Forward test: {config.walk_forward.forward_months} months")
    print(f"Step: {config.walk_forward.step_months} months")
    print()

    print("Parameters to optimize:")
    for param in config.params:
        print(f"  {param.name}: {param.start} to {param.stop} (step {param.step})")
    print()

    windows = config.walk_forward.calculate_windows(config.start_date, config.end_date)
    print(f"Walk-Forward Windows ({len(windows)} total):")
    for w in windows:
        print(f"  Window {w['window']}: "
              f"Optimize {w['optimization_start']} - {w['optimization_end']} | "
              f"Forward {w['forward_start']} - {w['forward_end']}")
    print()

    print("Pass/Fail Criteria:")
    print(f"  Min Forward PF: {config.criteria.min_forward_profit_factor}")
    print(f"  Max Drawdown: {config.criteria.max_drawdown_percent}%")
    print(f"  Min Trades/Window: {config.criteria.min_trades_per_window}")
    print(f"  Min WFE: {config.criteria.min_walk_forward_efficiency}")

    errors = config.validate()
    if errors:
        print(f"\nValidation Errors: {errors}")
    else:
        print(f"\nConfiguration valid!")
