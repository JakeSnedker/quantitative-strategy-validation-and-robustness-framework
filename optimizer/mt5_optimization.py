"""
MT5 Built-in Optimization Runner.

Runs MT5's native optimization (genetic algorithm or full sweep)
to find optimal parameter combinations.
"""

import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from config import get_config, MT5Config, BacktestConfig
from set_file_generator import SetFileGenerator, ENTRY_TYPES


@dataclass
class OptimizationParam:
    """Parameter to optimize"""
    name: str
    start: float
    step: float
    stop: float
    current: float = 0.0
    optimize: bool = True

    def to_ini_string(self) -> str:
        """Convert to MT5 ini format: value||start||step||stop||Y/N"""
        flag = "Y" if self.optimize else "N"
        return f"{self.current}||{self.start}||{self.step}||{self.stop}||{flag}"


@dataclass
class OptimizationResult:
    """Single optimization result (one parameter combination)"""
    pass_number: int
    profit: float
    profit_factor: float
    expected_payoff: float
    drawdown: float
    drawdown_percent: float
    trades: int
    params: Dict[str, float] = field(default_factory=dict)


class MT5OptimizationRunner:
    """
    Runs MT5's built-in optimization engine.

    This uses MT5's genetic algorithm or complete sweep to test
    thousands of parameter combinations automatically.
    """

    # Optimization criteria
    CRITERIA = {
        "balance": 0,           # Maximum balance
        "profit_factor": 1,     # Maximum profit factor
        "expected_payoff": 2,   # Maximum expected payoff
        "drawdown": 3,          # Minimum drawdown
        "recovery_factor": 4,   # Maximum recovery factor
        "sharpe": 5,            # Maximum Sharpe ratio
        "custom": 6,            # Custom criterion
    }

    # Forward testing modes
    FORWARD_MODES = {
        "off": 0,       # No forward testing
        "half": 1,      # 1/2 - half of period is forward test
        "third": 2,     # 1/3 - one third is forward test
        "quarter": 3,   # 1/4 - one quarter is forward test
        "custom": 4,    # Custom date (uses forward_date parameter)
    }

    def __init__(self, mt5_config: Optional[MT5Config] = None):
        if mt5_config is None:
            config = get_config()
            mt5_config = config.mt5

        self.config = mt5_config
        self.data_path = Path(self.config.data_path)
        self.tester_path = Path(self.config.tester_path)

    def create_optimization_config(
        self,
        ea_name: str,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        params: List[OptimizationParam],
        optimization_mode: int = 2,  # 1=complete, 2=genetic
        criterion: str = "profit_factor",
        deposit: float = 10000,
        leverage: int = 100,
        model: int = 3,  # 0=every tick, 1=1min OHLC, 2=open only, 3=real ticks (BEST)
        forward_mode: str = "off",  # off, half, third, quarter, custom
        forward_date: Optional[str] = None,  # For custom forward mode
    ) -> str:
        """
        Create config.ini for MT5 optimization.

        Args:
            ea_name: Expert Advisor filename
            symbol: Trading symbol (e.g., "US30")
            timeframe: Timeframe (e.g., "M1")
            start_date: Start date "YYYY.MM.DD"
            end_date: End date "YYYY.MM.DD"
            params: List of parameters to optimize
            optimization_mode: 1=complete sweep, 2=genetic algorithm
            criterion: What to optimize for (see CRITERIA)
            deposit: Starting balance
            leverage: Account leverage
            model: Tick model (0=every tick, 1=1min OHLC, 2=open only, 3=real ticks)
            forward_mode: Forward testing mode (off, half, third, quarter, custom)
            forward_date: Custom forward test start date (required if forward_mode=custom)

        Returns:
            Path to created config.ini
        """
        # Add .cash suffix for index CFDs
        if not symbol.endswith('.cash') and symbol in ['US30', 'NAS100', 'US500']:
            symbol = f"{symbol}.cash"

        criterion_value = self.CRITERIA.get(criterion, 1)
        forward_mode_value = self.FORWARD_MODES.get(forward_mode, 0)
        report_name = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build [TesterInputs] section with optimization ranges
        inputs_lines = []
        for param in params:
            inputs_lines.append(f"{param.name}={param.to_ini_string()}")

        inputs_section = "\n".join(inputs_lines)

        # Build forward testing config
        forward_config = f"ForwardMode={forward_mode_value}"
        if forward_mode == "custom" and forward_date:
            forward_config += f"\nForwardDate={forward_date}"

        # Determine mode description
        if forward_mode == "off":
            mode_desc = "No Forward Testing"
        elif forward_mode == "custom":
            mode_desc = f"Forward from {forward_date}"
        else:
            mode_desc = f"Forward {forward_mode} of period"

        config_content = f"""; MT5 Optimization Configuration
; Generated by JJC Optimizer on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
; Mode: {'Genetic Algorithm' if optimization_mode == 2 else 'Complete Sweep'}
; Forward Testing: {mode_desc}
[Tester]
Expert={ea_name}
Symbol={symbol}
Period={timeframe}
Optimization={optimization_mode}
Model={model}
FromDate={start_date}
ToDate={end_date}
{forward_config}
Deposit={int(deposit)}
Currency=USD
ProfitInPips=0
Leverage={leverage}
ExecutionMode=0
OptimizationCriterion={criterion_value}
Visual=0
ShutdownTerminal=1
Report={report_name}
ReplaceReport=1
UseCloud=0
[TesterInputs]
{inputs_section}
"""

        # Write to Tester folder (where MT5 Strategy Tester actually reads from)
        config_path = self.tester_path / "config.ini"
        # Use ASCII encoding (MT5 Tester expects plain text, NOT UTF-16)
        with open(config_path, 'w', encoding='ascii') as f:
            f.write(config_content)

        self._last_report_name = report_name
        return str(config_path)

    def run_optimization(
        self,
        entry_type: str,
        params: List[OptimizationParam],
        start_date: str = "2025.01.01",
        end_date: str = "2025.06.30",
        optimization_mode: int = 2,
        criterion: str = "profit_factor",
        timeout: int = 3600,  # 1 hour default for optimization
        forward_mode: str = "off",  # off, half, third, quarter, custom
        forward_date: Optional[str] = None,  # For custom forward mode
    ) -> Dict[str, Any]:
        """
        Run a full MT5 optimization with optional forward testing.

        Args:
            entry_type: Entry pattern name (e.g., "TrendEng")
            params: Parameters to optimize with their ranges
            start_date: Backtest start date
            end_date: Backtest end date
            optimization_mode: 1=complete, 2=genetic
            criterion: Optimization criterion
            timeout: Max time to wait (seconds)
            forward_mode: Forward testing mode:
                - "off": No forward testing (default)
                - "half": 1/2 of period is forward test
                - "third": 1/3 of period is forward test
                - "quarter": 1/4 of period is forward test
                - "custom": Use forward_date parameter
            forward_date: Custom forward test start date (YYYY.MM.DD)

        Returns:
            Dict with optimization results including forward test metrics
        """
        import subprocess

        config = get_config()
        backtest_config = config.backtest

        result = {
            "success": False,
            "results": [],
            "best_result": None,
            "report_path": None,
            "error": None,
            "duration": 0,
        }

        start_time = time.time()

        try:
            # Add entry type parameter
            entry_num = ENTRY_TYPES.get(entry_type, 1)
            entry_param = OptimizationParam(
                name="BOSSTESTENUMORATOR",
                start=entry_num,
                step=1,
                stop=entry_num,
                current=entry_num,
                optimize=False  # Don't optimize this, keep fixed
            )
            all_params = [entry_param] + params

            # Create config
            config_path = self.create_optimization_config(
                ea_name=self.config.ea_name,
                symbol=backtest_config.symbol,
                timeframe=backtest_config.timeframe,
                start_date=start_date,
                end_date=end_date,
                params=all_params,
                optimization_mode=optimization_mode,
                criterion=criterion,
                deposit=backtest_config.initial_deposit,
                model=backtest_config.modeling_mode,
                forward_mode=forward_mode,
                forward_date=forward_date,
            )

            print(f"Created optimization config: {config_path}")
            print(f"Optimizing {entry_type} with {len(params)} parameters")
            print(f"Mode: {'Genetic Algorithm' if optimization_mode == 2 else 'Complete Sweep'}")
            print(f"Criterion: {criterion}")
            print(f"Period: {start_date} to {end_date}")
            if forward_mode != "off":
                if forward_mode == "custom":
                    print(f"Forward Testing: Custom from {forward_date}")
                else:
                    print(f"Forward Testing: {forward_mode} of period")
            print()

            # Launch MT5 (no /config: flag needed - MT5 reads Tester/config.ini automatically)
            terminal_exe = self.config.terminal_exe
            cmd = [terminal_exe]

            print(f"Config written to: {config_path}")
            print(f"Launching MT5 optimization...")
            print(f"This may take several minutes...")
            print()

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait for completion
            elapsed = 0
            check_interval = 10

            while elapsed < timeout:
                if process.poll() is not None:
                    print(f"MT5 exited with code: {process.returncode}")
                    break

                elapsed = int(time.time() - start_time)
                mins = elapsed // 60
                secs = elapsed % 60
                print(f"Optimization running... {mins}m {secs}s", end="\r")
                time.sleep(check_interval)

            print()

            # Find and parse results
            result["duration"] = time.time() - start_time

            # Look for optimization report (XML format)
            report_path = self._find_optimization_report()
            if report_path:
                result["report_path"] = report_path
                result["results"] = self._parse_optimization_report(report_path)
                if result["results"]:
                    result["success"] = True
                    # Best result is first (sorted by criterion)
                    result["best_result"] = result["results"][0]
                    print(f"Found {len(result['results'])} optimization results")
            else:
                result["error"] = "No optimization report found"

        except Exception as e:
            result["error"] = str(e)

        return result

    def _find_optimization_report(self) -> Optional[str]:
        """Find the optimization report file"""
        # MT5 saves optimization results in data path root as optimization_*.xml
        search_paths = [
            self.data_path,  # Primary location for optimization XML
            self.tester_path,
            self.tester_path / "Results",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            # Look for optimization XML files (newest first)
            xml_files = []
            for pattern in ["optimization_*.xml", "*.xml"]:
                for filepath in search_path.glob(pattern):
                    # Check if recently modified (within last hour)
                    if time.time() - os.path.getmtime(filepath) < 3600:
                        xml_files.append((os.path.getmtime(filepath), filepath))

            if xml_files:
                # Return most recent file
                xml_files.sort(reverse=True)
                return str(xml_files[0][1])

        return None

    def _parse_optimization_report(self, filepath: str) -> List[OptimizationResult]:
        """Parse MT5 optimization XML report (Excel SpreadsheetML format)"""
        results = []

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # Define namespaces for Excel XML
            ns = {
                'ss': 'urn:schemas-microsoft-com:office:spreadsheet',
                'o': 'urn:schemas-microsoft-com:office:office',
                'x': 'urn:schemas-microsoft-com:office:excel',
                'html': 'http://www.w3.org/TR/REC-html40',
            }

            # Find the worksheet table
            table = root.find('.//ss:Table', ns)
            if table is None:
                # Try without namespace
                table = root.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Table')
            if table is None:
                print("Warning: Could not find Table element in optimization report")
                return results

            rows = table.findall('ss:Row', ns)
            if not rows:
                rows = table.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Row')

            if not rows:
                print("Warning: No rows found in optimization report")
                return results

            # First row is headers
            headers = []
            header_row = rows[0]
            for cell in header_row.findall('ss:Cell', ns) or header_row.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Cell'):
                data = cell.find('ss:Data', ns) or cell.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Data')
                if data is not None and data.text:
                    headers.append(data.text)
                else:
                    headers.append("")

            # Map header names to indices
            header_map = {h: i for i, h in enumerate(headers)}

            # Parse data rows
            for row in rows[1:]:
                cells = row.findall('ss:Cell', ns) or row.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Cell')
                values = []
                for cell in cells:
                    data = cell.find('ss:Data', ns) or cell.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Data')
                    if data is not None and data.text:
                        values.append(data.text)
                    else:
                        values.append("0")

                if len(values) < len(headers):
                    # Pad with zeros if row is shorter
                    values.extend(["0"] * (len(headers) - len(values)))

                try:
                    # Extract standard fields
                    def get_val(name, default=0):
                        idx = header_map.get(name, -1)
                        if idx >= 0 and idx < len(values):
                            try:
                                return float(values[idx])
                            except ValueError:
                                return default
                        return default

                    opt_result = OptimizationResult(
                        pass_number=int(get_val("Pass", 0)),
                        profit=get_val("Profit", 0),
                        profit_factor=get_val("Profit Factor", 0),
                        expected_payoff=get_val("Expected Payoff", 0),
                        drawdown=get_val("Equity DD %", 0),  # Use Equity DD %
                        drawdown_percent=get_val("Equity DD %", 0),
                        trades=int(get_val("Trades", 0)),
                    )

                    # Extract custom parameters (anything not in standard columns)
                    standard_cols = {"Pass", "Result", "Profit", "Expected Payoff",
                                   "Profit Factor", "Recovery Factor", "Sharpe Ratio",
                                   "Custom", "Equity DD %", "Trades"}

                    for header, idx in header_map.items():
                        if header not in standard_cols and idx < len(values):
                            try:
                                opt_result.params[header] = float(values[idx])
                            except ValueError:
                                opt_result.params[header] = values[idx]

                    results.append(opt_result)

                except (ValueError, TypeError, IndexError) as e:
                    continue

        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")
        except Exception as e:
            print(f"Error parsing optimization report: {e}")

        # Sort by profit factor descending
        results.sort(key=lambda x: x.profit_factor, reverse=True)

        return results


def run_mt5_optimization(
    entry_type: str,
    params: Dict[str, tuple],  # {"ParamName": (start, step, stop)}
    start_date: str = "2025.01.01",
    end_date: str = "2025.06.30",
    criterion: str = "profit_factor",
    genetic: bool = True,
    timeout: int = 3600,
    forward_mode: str = "off",
    forward_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run MT5 optimization with optional forward testing.

    Args:
        entry_type: Entry pattern (TrendEng, TrendEngWick, etc.)
        params: Dict of parameter ranges {"Name": (start, step, stop)}
        start_date: Start date
        end_date: End date
        criterion: What to optimize for
        genetic: Use genetic algorithm (True) or complete sweep (False)
        timeout: Max wait time in seconds
        forward_mode: Forward testing mode:
            - "off": No forward testing (default)
            - "half": 1/2 of period is forward test
            - "third": 1/3 of period is forward test
            - "quarter": 1/4 of period is forward test
            - "custom": Use forward_date parameter
        forward_date: Custom forward test start date (YYYY.MM.DD)

    Returns:
        Optimization results with forward test metrics when enabled

    Example:
        # Basic optimization without forward testing
        results = run_mt5_optimization(
            entry_type="TrendEng",
            params={
                "ATRStopLossMultiplier": (1.0, 0.5, 3.0),
                "TakeProfitStopMultiplier": (1.5, 0.5, 3.0),
            },
            criterion="profit_factor",
            genetic=True
        )

        # With forward testing (1/3 of period)
        results = run_mt5_optimization(
            entry_type="TrendEng",
            params={"ATRStopLossMultiplier": (1.0, 0.5, 3.0)},
            start_date="2025.01.01",
            end_date="2025.12.31",
            forward_mode="third",  # Last 4 months as forward test
        )

        # With custom forward date
        results = run_mt5_optimization(
            entry_type="TrendEng",
            params={"ATRStopLossMultiplier": (1.0, 0.5, 3.0)},
            start_date="2025.01.01",
            end_date="2025.12.31",
            forward_mode="custom",
            forward_date="2025.10.01",  # Oct-Dec as forward test
        )
    """
    # Convert dict to OptimizationParam list
    opt_params = []
    for name, (start, step, stop) in params.items():
        opt_params.append(OptimizationParam(
            name=name,
            start=start,
            step=step,
            stop=stop,
            current=start,
            optimize=True
        ))

    runner = MT5OptimizationRunner()
    return runner.run_optimization(
        entry_type=entry_type,
        params=opt_params,
        start_date=start_date,
        end_date=end_date,
        optimization_mode=2 if genetic else 1,
        criterion=criterion,
        timeout=timeout,
        forward_mode=forward_mode,
        forward_date=forward_date,
    )


if __name__ == "__main__":
    print("MT5 Optimization Runner")
    print("=" * 50)
    print()
    print("Example usage:")
    print()
    print("  from mt5_optimization import run_mt5_optimization")
    print()
    print("  results = run_mt5_optimization(")
    print("      entry_type='TrendEng',")
    print("      params={")
    print("          'ATRStopLossMultiplier': (1.0, 0.5, 3.0),")
    print("          'TakeProfitStopMultiplier': (1.5, 0.5, 3.0),")
    print("      },")
    print("      start_date='2025.01.01',")
    print("      end_date='2025.06.30',")
    print("      criterion='profit_factor',")
    print("      genetic=True")
    print("  )")
    print()
    print("  if results['success']:")
    print("      print(f'Best PF: {results[\"best_result\"].profit_factor}')")
