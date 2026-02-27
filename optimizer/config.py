"""
Configuration management for JJC Bot Optimizer.
Loads settings from .env file with auto-detection fallbacks.
"""

import os
import glob
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()


def auto_detect_mt5_path() -> Optional[str]:
    """
    Attempt to auto-detect MT5 installation path.
    Searches common locations for terminal64.exe
    """
    common_paths = [
        # Roaming AppData (most common for MT5)
        os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\*"),
        # Program Files
        r"C:\Program Files\MetaTrader 5",
        r"C:\Program Files (x86)\MetaTrader 5",
        # Common broker installations
        r"C:\Program Files\*MT5*",
        r"C:\Program Files (x86)\*MT5*",
    ]

    for pattern in common_paths:
        matches = glob.glob(pattern)
        for match in matches:
            terminal_exe = os.path.join(match, "terminal64.exe")
            if os.path.exists(terminal_exe):
                return match

    return None


def auto_detect_data_path(terminal_path: str) -> Optional[str]:
    """
    Attempt to find the MQL5 data folder from terminal path.
    """
    mql5_path = os.path.join(terminal_path, "MQL5")
    if os.path.exists(mql5_path):
        return mql5_path
    return None


@dataclass
class MT5Config:
    """MT5-related configuration"""
    terminal_path: str
    data_path: str
    ea_name: str = "JJC_Bot-V13.3  (OTN Added).ex5"

    @property
    def terminal_exe(self) -> str:
        return os.path.join(self.terminal_path, "terminal64.exe")

    @property
    def experts_path(self) -> str:
        return os.path.join(self.data_path, "Experts")

    @property
    def presets_path(self) -> str:
        return os.path.join(self.data_path, "Presets")

    @property
    def tester_path(self) -> str:
        return os.path.join(self.terminal_path, "Tester")

    def validate(self) -> bool:
        """Validate that paths exist"""
        if not os.path.exists(self.terminal_exe):
            raise FileNotFoundError(f"MT5 terminal not found: {self.terminal_exe}")
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"MT5 data path not found: {self.data_path}")
        return True


@dataclass
class BacktestConfig:
    """Backtest settings"""
    symbol: str = "US30"
    timeframe: str = "M1"
    start_date: str = "2025.08.01"
    end_date: str = "2026.02.01"
    modeling_mode: int = 1  # 0=Every tick, 1=1min OHLC, 2=Open only
    initial_deposit: float = 10000
    timeout: int = 600  # seconds


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str = "anthropic"  # anthropic, openai, ollama
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    openai_model: str = "gpt-4-turbo"


@dataclass
class OptimizationConfig:
    """Optimization loop settings"""
    max_iterations: int = 50
    target_profit_factor: float = 1.5
    target_max_drawdown: float = 5.0
    min_improvement_rate: float = 0.01
    results_path: str = "./optimization_results"
    log_level: str = "INFO"


@dataclass
class Config:
    """Main configuration container"""
    mt5: MT5Config
    backtest: BacktestConfig
    llm: LLMConfig
    optimization: OptimizationConfig

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""

        # MT5 paths with auto-detection fallback
        terminal_path = os.getenv("MT5_TERMINAL_PATH")
        if not terminal_path or not os.path.exists(terminal_path):
            terminal_path = auto_detect_mt5_path()
            if terminal_path:
                print(f"Auto-detected MT5 path: {terminal_path}")
            else:
                raise ValueError(
                    "Could not find MT5 installation. "
                    "Please set MT5_TERMINAL_PATH in .env file"
                )

        data_path = os.getenv("MT5_DATA_PATH")
        if not data_path or not os.path.exists(data_path):
            data_path = auto_detect_data_path(terminal_path)
            if not data_path:
                raise ValueError(
                    "Could not find MT5 data folder. "
                    "Please set MT5_DATA_PATH in .env file"
                )

        mt5_config = MT5Config(
            terminal_path=terminal_path,
            data_path=data_path,
            ea_name=os.getenv("EA_NAME", "JJC_Bot-V13.3  (OTN Added).ex5")
        )

        backtest_config = BacktestConfig(
            symbol=os.getenv("DEFAULT_SYMBOL", "US30"),
            timeframe=os.getenv("DEFAULT_TIMEFRAME", "M1"),
            start_date=os.getenv("DEFAULT_START_DATE", "2025.08.01"),
            end_date=os.getenv("DEFAULT_END_DATE", "2026.02.01"),
            modeling_mode=int(os.getenv("MODELING_MODE", "1")),
            initial_deposit=float(os.getenv("INITIAL_DEPOSIT", "10000")),
            timeout=int(os.getenv("BACKTEST_TIMEOUT", "600"))
        )

        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "anthropic"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama2"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4-turbo")
        )

        opt_config = OptimizationConfig(
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50")),
            target_profit_factor=float(os.getenv("TARGET_PROFIT_FACTOR", "1.5")),
            target_max_drawdown=float(os.getenv("TARGET_MAX_DRAWDOWN", "5.0")),
            min_improvement_rate=float(os.getenv("MIN_IMPROVEMENT_RATE", "0.01")),
            results_path=os.getenv("RESULTS_PATH", "./optimization_results"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )

        return cls(
            mt5=mt5_config,
            backtest=backtest_config,
            llm=llm_config,
            optimization=opt_config
        )


# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the configuration singleton"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reload_config() -> Config:
    """Force reload configuration from environment"""
    global _config
    load_dotenv(override=True)
    _config = Config.from_env()
    return _config


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_config()
        print("Configuration loaded successfully!")
        print(f"MT5 Terminal: {config.mt5.terminal_path}")
        print(f"MT5 Data: {config.mt5.data_path}")
        print(f"EA: {config.mt5.ea_name}")
        print(f"Symbol: {config.backtest.symbol}")
        print(f"LLM Provider: {config.llm.provider}")
        config.mt5.validate()
        print("MT5 paths validated!")
    except Exception as e:
        print(f"Configuration error: {e}")
