"""
.set file generator for MT5 Expert Advisors.
Creates and modifies MT5 preset files for backtesting.

IMPORTANT: MT5 .set files MUST be:
1. UTF-16 encoded (not ASCII/UTF-8)
2. Named exactly like the EA for auto-loading
3. Made read-only to prevent MT5 overwriting on close
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class SetFileGenerator:
    """
    Generates and modifies MT5 .set files for EA parameter configuration.

    .set file format:
    ; saved on YYYY-MM-DD HH:MM:SS
    ;
    ParameterName=value
    ParameterName=value||start||step||end||Y/N  (for optimization range)
    """

    # Default parameters for JJC Bot V13.3
    # These are the baseline settings for testing
    DEFAULT_PARAMS = {
        # Entry selector
        "BOSSTESTENUMORATOR": 0,

        # Account settings
        "UseMaxDailyLoss": True,
        "MaxDailyLossPercent": 4.0,
        "UseMaxDailyGain": False,
        "MaxDailyGainPercent": 6.0,
        "ResetAccountHour": 3,
        "ResetAccountMin": 0,

        # Lot sizing
        "Compounding": False,
        "NonCompoundingAccountSize": 10000.0,
        "CalculateLots": 2,  # Auto based on stop
        "RiskForAutoLotSize": 1.0,
        "SupAndRes": 0,
        "Measuremet_For_Room": 2,
        "ATRMuliplierForRoom": 3.0,
        "RewardMultiplierForRoom": 0.5,
        "CheckRoom": True,

        # Entry patterns (booleans)
        "TrendE": True,
        "TrendEW": True,
        "TrendG": True,
        "TDIbnr": True,
        "TrueShift": True,

        # Candle patterns
        "MinCandleSize": 0.0,
        "PercentOfCandle": 77.0,

        # Angle filters
        "EMAAngleOfSlope": 40.0,
        "AngleOf13": True,
        "AngleOf21": True,
        "AngleOf55": True,
        "AngleOfL50": True,
        "AngleOfFastRSI": True,

        # Stop loss settings
        "StopLossMethod": 3,  # ATR
        "UseHighLowOfPrevCandleIfStopTooTight": True,
        "ATRStopLossMultiplier": 2.0,
        "ATRPeriod": 50,
        "SpreadMultiplier2": 2.0,

        # Take profit settings
        "TakeProfitMethod": 3,  # SL multiplied
        "TakeProfitStopMultiplier": 2.0,

        # Break even settings
        "BreakEvenMethod": 0,  # No BE
        "BreakEvenafterXPercentOfTrade": 10.0,
        "BreakEvenXPointsinProf": 1200,
        "BEProfit": 800,
        "BreakEvenAtXPercent": 1.0,

        # Trail settings
        "TrailMethod": 0,  # No trail
        "TrailafterXPercentOfTrade": 10.0,
        "ATRTrailMultiplier": 1.5,
        "MoveEveryXPercent": 1.0,
        "TrailSLEMA": 8,

        # Exit settings
        "KCMethod": 0,
        "LCExit": False,
        "LCasStopOnly": True,
        "LConClosure": True,
        "VBCMethod": 0,
        "ATRMultiplierBufferForStop": 2.0,
        "BloodInTheWaterBuffer": 5.0,
        "PushAwayExit": False,
        "PushAwayMultiplier": 2.0,
        "CandlesCloseOutSideOfPushAway": 3,
        "PChanMethod": 0,
        "OpCandleMethod": 0,
        "ThreeCOL": False,
        "BBCol": 0,
        "DojiClose": 0,

        # TDI settings
        "MWTDIBuffer": 0.0,
        "MaxMWatr": 5.0,
        "InpOverbought": 70.0,
        "InpOversold": 30.0,
        "InpShowBase": 1,
        "InpShowVBL": 1,
        "TDICheck": False,

        # Trading times
        "StartHour": 2,
        "StartMin": 0,
        "EndHour": 22,
        "EndMin": 30,
        "IncludeBreak": False,
        "StartBreakHour": 17,
        "StartBreakMin": 0,
        "EndBreakHour": 20,
        "EndBreakMin": 0,
        "CloseAllTradesHour": 23,
        "CloseAllTradesMinute": 30,
        "CloseAllTradesAtTime": True,

        # News trading
        "minutesBefore": 3,
        "minutesAfter": 3,
        "MinBeforeNewsToCloseTrades": 2,
        "AvoidHighImpactNews": True,
        "AvoidMediumImpactNews": False,
        "AvoidLowImpactNews": False,

        # Market open
        "TradeDuringMarketOpen": True,
        "CloseTradesBeforeMarketOpen": True,
        "StopTradingBerforeMaketOpenHour": 16,
        "StopTradingBerforeMaketOpenMin": 15,
        "StartTradingAfterMaketOpenHour": 16,
        "StartTradingAfterMaketOpenMin": 45,
        "UseHardCodeATRPeriods": True,
        "BotStatus": 0,  # Backtesting
        "TurnOnOnceInitiated": True,

        # Prop firm
        "OpenMultipleTrades": 0,
        "PropChallenge": False,
        "ProfitPercentage": 10.0,
        "DrawDownMethod": 0,

        # New inputs
        "BBlineLength": 34,
        "UseBBLine": False,
        "UsePSAR": False,
        "UseCloudColor": False,
        "BBexpand": True,
        "Tradescore": 1,

        # HTF trend
        "TrendMethod": 1,
        "HigherTimeFrame": 16385,  # M15
        "HigherTFTwo": 16388,  # H1
        "HTFFastEMA": 21,
        "HTFSlowEMA": 55,

        # Liquidity sweeps
        "NeedLIqSweep": False,
        "Session": 2,

        # Risk reduction
        "UseRiskReduction": False,
        "DrawDownSetting": 1,
        "ReduceRiskAtXPercentDD": 8.0,
        "RuductionPercent": 50.0,
        "RuduceEveryPercentFurther": 0.25,
        "NoTradeOnStats": True,
        "UseBreak": True,

        # Quick capture
        "CaptureBigCanlde": False,
        "CaptureMultiplier": 4,
        "FastMove": True,
        "WaitThreeCandles": False,
        "TrailAfterXCandles": 3,

        # Cloud settings
        "JakesCloud": True,
        "TrailingStopLossEMA": True,
        "PurpleChannel": False,

        # Multiple trades
        "SameTradeTypeInBothDirection": False,
    }

    # Parameters that should be treated as booleans
    BOOLEAN_PARAMS = {
        "UseMaxDailyLoss", "UseMaxDailyGain", "Compounding", "CheckRoom",
        "TrendE", "TrendEW", "TrendG", "TDIbnr", "TrueShift",
        "AngleOf13", "AngleOf21", "AngleOf55", "AngleOfL50", "AngleOfFastRSI",
        "UseHighLowOfPrevCandleIfStopTooTight", "LCExit", "LCasStopOnly",
        "LConClosure", "PushAwayExit", "ThreeCOL", "TDICheck",
        "IncludeBreak", "CloseAllTradesAtTime", "AvoidHighImpactNews",
        "AvoidMediumImpactNews", "AvoidLowImpactNews", "TradeDuringMarketOpen",
        "CloseTradesBeforeMarketOpen", "UseHardCodeATRPeriods", "TurnOnOnceInitiated",
        "PropChallenge", "UseBBLine", "UsePSAR", "UseCloudColor", "BBexpand",
        "NeedLIqSweep", "UseRiskReduction", "NoTradeOnStats", "UseBreak",
        "CaptureBigCanlde", "FastMove", "WaitThreeCandles", "JakesCloud",
        "TrailingStopLossEMA", "PurpleChannel", "SameTradeTypeInBothDirection"
    }

    def __init__(self, template_params: Optional[Dict[str, Any]] = None):
        """
        Initialize the generator with optional template parameters.

        Args:
            template_params: Base parameters to use. Defaults to DEFAULT_PARAMS.
        """
        self.params = self.DEFAULT_PARAMS.copy()
        if template_params:
            self.params.update(template_params)

    def update_params(self, updates: Dict[str, Any]) -> None:
        """
        Update parameters with new values.

        Args:
            updates: Dictionary of parameter names and values to update
        """
        for key, value in updates.items():
            if key in self.params:
                self.params[key] = value
            else:
                print(f"Warning: Unknown parameter '{key}' - adding anyway")
                self.params[key] = value

    def get_param(self, name: str) -> Any:
        """Get a parameter value"""
        return self.params.get(name)

    def set_param(self, name: str, value: Any) -> None:
        """Set a parameter value"""
        self.params[name] = value

    def _format_value(self, name: str, value: Any) -> str:
        """Format a value for .set file output"""
        if name in self.BOOLEAN_PARAMS or isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, float):
            # Format floats without unnecessary decimals
            if value == int(value):
                return str(int(value))
            return str(value)
        else:
            return str(value)

    def generate(
        self,
        output_path: str,
        comment: str = "",
        make_readonly: bool = True,
        archive_copy: bool = False,
    ) -> str:
        """
        Generate a .set file with current parameters using UTF-16 template.

        Uses the baseline.set template and modifies values in-place to ensure
        MT5 can read the file correctly.

        Args:
            output_path: Path to save the .set file
            comment: Optional comment to include in file header
            make_readonly: Make file read-only to prevent MT5 overwriting
            archive_copy: Also save an archive copy with timestamp

        Returns:
            Path to the generated file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Find template file
        template_path = Path(__file__).parent / "templates" / "baseline.set"

        if template_path.exists():
            # Use template-based generation (UTF-16)
            return self._generate_from_template(
                output_path, template_path, make_readonly, archive_copy
            )
        else:
            # Fallback to legacy generation
            return self._generate_legacy(output_path, comment)

    def _generate_from_template(
        self,
        output_path: Path,
        template_path: Path,
        make_readonly: bool,
        archive_copy: bool,
    ) -> str:
        """Generate .set file from UTF-16 template."""
        # Read template with UTF-16 encoding
        with open(template_path, 'r', encoding='utf-16') as f:
            content = f.read()

        # Apply all parameter modifications
        for name, value in self.params.items():
            formatted_value = self._format_value(name, value)
            # Match: ParamName=anything_until_newline
            # Replace with: ParamName=formatted_value (preserving optimization range format)
            pattern = rf'^({re.escape(name)}=)[^\n]*'
            # For simple values, we need to preserve the optimization format
            # Read existing line to get the format
            match = re.search(pattern, content, flags=re.MULTILINE)
            if match:
                existing_line = match.group(0)
                # Check if it has optimization range format (contains ||)
                if '||' in existing_line:
                    # Parse existing range: value||start||step||stop||Y/N
                    parts = existing_line.split('=', 1)[1].split('||')
                    if len(parts) >= 5:
                        # Update value but keep range and optimization flag
                        new_line = f"{name}={formatted_value}||{parts[1]}||{parts[2]}||{parts[3]}||{parts[4]}"
                        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
                    else:
                        # Malformed, just replace value
                        replacement = rf'\g<1>{formatted_value}'
                        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                else:
                    # No optimization range, simple replacement
                    replacement = rf'\g<1>{formatted_value}'
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # Make writable first (in case read-only from previous run)
        if output_path.exists():
            os.chmod(output_path, 0o644)

        # Write with UTF-16 encoding
        with open(output_path, 'w', encoding='utf-16') as f:
            f.write(content)

        # Make read-only to prevent MT5 overwriting
        if make_readonly:
            os.chmod(output_path, 0o444)

        # Save archive copy if requested
        if archive_copy:
            archive_dir = output_path.parent / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = archive_dir / f"{output_path.stem}_{timestamp}.set"
            with open(archive_path, 'w', encoding='utf-16') as f:
                f.write(content)

        return str(output_path)

    def _generate_legacy(self, output_path: Path, comment: str) -> str:
        """Legacy .set generation (UTF-16, no template)."""
        lines = []

        # Header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"; saved on {timestamp}")
        lines.append(";")
        if comment:
            lines.append(f"; {comment}")
            lines.append(";")

        # Parameters with optimization format
        for name, value in sorted(self.params.items()):
            formatted_value = self._format_value(name, value)
            # Use optimization format: value||value||0||value||N (no optimization)
            lines.append(f"{name}={formatted_value}||{formatted_value}||0||{formatted_value}||N")

        # Write with UTF-16 encoding for MT5 compatibility
        with open(output_path, 'w', encoding='utf-16') as f:
            f.write('\n'.join(lines))

        return str(output_path)

    def load_from_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load parameters from an existing .set file.

        Handles both UTF-16 (MT5 native) and UTF-8 encoded files.

        Args:
            filepath: Path to the .set file

        Returns:
            Dictionary of parameters loaded from file
        """
        loaded_params = {}

        # Try UTF-16 first (MT5's native format), fall back to UTF-8
        try:
            with open(filepath, 'r', encoding='utf-16') as f:
                content = f.read()
        except (UnicodeDecodeError, UnicodeError):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

        for line in content.split('\n'):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith(';'):
                    continue

                # Parse parameter line
                if '=' in line:
                    # Handle optimization range format: param=value||start||step||end||Y
                    parts = line.split('||')
                    name_value = parts[0].split('=', 1)

                    if len(name_value) == 2:
                        name = name_value[0].strip()
                        value_str = name_value[1].strip()

                        # Convert value to appropriate type
                        value = self._parse_value(name, value_str)
                        loaded_params[name] = value

        self.params.update(loaded_params)
        return loaded_params

    def _parse_value(self, name: str, value_str: str) -> Any:
        """Parse a string value to appropriate type"""
        value_str = value_str.strip()

        # Boolean
        if value_str.lower() in ('true', 'false'):
            return value_str.lower() == 'true'

        # Try integer
        try:
            if '.' not in value_str:
                return int(value_str)
        except ValueError:
            pass

        # Try float
        try:
            return float(value_str)
        except ValueError:
            pass

        # Return as string
        return value_str

    def create_baseline_config(self, entry_type: int) -> Dict[str, Any]:
        """
        Create a baseline configuration for testing a specific entry type.
        Disables all filters and trade management for raw edge testing.

        Args:
            entry_type: BOSSTESTENUMORATOR value (1, 2, 5, 8, or 9)

        Returns:
            Dictionary of baseline parameters
        """
        baseline = {
            "BOSSTESTENUMORATOR": entry_type,
            "BreakEvenMethod": 0,
            "TrailMethod": 0,
            "TakeProfitMethod": 3,
            "TakeProfitStopMultiplier": 2,
            "CheckRoom": False,
            "TrendMethod": 0,
            "BBexpand": False,
            "UsePSAR": False,
            "UseCloudColor": False,
            "UseBBLine": False,
            "Tradescore": 0,
            "AngleOf13": False,
            "AngleOf21": False,
            "AngleOf55": False,
            "AngleOfL50": False,
            "AngleOfFastRSI": False,
            "TDICheck": False,
        }

        self.update_params(baseline)
        return baseline

    def get_diff(self, other_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get parameters that differ from another set.

        Args:
            other_params: Parameters to compare against

        Returns:
            Dictionary of parameters that differ
        """
        diff = {}
        for key, value in self.params.items():
            if key in other_params and other_params[key] != value:
                diff[key] = {"current": value, "other": other_params[key]}
        return diff


# Entry type mapping for convenience
ENTRY_TYPES = {
    "TrendEng": 1,
    "TrendEngWick": 2,
    "TrendingGray": 5,
    "TrueShift": 8,
    "TDIBnR": 9,
}

# EA .set filename - MT5 auto-loads a .set file matching the EA name
EA_SET_FILENAME = "JJC_Bot-V13.3  (OTN Added).set"


def create_test_set_file(
    entry_type: str,
    output_dir: str,
    params: Optional[Dict[str, Any]] = None,
    test_id: str = ""
) -> str:
    """
    Convenience function to create a .set file for testing.

    Args:
        entry_type: Entry name (e.g., "TrendEng")
        output_dir: Directory to save the file
        params: Optional parameter overrides
        test_id: Optional test identifier for filename

    Returns:
        Path to generated .set file
    """
    generator = SetFileGenerator()

    # Set entry type
    entry_num = ENTRY_TYPES.get(entry_type, 0)
    generator.set_param("BOSSTESTENUMORATOR", entry_num)

    # Apply any additional params
    if params:
        generator.update_params(params)

    # Generate filename
    if test_id:
        filename = f"JJC_Bot_{entry_type}_{test_id}.set"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"JJC_Bot_{entry_type}_{timestamp}.set"

    output_path = os.path.join(output_dir, filename)

    return generator.generate(
        output_path,
        comment=f"Test config for {entry_type} entry"
    )


if __name__ == "__main__":
    # Test the generator
    gen = SetFileGenerator()

    # Create baseline for TrendEng
    gen.create_baseline_config(1)

    # Generate test file
    output = gen.generate(
        "test_output.set",
        comment="Baseline test for TrendEng"
    )
    print(f"Generated: {output}")

    # Show first few lines
    with open(output, 'r') as f:
        for i, line in enumerate(f):
            if i < 20:
                print(line.rstrip())
            else:
                print("...")
                break
