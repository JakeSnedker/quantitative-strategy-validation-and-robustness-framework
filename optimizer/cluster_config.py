"""
Cluster Configuration for Staged Walk-Forward Optimization.

This module defines all parameter clusters organized by stage,
as determined through systematic analysis of the JJC Bot parameters.

Version: 2.0
Date: 2026-03-04
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class Stage(Enum):
    """Optimization stages"""
    FOUNDATION = 1
    ENTRY_REFINEMENT = 2
    TIME_CONTEXT = 3
    TRADE_MANAGEMENT = 4
    EXITS_RISK = 5


@dataclass
class Cluster:
    """Definition of a parameter cluster"""
    name: str
    stage: Stage
    phase: int
    parameters: List[str]
    description: str
    priority: str = "normal"  # "critical", "normal", "low"
    test_method: str = "standard"  # "standard", "method_selection", "quick_check"
    method_param: Optional[str] = None  # For method_selection type
    method_count: Optional[int] = None  # Number of methods to test


# =============================================================================
# FIXED PARAMETERS (Never Optimize)
# =============================================================================

FIXED_PARAMETERS = {
    # Entry Type Selection (set per model)
    "BOSSTESTENUMORATOR": "Set per entry type",
    "TrendE": True,
    "TrendEW": True,
    "TrendG": True,
    "TDIbnr": True,
    "TrueShift": True,

    # Account Settings
    "Compounding": False,
    "NonCompoundingAccountSize": "Match deposit setting",
    "CalculateLots": 2,
    "RiskForAutoLotSize": 1,
    "SupAndRes": 0,

    # Fixed Logic
    "ResetAccountHour": 3,
    "ResetAccountMin": 0,
    "WaitThreeCandles": False,
    "UseHardCodeATRPeriods": True,
    "TurnOnOnceInitiated": True,
    "PushAwayMultiplier": 2,
    "LConClosure": True,
    "LCasStopOnly": True,
    "BotStatus": 0,
    "PropChallenge": False,
    "ProfitPercentage": 10,

    # FTMO Requirement
    "AvoidHighImpactNews": True,  # NEVER CHANGE

    # Visual Only
    "JakesCloud": "Visual indicator",
    "TrailingStopLossEMA": "Visual indicator",
    "PurpleChannel": "Visual indicator",
    "InpShowBase": 1,
    "InpShowVBL": 1,

    # Ignored (leave default)
    "ATRMultiplierBufferForStop": 2,
    "BBlineLength": 34,
    "BloodInTheWaterBuffer": 5,
    "CandlesCloseOutSideOfPushAway": 3,
    "MWTDIBuffer": 0,
    "MaxMWatr": 5,
    "UseBreak": True,

    # Leave off
    "AvoidMediumImpactNews": False,
    "AvoidLowImpactNews": False,
}


# =============================================================================
# STAGE 1: FOUNDATION
# =============================================================================

STAGE_1_CLUSTERS = [
    Cluster(
        name="SL_TP_Structure",
        stage=Stage.FOUNDATION,
        phase=0,
        parameters=[
            # SL Method 3 (ATR) params
            "StopLossMethod",
            "ATRPeriod",
            "ATRStopLossMultiplier",
            "UseHighLowOfPrevCandleIfStopTooTight",
            # SL Method 6 (L_O_TH) params
            "SpreadMultiplier2",
            # TP params
            "TakeProfitMethod",
            "TakeProfitStopMultiplier",  # Only used by TP=3
        ],
        description="Core SL/TP structure - test 2 SL methods × 7 TP methods",
        priority="critical",
        test_method="structure_comparison",
    ),
]

# SL/TP Method Configuration
SL_METHODS = {
    3: {
        "name": "ATR_SL",
        "params": ["ATRPeriod", "ATRStopLossMultiplier", "UseHighLowOfPrevCandleIfStopTooTight"],
    },
    6: {
        "name": "L_O_TH",
        "params": ["SpreadMultiplier2", "UseHighLowOfPrevCandleIfStopTooTight"],
    },
}

TP_METHODS = {
    0: {"name": "TP_Method_0", "params": []},
    1: {"name": "TP_Method_1", "params": []},
    2: {"name": "TP_Method_2", "params": []},
    3: {"name": "TP_Method_3", "params": ["TakeProfitStopMultiplier"]},
    4: {"name": "TP_Method_4", "params": []},
    5: {"name": "TP_Method_5", "params": []},
    6: {"name": "TP_Method_6", "params": []},
}


# =============================================================================
# STAGE 2: ENTRY REFINEMENT
# =============================================================================

STAGE_2_CLUSTERS = [
    Cluster(
        name="Candle_Size",
        stage=Stage.ENTRY_REFINEMENT,
        phase=1,
        parameters=[
            "MinCandleSize",
            "PercentOfCandle",
        ],
        description="Quick check - do candle size filters matter?",
        priority="normal",
        test_method="quick_check",
    ),

    Cluster(
        name="Room",
        stage=Stage.ENTRY_REFINEMENT,
        phase=2,
        parameters=[
            "CheckRoom",
            "Measuremet_For_Room",
            "ATRMuliplierForRoom",
            "RewardMultiplierForRoom",
        ],
        description="Room for profit target - is there space?",
        priority="critical",
    ),

    Cluster(
        name="HTF_Trend",
        stage=Stage.ENTRY_REFINEMENT,
        phase=3,
        parameters=[
            "HigherTimeFrame",
            "HigherTFTwo",
            "HTFFastEMA",
            "HTFSlowEMA",
            "TrendMethod",
        ],
        description="Higher timeframe trend alignment",
        priority="normal",
    ),

    Cluster(
        name="EMA_Angles",
        stage=Stage.ENTRY_REFINEMENT,
        phase=4,
        parameters=[
            "EMAAngleOfSlope",
            "AngleOf13",
            "AngleOf21",
            "AngleOf55",
            "AngleOfFastRSI",
            "AngleOfL50",
        ],
        description="Momentum direction via EMA slopes",
        priority="normal",
    ),

    Cluster(
        name="TDI_Filter",
        stage=Stage.ENTRY_REFINEMENT,
        phase=5,
        parameters=[
            "TDICheck",
            "InpOverbought",
            "InpOversold",
        ],
        description="TDI overbought/oversold conditions",
        priority="normal",
    ),

    Cluster(
        name="Entry_Filters",
        stage=Stage.ENTRY_REFINEMENT,
        phase=6,
        parameters=[
            "UseBBLine",
            "UsePSAR",
            "UseCloudColor",
            "BBexpand",
            "TradeScore",
        ],
        description="Various technical entry confirmations",
        priority="normal",
    ),

    Cluster(
        name="Capture_FastMove",
        stage=Stage.ENTRY_REFINEMENT,
        phase=7,
        parameters=[
            "FastMove",
            "CaptureBigCandle",
            "CaptureMultiplier",
        ],
        description="Momentum/volatility capture",
        priority="normal",
    ),

    Cluster(
        name="Liquidity_Sweep",
        stage=Stage.ENTRY_REFINEMENT,
        phase=8,
        parameters=[
            "NeedLiqSweep",
            "Session",
        ],
        description="Liquidity-based entry filtering (Session 0-4)",
        priority="normal",
    ),
]


# =============================================================================
# STAGE 3: TIME & CONTEXT
# =============================================================================

STAGE_3_CLUSTERS = [
    Cluster(
        name="Trading_Session",
        stage=Stage.TIME_CONTEXT,
        phase=9,
        parameters=[
            "StartHour",
            "StartMin",
            "EndHour",
            "EndMin",
            "IncludeBreak",
            "StartBreakHour",
            "StartBreakMin",
            "EndBreakHour",
            "EndBreakMin",
        ],
        description="Which sessions to trade - London, NY, both with break?",
        priority="normal",
    ),

    Cluster(
        name="Market_Open",
        stage=Stage.TIME_CONTEXT,
        phase=10,
        parameters=[
            "TradeDuringMarketOpen",
            "CloseTradesBeforeMarketOpen",
            "StartTradingAfterMarketOpenHour",
            "StartTradingAfterMarketOpenMin",
            "StopTradingBerforeMaketOpenHour",
            "StopTradingBerforeMaketOpenMin",
        ],
        description="Behavior around NYSE open volatility",
        priority="normal",
    ),

    Cluster(
        name="News",
        stage=Stage.TIME_CONTEXT,
        phase=11,
        parameters=[
            # AvoidHighImpactNews = TRUE (FIXED)
            "minutesBefore",
            "minutesAfter",
            "MinBeforeNewsToCloseTrades",
            "NoTradeOnStats",
        ],
        description="News avoidance timing (High impact always avoided)",
        priority="normal",
    ),
]


# =============================================================================
# STAGE 4: TRADE MANAGEMENT
# =============================================================================

STAGE_4_CLUSTERS = [
    Cluster(
        name="Break_Even",
        stage=Stage.TRADE_MANAGEMENT,
        phase=12,
        parameters=[
            "BreakEvenMethod",
            "BEProfit",
            "BreakEvenAtXPercent",
            "BreakEvenXPointsinProf",
            "BreakEvenafterXPercentOfTrade",
        ],
        description="Break even methods (11 options) - test method first, then params",
        priority="normal",
        test_method="method_selection",
        method_param="BreakEvenMethod",
        method_count=11,
    ),

    Cluster(
        name="Trail_Methods",
        stage=Stage.TRADE_MANAGEMENT,
        phase=13,
        parameters=[
            "TrailMethod",
            "ATRTrailMultiplier",
            "TrailAfterXCandles",
            "TrailSLEMA",
            "TrailafterXPercentOfTrade",
            "MoveEveryXPercent",
            # Re-test TP with trailing - trailing may benefit from extended TP
            "TakeProfitMethod",
            "TakeProfitStopMultiplier",
        ],
        description="Trailing stop methods (15 options) + re-test TP (trailing may benefit from extended TP)",
        priority="normal",
        test_method="method_selection",
        method_param="TrailMethod",
        method_count=15,
    ),

    Cluster(
        name="Close_All_Trades",
        stage=Stage.TIME_CONTEXT,
        phase=14,
        parameters=[
            "CloseAllTradesAtTime",
            "CloseAllTradesHour",
            "CloseAllTradesMinute",
        ],
        description="Force close all trades at specific time",
        priority="normal",
    ),
]


# =============================================================================
# STAGE 5: EXITS & RISK
# =============================================================================

STAGE_5_CLUSTERS = [
    Cluster(
        name="Exit_Methods",
        stage=Stage.EXITS_RISK,
        phase=15,
        parameters=[
            "KCMethod",
            "LCExit",
            "VBCMethod",
            "PushAwayExit",
            "PChanMethod",
            "OpCandleMethod",
            "BBCol",
            "ThreeCOL",
            "DojiClose",
        ],
        description="Various exit methods - low priority, test last",
        priority="low",
    ),

    Cluster(
        name="Multiple_Trades",
        stage=Stage.EXITS_RISK,
        phase=16,
        parameters=[
            "OpenMultipleTrades",
            "SameTradeTypeInBothDirection",
        ],
        description="Multiple trade handling",
        priority="low",
    ),

    Cluster(
        name="Risk_Drawdown",
        stage=Stage.EXITS_RISK,
        phase=17,
        parameters=[
            "DrawDownMethod",
            "DrawDownSetting",
            "MaxDailyLossPercent",
            "MaxDailyGainPercent",
            "UseMaxDailyLoss",
            "UseMaxDailyGain",
            "ReduceRiskAtXPercentDD",
            "RuduceEveryPercentFurther",
            "RuductionPercent",
            "UseRiskReduction",
        ],
        description="Prop firm compliance - DD and risk management",
        priority="normal",
    ),
]


# =============================================================================
# ALL CLUSTERS
# =============================================================================

ALL_CLUSTERS = (
    STAGE_1_CLUSTERS +
    STAGE_2_CLUSTERS +
    STAGE_3_CLUSTERS +
    STAGE_4_CLUSTERS +
    STAGE_5_CLUSTERS
)


def get_clusters_by_stage(stage: Stage) -> List[Cluster]:
    """Get all clusters for a specific stage"""
    return [c for c in ALL_CLUSTERS if c.stage == stage]


def get_cluster_by_name(name: str) -> Optional[Cluster]:
    """Get a specific cluster by name"""
    for c in ALL_CLUSTERS:
        if c.name == name:
            return c
    return None


def get_cluster_by_phase(phase: int) -> Optional[Cluster]:
    """Get cluster for a specific phase number"""
    for c in ALL_CLUSTERS:
        if c.phase == phase:
            return c
    return None


# =============================================================================
# ENTRY TYPES
# =============================================================================

ENTRY_TYPES = {
    "TrendEng": {"BOSSTESTENUMORATOR": 1, "magic": 3},
    "TrendEngWick": {"BOSSTESTENUMORATOR": 2, "magic": 4},
    "TrendingGray": {"BOSSTESTENUMORATOR": 5, "magic": 7},
    "TrueShift": {"BOSSTESTENUMORATOR": 8, "magic": 10},
    "TDIBnR": {"BOSSTESTENUMORATOR": 9, "magic": 11},
}


# =============================================================================
# DISPLAY
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("JJC BOT OPTIMIZATION CLUSTER CONFIGURATION")
    print("=" * 70)

    for stage in Stage:
        clusters = get_clusters_by_stage(stage)
        if clusters:
            print(f"\n{'='*70}")
            print(f"STAGE {stage.value}: {stage.name}")
            print("=" * 70)

            for cluster in clusters:
                print(f"\n  Phase {cluster.phase}: {cluster.name}")
                print(f"  Priority: {cluster.priority}")
                print(f"  Description: {cluster.description}")
                print(f"  Parameters:")
                for param in cluster.parameters:
                    print(f"    - {param}")

    print(f"\n{'='*70}")
    print(f"FIXED PARAMETERS ({len(FIXED_PARAMETERS)} total)")
    print("=" * 70)
    for param, value in list(FIXED_PARAMETERS.items())[:10]:
        print(f"  {param} = {value}")
    print(f"  ... and {len(FIXED_PARAMETERS) - 10} more")

    print(f"\n{'='*70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total Clusters: {len(ALL_CLUSTERS)}")
    print(f"  Total Phases: {max(c.phase for c in ALL_CLUSTERS) + 1}")
    print(f"  Entry Types: {len(ENTRY_TYPES)}")
