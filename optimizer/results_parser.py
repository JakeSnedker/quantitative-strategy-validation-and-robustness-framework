"""
MT5 Backtest Results Parser.
Parses XML/HTML reports from MT5 Strategy Tester.
"""

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import html.parser
import json


@dataclass
class Trade:
    """Individual trade record"""
    ticket: int
    open_time: str
    close_time: str
    type: str  # "buy" or "sell"
    volume: float
    symbol: str
    open_price: float
    close_price: float
    sl: float
    tp: float
    profit: float
    commission: float
    swap: float
    magic: int
    comment: str = ""

    @property
    def profit_pips(self) -> float:
        """Calculate profit in pips (approximate)"""
        if self.type.lower() == "buy":
            return self.close_price - self.open_price
        else:
            return self.open_price - self.close_price

    @property
    def is_winner(self) -> bool:
        return self.profit > 0


@dataclass
class BacktestResults:
    """Complete backtest results"""
    # Identification
    ea_name: str = ""
    symbol: str = ""
    timeframe: str = ""
    start_date: str = ""
    end_date: str = ""

    # Performance metrics
    initial_deposit: float = 0.0
    total_net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    expected_payoff: float = 0.0
    recovery_factor: float = 0.0
    sharpe_ratio: float = 0.0

    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    relative_drawdown: float = 0.0
    relative_drawdown_percent: float = 0.0

    # Trade statistics
    total_trades: int = 0
    total_deals: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # Position stats
    long_trades: int = 0
    long_wins: int = 0
    short_trades: int = 0
    short_wins: int = 0

    # Win/Loss metrics
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # Risk metrics
    avg_win_r: float = 0.0  # Average win in R multiples
    avg_loss_r: float = 1.0  # Average loss in R multiples (usually 1)

    # Individual trades
    trades: List[Trade] = field(default_factory=list)

    # Metadata
    report_path: str = ""
    parsed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding trade list for LLM)"""
        return {
            "ea_name": self.ea_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": f"{self.start_date} to {self.end_date}",
            "initial_deposit": self.initial_deposit,
            "total_net_profit": self.total_net_profit,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "expected_payoff": self.expected_payoff,
            "recovery_factor": self.recovery_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": self.max_drawdown_percent,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "long_trades": self.long_trades,
            "long_win_rate": (self.long_wins / self.long_trades * 100) if self.long_trades > 0 else 0,
            "short_trades": self.short_trades,
            "short_win_rate": (self.short_wins / self.short_trades * 100) if self.short_trades > 0 else 0,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "avg_win_r": self.avg_win_r,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
        }

    def to_summary(self) -> str:
        """Generate a concise summary for LLM analysis"""
        return f"""Backtest Results Summary:
- Period: {self.start_date} to {self.end_date}
- Symbol: {self.symbol} {self.timeframe}
- Total Trades: {self.total_trades}
- Win Rate: {self.win_rate:.1f}%
- Profit Factor: {self.profit_factor:.2f}
- Net Profit: ${self.total_net_profit:.2f}
- Max Drawdown: {self.max_drawdown_percent:.2f}%
- Average Win: ${self.average_win:.2f} ({self.avg_win_r:.1f}R)
- Average Loss: ${self.average_loss:.2f}
- Largest Win: ${self.largest_win:.2f}
- Largest Loss: ${self.largest_loss:.2f}
- Max Consecutive Losses: {self.max_consecutive_losses}
- Sharpe Ratio: {self.sharpe_ratio:.2f}
- Recovery Factor: {self.recovery_factor:.2f}"""

    def calculate_expectancy(self) -> float:
        """Calculate expectancy per trade"""
        if self.total_trades == 0:
            return 0.0
        win_pct = self.win_rate / 100
        loss_pct = 1 - win_pct
        return (win_pct * self.average_win) - (loss_pct * abs(self.average_loss))

    def calculate_r_metrics(self) -> None:
        """Calculate R-multiple metrics from trades"""
        if not self.trades or self.average_loss == 0:
            return

        # Use average loss as 1R
        r_unit = abs(self.average_loss)

        # Calculate average win in R
        if self.winning_trades > 0:
            total_wins = sum(t.profit for t in self.trades if t.profit > 0)
            self.avg_win_r = (total_wins / self.winning_trades) / r_unit


class XMLResultsParser:
    """Parse MT5 XML report files"""

    def parse(self, filepath: str) -> BacktestResults:
        """
        Parse an XML results file.

        Args:
            filepath: Path to the XML file

        Returns:
            BacktestResults object
        """
        results = BacktestResults()
        results.report_path = filepath
        results.parsed_at = datetime.now().isoformat()

        tree = ET.parse(filepath)
        root = tree.getroot()

        # Parse based on XML structure
        # MT5 XML reports can vary, so we handle multiple formats

        # Try to find summary statistics
        for elem in root.iter():
            tag = elem.tag.lower()
            text = elem.text.strip() if elem.text else ""

            # Map common fields
            self._map_field(results, tag, text, elem.attrib)

        # Parse trades table if present
        self._parse_trades(root, results)

        # Calculate derived metrics
        results.calculate_r_metrics()

        return results

    def _map_field(
        self,
        results: BacktestResults,
        tag: str,
        text: str,
        attrib: dict
    ) -> None:
        """Map XML field to results attribute"""

        # Common field mappings
        mappings = {
            "profit": ("total_net_profit", float),
            "totalnetprofit": ("total_net_profit", float),
            "grossprofit": ("gross_profit", float),
            "grossloss": ("gross_loss", float),
            "profitfactor": ("profit_factor", float),
            "expectedpayoff": ("expected_payoff", float),
            "recoveryfactor": ("recovery_factor", float),
            "sharperatio": ("sharpe_ratio", float),
            "maxdrawdown": ("max_drawdown", float),
            "maxdrawdownpercent": ("max_drawdown_percent", float),
            "relativedrawdown": ("relative_drawdown", float),
            "totaltrades": ("total_trades", int),
            "totaldeals": ("total_deals", int),
            "winningtrades": ("winning_trades", int),
            "losingtrades": ("losing_trades", int),
            "longtrades": ("long_trades", int),
            "longwins": ("long_wins", int),
            "shorttrades": ("short_trades", int),
            "shortwins": ("short_wins", int),
            "largestwin": ("largest_win", float),
            "largestloss": ("largest_loss", float),
            "averagewin": ("average_win", float),
            "averageloss": ("average_loss", float),
            "maxconsecutivewins": ("max_consecutive_wins", int),
            "maxconsecutivelosses": ("max_consecutive_losses", int),
            "deposit": ("initial_deposit", float),
            "symbol": ("symbol", str),
            "period": ("timeframe", str),
        }

        tag_clean = tag.replace("_", "").replace("-", "").lower()

        if tag_clean in mappings:
            attr_name, type_func = mappings[tag_clean]
            try:
                # Handle percentage values
                value = text.replace("%", "").replace(",", "").strip()
                setattr(results, attr_name, type_func(value))
            except (ValueError, TypeError):
                pass

    def _parse_trades(self, root: ET.Element, results: BacktestResults) -> None:
        """Parse individual trades from XML"""
        # Look for trades/deals table
        for table in root.iter("table"):
            # Check if this is the trades table
            headers = [th.text for th in table.findall(".//th") if th.text]

            if any("ticket" in h.lower() for h in headers if h):
                # Found trades table
                for row in table.findall(".//tr"):
                    cells = [td.text for td in row.findall("td")]
                    if len(cells) >= 8:
                        try:
                            trade = Trade(
                                ticket=int(cells[0]) if cells[0] else 0,
                                open_time=cells[1] or "",
                                close_time=cells[2] or "",
                                type=cells[3] or "",
                                volume=float(cells[4]) if cells[4] else 0,
                                symbol=cells[5] or "",
                                open_price=float(cells[6]) if cells[6] else 0,
                                close_price=float(cells[7]) if cells[7] else 0,
                                sl=float(cells[8]) if len(cells) > 8 and cells[8] else 0,
                                tp=float(cells[9]) if len(cells) > 9 and cells[9] else 0,
                                profit=float(cells[10]) if len(cells) > 10 and cells[10] else 0,
                                commission=float(cells[11]) if len(cells) > 11 and cells[11] else 0,
                                swap=float(cells[12]) if len(cells) > 12 and cells[12] else 0,
                                magic=int(cells[13]) if len(cells) > 13 and cells[13] else 0,
                            )
                            results.trades.append(trade)
                        except (ValueError, IndexError):
                            continue


class HTMLResultsParser:
    """Parse MT5 HTML report files"""

    def parse(self, filepath: str) -> BacktestResults:
        """
        Parse an HTML results file.

        This is a simplified parser that extracts key metrics using regex.
        MT5 HTML reports have a specific format we can target.
        """
        results = BacktestResults()
        results.report_path = filepath
        results.parsed_at = datetime.now().isoformat()

        # MT5 reports can be UTF-16 or UTF-8, try both
        try:
            with open(filepath, 'r', encoding='utf-16') as f:
                content = f.read()
        except (UnicodeError, UnicodeDecodeError):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        # Extract metrics using regex patterns - MT5 format: Label:</td><td><b>value</b></td>
        patterns = {
            "total_net_profit": r"Total Net Profit:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "gross_profit": r"Gross Profit:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "gross_loss": r"Gross Loss:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "profit_factor": r"Profit Factor:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "expected_payoff": r"Expected Payoff:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "max_drawdown": r"Balance Drawdown Maximal:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "max_drawdown_percent": r"Equity Drawdown Maximal:</td>\s*<td[^>]*><b>[^<]*\(([^)]+)%\)</b>",
            "total_trades": r"Total Trades:</td>\s*<td[^>]*><b>(\d+)</b>",
            "sharpe_ratio": r"Sharpe Ratio:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "recovery_factor": r"Recovery Factor:</td>\s*<td[^>]*><b>([^<]+)</b>",
            "winning_trades": r"Profit Trades[^:]*:</td>\s*<td[^>]*><b>(\d+)",
            "losing_trades": r"Loss Trades[^:]*:</td>\s*<td[^>]*><b>(\d+)",
        }

        for attr, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                value_str = match.group(1).strip()
                # Remove non-numeric chars except decimal and minus
                value_str = re.sub(r'[^\d.\-]', '', value_str)
                try:
                    if attr in ["total_trades", "winning_trades", "losing_trades"]:
                        setattr(results, attr, int(float(value_str)))
                    else:
                        setattr(results, attr, float(value_str))
                except (ValueError, TypeError):
                    pass

        # Calculate win rate
        if results.total_trades > 0 and results.winning_trades > 0:
            results.win_rate = (results.winning_trades / results.total_trades) * 100

        # Calculate losing trades if not found
        if results.losing_trades == 0 and results.total_trades > 0 and results.winning_trades > 0:
            results.losing_trades = results.total_trades - results.winning_trades

        return results


def parse_results(filepath: str) -> BacktestResults:
    """
    Parse a results file (auto-detect format).

    Args:
        filepath: Path to the results file

    Returns:
        BacktestResults object
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".xml":
        parser = XMLResultsParser()
    elif ext in [".htm", ".html"]:
        parser = HTMLResultsParser()
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    results = parser.parse(filepath)

    # Calculate win rate if not already set
    if results.total_trades > 0 and results.win_rate == 0:
        results.win_rate = (results.winning_trades / results.total_trades) * 100

    return results


def results_to_json(results: BacktestResults, filepath: str) -> None:
    """Save results to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)


if __name__ == "__main__":
    # Test parsing
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"Parsing: {filepath}")

        results = parse_results(filepath)
        print(results.to_summary())
        print("\nFull metrics:")
        for key, value in results.to_dict().items():
            print(f"  {key}: {value}")
    else:
        print("Usage: python results_parser.py <report_file>")
        print("\nSupported formats: .xml, .htm, .html")
