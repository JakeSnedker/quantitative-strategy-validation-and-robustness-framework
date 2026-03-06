"""
Terminal.ini Configuration Manager.

This module handles reading and writing MT5's terminal.ini file,
which controls Strategy Tester settings (dates, criterion, mode, etc.).

CRITICAL: MT5 overwrites terminal.ini when it closes, so we must:
1. Ensure MT5 is closed before writing
2. Write our settings
3. Optionally make read-only to prevent MT5 overwriting
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import IntEnum

from config import get_config


class OptimizationMode(IntEnum):
    """MT5 Optimization modes (values match MT5 terminal.ini)"""
    COMPLETE = 0      # Slow complete algorithm (use when combos < 1200)
    GENETIC = 1       # Fast genetic algorithm (use when combos > 1200)
    DISABLED = 2      # Single backtest (no optimization)


class TicksMode(IntEnum):
    """MT5 Modeling modes (values match MT5 terminal.ini)"""
    EVERY_TICK = 0              # Every tick (synthetic)
    OHLC_1MIN = 1               # 1 minute OHLC
    OPEN_PRICE = 2              # Open price only
    MATH_CALCULATION = 3        # Math calculation
    REAL_TICKS = 4              # Every tick based on real ticks (BEST)


class ForwardMode(IntEnum):
    """MT5 Forward testing modes"""
    OFF = 0           # No forward testing
    HALF = 1          # 1/2 of period
    THIRD = 2         # 1/3 of period (our default)
    QUARTER = 3       # 1/4 of period
    CUSTOM = 4        # Custom date


class OptimizationCriterion(IntEnum):
    """MT5 Optimization criteria"""
    BALANCE = 0           # Maximum balance
    PROFIT_FACTOR = 1     # Maximum profit factor (our default)
    EXPECTED_PAYOFF = 2   # Maximum expected payoff
    DRAWDOWN = 3          # Minimum drawdown
    RECOVERY_FACTOR = 4   # Maximum recovery factor
    SHARPE_RATIO = 5      # Maximum Sharpe ratio
    CUSTOM = 6            # Custom criterion


@dataclass
class TesterSettings:
    """Strategy Tester settings for terminal.ini"""
    # EA and Symbol
    expert: str = "Experts\\JJC_Bot-V13.3  (OTN Added).ex5"
    expert_parameters: str = ""  # Path to .set file (relative to MQL5/Profiles/Tester/)
    symbol: str = "US30.cash"
    period: int = 1  # M1

    # Date range (Unix timestamps)
    date_from: int = 0
    date_to: int = 0

    # Core settings
    ticks_mode: TicksMode = TicksMode.REAL_TICKS
    deposit: float = 10000.0
    leverage: int = 50
    currency: str = "USD"
    execution_delay: int = 50  # Delay in ms (Execution field in terminal.ini)

    # Optimization settings
    opt_mode: OptimizationMode = OptimizationMode.COMPLETE
    opt_criterion: OptimizationCriterion = OptimizationCriterion.PROFIT_FACTOR
    opt_forward: ForwardMode = ForwardMode.THIRD
    opt_forward_date: int = 0  # Unix timestamp for custom forward

    # Visual settings
    visualization: int = 0  # 0=off for automation

    @classmethod
    def for_optimization(
        cls,
        start_date: str,
        end_date: str,
        symbol: str = "US30.cash",
        param_combinations: int = 100,
        forward_mode: ForwardMode = ForwardMode.THIRD,
    ) -> "TesterSettings":
        """
        Create settings for an optimization run.

        Args:
            start_date: Start date "YYYY.MM.DD"
            end_date: End date "YYYY.MM.DD"
            symbol: Trading symbol
            param_combinations: Number of parameter combinations to test
            forward_mode: Forward testing mode

        Returns:
            TesterSettings configured for optimization
        """
        settings = cls()
        settings.symbol = symbol
        settings.date_from = cls._date_to_timestamp(start_date)
        settings.date_to = cls._date_to_timestamp(end_date)
        settings.opt_forward = forward_mode

        # Use complete sweep for small optimizations, genetic for large
        if param_combinations <= 1200:
            settings.opt_mode = OptimizationMode.COMPLETE
        else:
            settings.opt_mode = OptimizationMode.GENETIC

        return settings

    @classmethod
    def for_backtest(
        cls,
        start_date: str,
        end_date: str,
        symbol: str = "US30.cash",
    ) -> "TesterSettings":
        """
        Create settings for a single backtest run.

        Args:
            start_date: Start date "YYYY.MM.DD"
            end_date: End date "YYYY.MM.DD"
            symbol: Trading symbol

        Returns:
            TesterSettings configured for single backtest
        """
        settings = cls()
        settings.symbol = symbol
        settings.date_from = cls._date_to_timestamp(start_date)
        settings.date_to = cls._date_to_timestamp(end_date)
        settings.opt_mode = OptimizationMode.DISABLED
        settings.opt_forward = ForwardMode.OFF

        return settings

    @staticmethod
    def _date_to_timestamp(date_str: str) -> int:
        """Convert date string to Unix timestamp"""
        dt = datetime.strptime(date_str, "%Y.%m.%d")
        return int(dt.timestamp())

    @staticmethod
    def _timestamp_to_date(timestamp: int) -> str:
        """Convert Unix timestamp to date string"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y.%m.%d")


class TerminalConfigManager:
    """
    Manages MT5's terminal.ini file for Strategy Tester settings.

    IMPORTANT: MT5 must be CLOSED before writing to terminal.ini,
    as MT5 overwrites this file when it shuts down.
    """

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            config = get_config()
            data_path = config.mt5.data_path

        self.terminal_ini_path = Path(data_path) / "config" / "terminal.ini"

        if not self.terminal_ini_path.exists():
            raise FileNotFoundError(f"terminal.ini not found: {self.terminal_ini_path}")

    def read_tester_settings(self) -> Dict[str, Any]:
        """Read current [Tester] section from terminal.ini"""
        with open(self.terminal_ini_path, 'r', encoding='utf-16') as f:
            content = f.read()

        settings = {}
        in_tester = False

        for line in content.split('\n'):
            line = line.strip()

            if line == '[Tester]':
                in_tester = True
                continue

            if in_tester:
                if line.startswith('['):
                    break  # End of Tester section

                if '=' in line:
                    key, value = line.split('=', 1)
                    settings[key.strip()] = value.strip()

        return settings

    def write_tester_settings(
        self,
        settings: TesterSettings,
        make_readonly: bool = True
    ) -> None:
        """
        Write tester settings to terminal.ini.

        Args:
            settings: TesterSettings to write
            make_readonly: Make file read-only after writing to prevent MT5 overwriting
        """
        # Read existing content
        with open(self.terminal_ini_path, 'r', encoding='utf-16') as f:
            content = f.read()

        # Build replacement values
        replacements = {
            'Symbol': settings.symbol,
            'Period': str(settings.period),
            'DateFrom': str(settings.date_from),
            'DateTo': str(settings.date_to),
            'TicksMode': str(settings.ticks_mode.value),
            'LastTicksMode': str(settings.ticks_mode.value),
            'Deposit': f"{settings.deposit:.2f}",
            'Leverage': str(settings.leverage),
            'Currency': settings.currency,
            'Execution': str(settings.execution_delay),
            'OptMode': str(settings.opt_mode.value),
            'OptCrit': str(settings.opt_criterion.value),
            'OptForward': str(settings.opt_forward.value),
            'Visualization': str(settings.visualization),
            'DateRange': '3',  # Custom range
        }

        # Add ExpertParameters (path to .set file) if specified
        if settings.expert_parameters:
            replacements['ExpertParameters'] = settings.expert_parameters

        if settings.opt_forward == ForwardMode.CUSTOM and settings.opt_forward_date > 0:
            replacements['OptFwdDate'] = str(settings.opt_forward_date)

        # Apply replacements
        for key, value in replacements.items():
            # Match key=anything and replace with key=newvalue
            pattern = rf'{key}=[^\n]*'
            replacement = f'{key}={value}'
            content = re.sub(pattern, replacement, content)

        # Make writable if currently read-only
        if not os.access(self.terminal_ini_path, os.W_OK):
            os.chmod(self.terminal_ini_path, 0o644)

        # Write updated content
        with open(self.terminal_ini_path, 'w', encoding='utf-16') as f:
            f.write(content)

        # Make read-only if requested
        if make_readonly:
            os.chmod(self.terminal_ini_path, 0o444)

        print(f"Updated terminal.ini:")
        print(f"  Symbol: {settings.symbol}")
        print(f"  Dates: {TesterSettings._timestamp_to_date(settings.date_from)} to {TesterSettings._timestamp_to_date(settings.date_to)}")
        print(f"  Mode: {settings.opt_mode.name}")
        print(f"  Criterion: {settings.opt_criterion.name}")
        print(f"  Forward: {settings.opt_forward.name}")
        print(f"  Read-only: {make_readonly}")

    def make_writable(self) -> None:
        """Make terminal.ini writable"""
        os.chmod(self.terminal_ini_path, 0o644)
        print(f"Made writable: {self.terminal_ini_path}")

    def make_readonly(self) -> None:
        """Make terminal.ini read-only"""
        os.chmod(self.terminal_ini_path, 0o444)
        print(f"Made read-only: {self.terminal_ini_path}")


def configure_for_optimization(
    start_date: str,
    end_date: str,
    symbol: str = "US30.cash",
    param_combinations: int = 100,
    forward_mode: ForwardMode = ForwardMode.THIRD,
    make_readonly: bool = True,
) -> None:
    """
    Configure MT5 for an optimization run.

    Args:
        start_date: Start date "YYYY.MM.DD"
        end_date: End date "YYYY.MM.DD"
        symbol: Trading symbol
        param_combinations: Number of parameter combinations
        forward_mode: Forward testing mode
        make_readonly: Prevent MT5 from overwriting settings
    """
    settings = TesterSettings.for_optimization(
        start_date=start_date,
        end_date=end_date,
        symbol=symbol,
        param_combinations=param_combinations,
        forward_mode=forward_mode,
    )

    manager = TerminalConfigManager()
    manager.write_tester_settings(settings, make_readonly=make_readonly)


def configure_for_backtest(
    start_date: str,
    end_date: str,
    symbol: str = "US30.cash",
    make_readonly: bool = True,
) -> None:
    """
    Configure MT5 for a single backtest run.

    Args:
        start_date: Start date "YYYY.MM.DD"
        end_date: End date "YYYY.MM.DD"
        symbol: Trading symbol
        make_readonly: Prevent MT5 from overwriting settings
    """
    settings = TesterSettings.for_backtest(
        start_date=start_date,
        end_date=end_date,
        symbol=symbol,
    )

    manager = TerminalConfigManager()
    manager.write_tester_settings(settings, make_readonly=make_readonly)


if __name__ == "__main__":
    # Test the module
    print("Terminal Config Manager")
    print("=" * 50)

    manager = TerminalConfigManager()

    # Read current settings
    print("\nCurrent [Tester] settings:")
    current = manager.read_tester_settings()
    for key, value in sorted(current.items()):
        print(f"  {key}: {value}")

    print("\n" + "=" * 50)
    print("Example usage:")
    print()
    print("  # For optimization:")
    print("  configure_for_optimization('2024.07.01', '2025.01.01', param_combinations=50)")
    print()
    print("  # For single backtest:")
    print("  configure_for_backtest('2024.07.01', '2025.01.01')")
