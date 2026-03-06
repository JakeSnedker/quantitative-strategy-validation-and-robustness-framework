"""
Staged Walk-Forward Optimizer.

Implements the 5-stage optimization architecture:
  Stage 1: Foundation (SL/TP structure)
  Stage 2: Entry Refinement (filters vs baseline)
  Stage 3: Time & Context (vs winning system)
  Stage 4: Trade Management (BE/Trail methods vs winning system)
  Stage 5: Exits & Risk (final adjustments)

Each stage has gates - if no edge is found, optimization stops.
Compounding: Stage 2 tests vs baseline, Stage 3+ tests vs winning system.

Version: 1.0
Date: 2026-03-04
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from cluster_config import (
    Stage,
    Cluster,
    ALL_CLUSTERS,
    STAGE_1_CLUSTERS,
    STAGE_2_CLUSTERS,
    STAGE_3_CLUSTERS,
    STAGE_4_CLUSTERS,
    STAGE_5_CLUSTERS,
    FIXED_PARAMETERS,
    ENTRY_TYPES,
    SL_METHODS,
    TP_METHODS,
    get_clusters_by_stage,
    get_cluster_by_phase,
)
from walk_forward_config import (
    WalkForwardConfig,
    WalkForwardSettings,
    PassFailCriteria,
    PassFailStatus,
    OptimizationParameter,
    get_default_config,
)
from walk_forward_optimizer import (
    WalkForwardOptimizer,
    WalkForwardReport,
    WindowResult,
)
from set_file_generator import SetFileGenerator, ENTRY_TYPES as SET_ENTRY_TYPES
from config import get_config


class StageGateResult(Enum):
    """Result of a stage gate evaluation"""
    PASS = "PASS"           # Edge found, proceed to next stage
    FAIL = "FAIL"           # No edge, stop optimization
    MARGINAL = "MARGINAL"   # Borderline, can proceed with caution


@dataclass
class PhaseResult:
    """Results from optimizing a single phase/cluster"""
    phase: int
    cluster_name: str
    stage: Stage

    # Walk-forward results
    walk_forward_report: Optional[WalkForwardReport] = None

    # Comparison to baseline/previous
    baseline_pf: float = 0.0
    optimized_pf: float = 0.0
    improvement_percent: float = 0.0

    # Best parameters found
    best_params: Dict[str, Any] = field(default_factory=dict)

    # Status
    success: bool = False
    has_edge: bool = False
    error: Optional[str] = None

    # Timing
    duration_seconds: float = 0.0


@dataclass
class StageResult:
    """Results from a complete stage"""
    stage: Stage
    phases: List[PhaseResult] = field(default_factory=list)

    # Aggregated best params from all phases in this stage
    cumulative_params: Dict[str, Any] = field(default_factory=dict)

    # Gate result
    gate_result: StageGateResult = StageGateResult.FAIL
    gate_pf: float = 0.0
    gate_baseline_pf: float = 0.0

    # Should we continue to next stage?
    proceed: bool = False

    duration_seconds: float = 0.0


@dataclass
class StagedOptimizationReport:
    """Complete staged optimization report"""
    entry_type: str
    started_at: str = ""
    completed_at: str = ""

    # Stage results
    stages: Dict[str, StageResult] = field(default_factory=dict)

    # Final status
    final_status: PassFailStatus = PassFailStatus.FAIL
    final_params: Dict[str, Any] = field(default_factory=dict)
    final_pf: float = 0.0
    final_drawdown: float = 0.0

    # Gate that stopped us (if any)
    stopped_at_stage: Optional[Stage] = None
    stop_reason: Optional[str] = None

    total_duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "entry_type": self.entry_type,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "final_status": self.final_status.value,
            "final_params": self.final_params,
            "final_pf": self.final_pf,
            "final_drawdown": self.final_drawdown,
            "stopped_at_stage": self.stopped_at_stage.name if self.stopped_at_stage else None,
            "stop_reason": self.stop_reason,
            "total_duration_seconds": self.total_duration_seconds,
            "stages": {},
        }

        for stage_name, stage_result in self.stages.items():
            result["stages"][stage_name] = {
                "gate_result": stage_result.gate_result.value,
                "gate_pf": stage_result.gate_pf,
                "cumulative_params": stage_result.cumulative_params,
                "proceed": stage_result.proceed,
                "duration_seconds": stage_result.duration_seconds,
                "phases": [
                    {
                        "phase": p.phase,
                        "cluster_name": p.cluster_name,
                        "optimized_pf": p.optimized_pf,
                        "baseline_pf": p.baseline_pf,
                        "improvement_percent": p.improvement_percent,
                        "has_edge": p.has_edge,
                        "best_params": p.best_params,
                        "success": p.success,
                        "error": p.error,
                    }
                    for p in stage_result.phases
                ]
            }

        return result

    def to_summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            "=" * 70,
            f"STAGED OPTIMIZATION REPORT: {self.entry_type}",
            "=" * 70,
            "",
            f"Final Status: {self.final_status.value}",
            f"Final PF: {self.final_pf:.3f}",
            f"Final Max DD: {self.final_drawdown:.2f}%",
            f"Duration: {self.total_duration_seconds / 60:.1f} minutes",
            "",
        ]

        if self.stopped_at_stage:
            lines.append(f"STOPPED AT: Stage {self.stopped_at_stage.value} - {self.stopped_at_stage.name}")
            lines.append(f"Reason: {self.stop_reason}")
            lines.append("")

        lines.append("STAGE RESULTS:")
        lines.append("-" * 70)

        for stage in Stage:
            stage_name = stage.name
            if stage_name in self.stages:
                sr = self.stages[stage_name]
                gate_icon = "[PASS]" if sr.gate_result == StageGateResult.PASS else (
                    "[MARG]" if sr.gate_result == StageGateResult.MARGINAL else "[FAIL]"
                )
                lines.append(f"\nStage {stage.value}: {stage_name} {gate_icon}")
                lines.append(f"  Gate PF: {sr.gate_pf:.3f} (baseline: {sr.gate_baseline_pf:.3f})")
                lines.append(f"  Proceed: {'Yes' if sr.proceed else 'No'}")

                for phase in sr.phases:
                    phase_icon = "[+]" if phase.has_edge else "[-]"
                    lines.append(f"    Phase {phase.phase}: {phase.cluster_name} {phase_icon}")
                    lines.append(f"      PF: {phase.optimized_pf:.3f} vs baseline {phase.baseline_pf:.3f} "
                               f"({phase.improvement_percent:+.1f}%)")

        lines.append("")
        lines.append("-" * 70)
        lines.append("FINAL PARAMETERS:")
        lines.append("-" * 70)
        for name, value in sorted(self.final_params.items()):
            lines.append(f"  {name}: {value}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)


class StagedOptimizer:
    """
    Staged walk-forward optimization engine.

    Implements the 5-stage architecture with gates and compounding.
    """

    # Gate thresholds
    STAGE_1_MIN_PF = 0.9      # Foundation: must be at least marginally viable
    STAGE_2_MIN_IMPROVEMENT = 0.05  # Entry filters: must improve PF by 5%
    STAGE_3_MIN_IMPROVEMENT = 0.02  # Time/Context: must improve PF by 2%
    STAGE_4_MIN_IMPROVEMENT = 0.02  # Trade Management: must improve PF by 2%
    STAGE_5_MIN_IMPROVEMENT = 0.0   # Exits: any improvement OK

    def __init__(
        self,
        entry_type: str,
        start_date: str = "2024.07.01",
        end_date: str = "2025.12.31",
        output_dir: str = "results",
    ):
        """
        Initialize the staged optimizer.

        Args:
            entry_type: One of the ENTRY_TYPES (TrendEng, TrendEngWick, etc.)
            start_date: Overall data start date (YYYY.MM.DD)
            end_date: Overall data end date (YYYY.MM.DD)
            output_dir: Directory to save results
        """
        self.entry_type = entry_type
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = Path(output_dir)

        # Current cumulative parameters (starts with fixed + baseline)
        self.current_params: Dict[str, Any] = {}

        # Report
        self.report = StagedOptimizationReport(entry_type=entry_type)

        # Baseline PF (established in Stage 1)
        self.baseline_pf: float = 0.0

        # .set file management
        self.set_generator = SetFileGenerator()
        self._setup_set_file_paths()

    def _setup_set_file_paths(self):
        """Setup paths for .set file generation"""
        config = get_config()
        self.set_file_dir = Path(config.mt5.data_path) / "MQL5" / "Profiles" / "Tester"
        self.set_file_dir.mkdir(parents=True, exist_ok=True)

        # Current .set file path (updated after each stage)
        self.current_set_file = self.set_file_dir / f"staged_{self.entry_type}_current.set"

        # Stage-specific .set files for history/debugging
        self.stage_set_files: Dict[str, Path] = {}

    def _write_stage_set_file(self, stage: Stage) -> Path:
        """
        Write .set file with current winning parameters after a stage completes.

        Args:
            stage: The stage that just completed

        Returns:
            Path to the generated .set file
        """
        # Update generator with current params
        self.set_generator.update_params(self.current_params)

        # Write stage-specific .set file (for history)
        stage_filename = f"staged_{self.entry_type}_stage{stage.value}_{stage.name.lower()}.set"
        stage_set_path = self.set_file_dir / stage_filename

        self.set_generator.generate(
            str(stage_set_path),
            comment=f"Stage {stage.value} ({stage.name}) winning parameters for {self.entry_type}"
        )
        self.stage_set_files[stage.name] = stage_set_path

        # Also update the "current" .set file (used by next stage)
        self.set_generator.generate(
            str(self.current_set_file),
            comment=f"Current winning parameters after Stage {stage.value} for {self.entry_type}"
        )

        print(f"\n[SET FILE] Written: {stage_set_path.name}")
        print(f"[SET FILE] Current: {self.current_set_file.name}")

        return stage_set_path

    def _write_final_set_file(self) -> Path:
        """
        Write the final .set file with all winning parameters.

        Returns:
            Path to the final .set file
        """
        # Update generator with final params
        self.set_generator.update_params(self.current_params)

        # Write final .set file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"staged_{self.entry_type}_FINAL_{timestamp}.set"
        final_set_path = self.set_file_dir / final_filename

        self.set_generator.generate(
            str(final_set_path),
            comment=f"FINAL optimized parameters for {self.entry_type} - {self.report.final_status.value}"
        )

        # Also copy to a predictable "latest" filename
        latest_set_path = self.set_file_dir / f"staged_{self.entry_type}_LATEST.set"
        self.set_generator.generate(
            str(latest_set_path),
            comment=f"LATEST optimized parameters for {self.entry_type}"
        )

        print(f"\n[SET FILE] FINAL: {final_set_path.name}")
        print(f"[SET FILE] LATEST: {latest_set_path.name}")

        return final_set_path

    def run(self) -> StagedOptimizationReport:
        """
        Execute the full staged optimization.

        Returns:
            StagedOptimizationReport with all results
        """
        start_time = time.time()
        self.report.started_at = datetime.now().isoformat()

        print("=" * 70)
        print(f"STAGED OPTIMIZATION: {self.entry_type}")
        print(f"Period: {self.start_date} to {self.end_date}")
        print("=" * 70)

        # Initialize with fixed parameters
        self._initialize_params()

        # Run each stage in order
        stages = [
            (Stage.FOUNDATION, self._run_stage_1_foundation),
            (Stage.ENTRY_REFINEMENT, self._run_stage_2_entry_refinement),
            (Stage.TIME_CONTEXT, self._run_stage_3_time_context),
            (Stage.TRADE_MANAGEMENT, self._run_stage_4_trade_management),
            (Stage.EXITS_RISK, self._run_stage_5_exits_risk),
        ]

        for stage, run_func in stages:
            print(f"\n{'='*70}")
            print(f"STAGE {stage.value}: {stage.name}")
            print("=" * 70)

            stage_result = run_func()
            self.report.stages[stage.name] = stage_result

            # Check gate
            if not stage_result.proceed:
                self.report.stopped_at_stage = stage
                self.report.stop_reason = f"Gate failed at Stage {stage.value}: {stage.name}"
                print(f"\n[GATE FAILED] Stopping at Stage {stage.value}")
                # Still write .set file with whatever we have
                self._write_stage_set_file(stage)
                break

            # Update cumulative params
            self.current_params.update(stage_result.cumulative_params)

            # Write .set file with winning params from this stage
            self._write_stage_set_file(stage)

            print(f"\n[GATE PASSED] Proceeding to next stage")

        # Finalize report
        self.report.completed_at = datetime.now().isoformat()
        self.report.total_duration_seconds = time.time() - start_time
        self.report.final_params = self.current_params.copy()

        # Set final status based on how far we got
        if self.report.stopped_at_stage is None:
            # Made it through all stages
            if self.report.stages.get(Stage.EXITS_RISK.name):
                final_stage = self.report.stages[Stage.EXITS_RISK.name]
                self.report.final_pf = final_stage.gate_pf
                if final_stage.gate_result == StageGateResult.PASS:
                    self.report.final_status = PassFailStatus.PASS
                elif final_stage.gate_result == StageGateResult.MARGINAL:
                    self.report.final_status = PassFailStatus.MARGINAL
                else:
                    self.report.final_status = PassFailStatus.FAIL
        else:
            self.report.final_status = PassFailStatus.FAIL

        # Write FINAL .set file with all winning parameters
        final_set_path = self._write_final_set_file()
        print(f"\n{'='*70}")
        print(f"FINAL .SET FILE READY FOR USE:")
        print(f"  {final_set_path}")
        print(f"{'='*70}")

        # Save report
        self._save_report()

        print("\n" + self.report.to_summary())

        return self.report

    def _initialize_params(self):
        """Initialize with fixed parameters and entry type"""
        # Start with fixed params
        for name, value in FIXED_PARAMETERS.items():
            if isinstance(value, (int, float, bool)):
                self.current_params[name] = value

        # Set entry type
        entry_info = ENTRY_TYPES[self.entry_type]
        self.current_params["BOSSTESTENUMORATOR"] = entry_info["BOSSTESTENUMORATOR"]

        # Baseline settings (all filters off, no trade management)
        baseline_overrides = {
            # Filters OFF
            "CheckRoom": False,
            "EMAAngleOfSlope": False,
            "TDICheck": False,
            "UseBBLine": False,
            "UsePSAR": False,
            "UseCloudColor": False,
            "BBexpand": False,
            "FastMove": False,
            "CaptureBigCandle": False,
            "NeedLiqSweep": False,

            # Trade Management OFF
            "BreakEvenMethod": 0,
            "TrailMethod": 0,

            # Basic SL/TP (will be optimized in Stage 1)
            "StopLossMethod": 3,  # ATR
            "TakeProfitMethod": 3,  # R:R multiplier
            "ATRStopLossMultiplier": 2.0,
            "TakeProfitStopMultiplier": 2.0,
        }
        self.current_params.update(baseline_overrides)

    def _run_stage_1_foundation(self) -> StageResult:
        """
        Stage 1: Foundation - Find best SL/TP structure.

        Tests 2 SL methods × 7 TP methods = 14 combinations.
        """
        stage_start = time.time()
        stage_result = StageResult(stage=Stage.FOUNDATION)

        print("\nTesting SL/TP method combinations...")

        # Test each SL/TP combination
        best_combination = None
        best_pf = 0.0

        sl_methods = list(SL_METHODS.keys())  # [3, 6]
        tp_methods = list(TP_METHODS.keys())  # [0, 1, 2, 3, 4, 5, 6]

        combination_results = []

        for sl_method in sl_methods:
            for tp_method in tp_methods:
                combo_name = f"SL{sl_method}_TP{tp_method}"
                print(f"\n  Testing {combo_name}...")

                # Build params for this combination
                test_params = self.current_params.copy()
                test_params["StopLossMethod"] = sl_method
                test_params["TakeProfitMethod"] = tp_method

                # Set up optimization params based on SL/TP methods
                opt_params = []

                # SL method params
                sl_config = SL_METHODS[sl_method]
                for param_name in sl_config["params"]:
                    opt_params.append(self._get_param_range(param_name))

                # TP method params
                tp_config = TP_METHODS[tp_method]
                for param_name in tp_config["params"]:
                    opt_params.append(self._get_param_range(param_name))

                # If no variable params, just run backtest with fixed settings
                if not opt_params:
                    # Add a dummy param range (e.g., ATRPeriod)
                    opt_params.append(OptimizationParameter(
                        name="ATRPeriod",
                        start=14, stop=14, step=1,
                        description="Fixed ATR period"
                    ))

                # Run walk-forward
                wf_report = self._run_walk_forward(
                    phase_name=combo_name,
                    base_params=test_params,
                    opt_params=opt_params,
                )

                result_pf = wf_report.combined_forward_pf if wf_report else 0.0

                combination_results.append({
                    "sl_method": sl_method,
                    "tp_method": tp_method,
                    "name": combo_name,
                    "pf": result_pf,
                    "report": wf_report,
                })

                print(f"    Result: PF = {result_pf:.3f}")

                if result_pf > best_pf:
                    best_pf = result_pf
                    best_combination = {
                        "StopLossMethod": sl_method,
                        "TakeProfitMethod": tp_method,
                    }
                    if wf_report and wf_report.recommended_params:
                        best_combination.update(wf_report.recommended_params)

        # Create phase result
        phase_result = PhaseResult(
            phase=0,
            cluster_name="SL_TP_Structure",
            stage=Stage.FOUNDATION,
            optimized_pf=best_pf,
            baseline_pf=0.0,  # No baseline for Stage 1
            improvement_percent=0.0,
            best_params=best_combination or {},
            success=best_pf > 0,
            has_edge=best_pf >= self.STAGE_1_MIN_PF,
        )
        stage_result.phases.append(phase_result)

        # Set baseline for future stages
        self.baseline_pf = best_pf

        # Gate evaluation
        if best_pf >= self.STAGE_1_MIN_PF:
            stage_result.gate_result = StageGateResult.PASS
            stage_result.proceed = True
            stage_result.cumulative_params = best_combination or {}
        else:
            stage_result.gate_result = StageGateResult.FAIL
            stage_result.proceed = False

        stage_result.gate_pf = best_pf
        stage_result.gate_baseline_pf = 0.0
        stage_result.duration_seconds = time.time() - stage_start

        print(f"\nStage 1 Complete: Best PF = {best_pf:.3f}")
        print(f"Best combination: SL={best_combination.get('StopLossMethod')}, "
              f"TP={best_combination.get('TakeProfitMethod')}")

        return stage_result

    def _run_stage_2_entry_refinement(self) -> StageResult:
        """
        Stage 2: Entry Refinement - Test filters against baseline.

        Each filter is tested individually against baseline.
        Only filters that improve PF are kept.
        """
        stage_start = time.time()
        stage_result = StageResult(stage=Stage.ENTRY_REFINEMENT)

        clusters = get_clusters_by_stage(Stage.ENTRY_REFINEMENT)
        winning_params = {}

        for cluster in clusters:
            print(f"\n--- Phase {cluster.phase}: {cluster.name} ---")
            print(f"Description: {cluster.description}")

            phase_result = self._test_cluster_vs_baseline(cluster)
            stage_result.phases.append(phase_result)

            # If this cluster improves PF, add its params
            if phase_result.has_edge:
                print(f"  [+] Edge found! Adding params to winning system")
                winning_params.update(phase_result.best_params)
            else:
                print(f"  [-] No edge, keeping baseline settings")

        # Gate evaluation: Did we improve overall?
        # Test the combined winning params
        if winning_params:
            print("\nTesting combined winning filters...")
            combined_params = self.current_params.copy()
            combined_params.update(winning_params)

            combined_pf = self._test_params_quick(combined_params)
            improvement = (combined_pf - self.baseline_pf) / self.baseline_pf if self.baseline_pf > 0 else 0

            print(f"Combined PF: {combined_pf:.3f} (baseline: {self.baseline_pf:.3f})")
            print(f"Improvement: {improvement*100:.1f}%")

            if improvement >= self.STAGE_2_MIN_IMPROVEMENT:
                stage_result.gate_result = StageGateResult.PASS
                stage_result.proceed = True
                stage_result.cumulative_params = winning_params
                self.baseline_pf = combined_pf  # Update baseline for next stage
            elif improvement >= 0:
                stage_result.gate_result = StageGateResult.MARGINAL
                stage_result.proceed = True
                stage_result.cumulative_params = winning_params
                self.baseline_pf = combined_pf
            else:
                stage_result.gate_result = StageGateResult.FAIL
                stage_result.proceed = False

            stage_result.gate_pf = combined_pf
        else:
            # No filters improved, proceed with baseline
            stage_result.gate_result = StageGateResult.MARGINAL
            stage_result.proceed = True
            stage_result.gate_pf = self.baseline_pf

        stage_result.gate_baseline_pf = self.baseline_pf
        stage_result.duration_seconds = time.time() - stage_start

        return stage_result

    def _run_stage_3_time_context(self) -> StageResult:
        """
        Stage 3: Time & Context - Test vs winning system (not baseline).

        Session times, market open behavior, news timing.
        """
        stage_start = time.time()
        stage_result = StageResult(stage=Stage.TIME_CONTEXT)

        clusters = get_clusters_by_stage(Stage.TIME_CONTEXT)
        winning_params = {}
        current_pf = self.baseline_pf

        for cluster in clusters:
            print(f"\n--- Phase {cluster.phase}: {cluster.name} ---")
            print(f"Description: {cluster.description}")

            # Test vs current winning system
            phase_result = self._test_cluster_vs_current(cluster, current_pf)
            stage_result.phases.append(phase_result)

            if phase_result.has_edge:
                print(f"  [+] Edge found! Adding params")
                winning_params.update(phase_result.best_params)
                current_pf = phase_result.optimized_pf
            else:
                print(f"  [-] No edge, keeping current settings")

        # Gate evaluation
        improvement = (current_pf - self.baseline_pf) / self.baseline_pf if self.baseline_pf > 0 else 0

        if improvement >= self.STAGE_3_MIN_IMPROVEMENT:
            stage_result.gate_result = StageGateResult.PASS
            stage_result.proceed = True
        elif improvement >= 0:
            stage_result.gate_result = StageGateResult.MARGINAL
            stage_result.proceed = True
        else:
            stage_result.gate_result = StageGateResult.FAIL
            stage_result.proceed = False

        stage_result.cumulative_params = winning_params
        stage_result.gate_pf = current_pf
        stage_result.gate_baseline_pf = self.baseline_pf
        stage_result.duration_seconds = time.time() - stage_start

        self.baseline_pf = current_pf  # Update for next stage

        return stage_result

    def _run_stage_4_trade_management(self) -> StageResult:
        """
        Stage 4: Trade Management - BreakEven and Trail methods.

        Uses method_selection approach: test all methods, then optimize params.
        """
        stage_start = time.time()
        stage_result = StageResult(stage=Stage.TRADE_MANAGEMENT)

        clusters = get_clusters_by_stage(Stage.TRADE_MANAGEMENT)
        winning_params = {}
        current_pf = self.baseline_pf

        for cluster in clusters:
            print(f"\n--- Phase {cluster.phase}: {cluster.name} ---")
            print(f"Description: {cluster.description}")

            if cluster.test_method == "method_selection":
                # Special handling for method selection
                phase_result = self._test_method_selection(
                    cluster,
                    current_pf
                )
            else:
                phase_result = self._test_cluster_vs_current(cluster, current_pf)

            stage_result.phases.append(phase_result)

            if phase_result.has_edge:
                print(f"  [+] Edge found! Adding params")
                winning_params.update(phase_result.best_params)
                current_pf = phase_result.optimized_pf
            else:
                print(f"  [-] No edge, keeping current settings")

        # Gate evaluation
        improvement = (current_pf - self.baseline_pf) / self.baseline_pf if self.baseline_pf > 0 else 0

        if improvement >= self.STAGE_4_MIN_IMPROVEMENT:
            stage_result.gate_result = StageGateResult.PASS
            stage_result.proceed = True
        elif improvement >= 0:
            stage_result.gate_result = StageGateResult.MARGINAL
            stage_result.proceed = True
        else:
            stage_result.gate_result = StageGateResult.FAIL
            stage_result.proceed = False

        stage_result.cumulative_params = winning_params
        stage_result.gate_pf = current_pf
        stage_result.gate_baseline_pf = self.baseline_pf
        stage_result.duration_seconds = time.time() - stage_start

        self.baseline_pf = current_pf

        return stage_result

    def _run_stage_5_exits_risk(self) -> StageResult:
        """
        Stage 5: Exits & Risk - Final adjustments.

        Exit methods and risk/drawdown management.
        """
        stage_start = time.time()
        stage_result = StageResult(stage=Stage.EXITS_RISK)

        clusters = get_clusters_by_stage(Stage.EXITS_RISK)
        winning_params = {}
        current_pf = self.baseline_pf

        for cluster in clusters:
            print(f"\n--- Phase {cluster.phase}: {cluster.name} ---")
            print(f"Description: {cluster.description}")

            # Low priority clusters can be skipped if time constrained
            if cluster.priority == "low":
                print(f"  [SKIP] Low priority cluster")
                continue

            phase_result = self._test_cluster_vs_current(cluster, current_pf)
            stage_result.phases.append(phase_result)

            if phase_result.has_edge:
                print(f"  [+] Edge found! Adding params")
                winning_params.update(phase_result.best_params)
                current_pf = phase_result.optimized_pf
            else:
                print(f"  [-] No edge, keeping current settings")

        # Stage 5 gate is lenient - any non-negative improvement OK
        improvement = (current_pf - self.baseline_pf) / self.baseline_pf if self.baseline_pf > 0 else 0

        if improvement >= self.STAGE_5_MIN_IMPROVEMENT:
            stage_result.gate_result = StageGateResult.PASS
            stage_result.proceed = True
        else:
            stage_result.gate_result = StageGateResult.MARGINAL
            stage_result.proceed = True  # Always proceed from final stage

        stage_result.cumulative_params = winning_params
        stage_result.gate_pf = current_pf
        stage_result.gate_baseline_pf = self.baseline_pf
        stage_result.duration_seconds = time.time() - stage_start

        return stage_result

    def _test_cluster_vs_baseline(self, cluster: Cluster) -> PhaseResult:
        """Test a cluster against baseline (Stage 2 approach)"""
        phase_start = time.time()

        # Build optimization params
        opt_params = []
        for param_name in cluster.parameters:
            opt_params.append(self._get_param_range(param_name))

        # Run walk-forward with cluster params
        wf_report = self._run_walk_forward(
            phase_name=cluster.name,
            base_params=self.current_params,
            opt_params=opt_params,
        )

        optimized_pf = wf_report.combined_forward_pf if wf_report else 0.0
        improvement = (optimized_pf - self.baseline_pf) / self.baseline_pf if self.baseline_pf > 0 else 0

        return PhaseResult(
            phase=cluster.phase,
            cluster_name=cluster.name,
            stage=cluster.stage,
            walk_forward_report=wf_report,
            baseline_pf=self.baseline_pf,
            optimized_pf=optimized_pf,
            improvement_percent=improvement * 100,
            best_params=wf_report.recommended_params if wf_report else {},
            success=wf_report is not None,
            has_edge=improvement > 0.02,  # 2% improvement threshold
            duration_seconds=time.time() - phase_start,
        )

    def _test_cluster_vs_current(self, cluster: Cluster, current_pf: float) -> PhaseResult:
        """Test a cluster against current winning system (Stage 3+ approach)"""
        phase_start = time.time()

        # Build optimization params
        opt_params = []
        for param_name in cluster.parameters:
            opt_params.append(self._get_param_range(param_name))

        # Run walk-forward with cluster params ON TOP of current params
        wf_report = self._run_walk_forward(
            phase_name=cluster.name,
            base_params=self.current_params,
            opt_params=opt_params,
        )

        optimized_pf = wf_report.combined_forward_pf if wf_report else 0.0
        improvement = (optimized_pf - current_pf) / current_pf if current_pf > 0 else 0

        return PhaseResult(
            phase=cluster.phase,
            cluster_name=cluster.name,
            stage=cluster.stage,
            walk_forward_report=wf_report,
            baseline_pf=current_pf,
            optimized_pf=optimized_pf,
            improvement_percent=improvement * 100,
            best_params=wf_report.recommended_params if wf_report else {},
            success=wf_report is not None,
            has_edge=improvement > 0.01,  # 1% improvement for later stages
            duration_seconds=time.time() - phase_start,
        )

    def _test_method_selection(self, cluster: Cluster, current_pf: float) -> PhaseResult:
        """
        Test multiple method values, then optimize params for best method.

        Used for BreakEven (11 methods) and Trail (15 methods).
        """
        phase_start = time.time()

        method_param = cluster.method_param
        method_count = cluster.method_count

        print(f"  Testing {method_count} methods for {method_param}...")

        best_method = 0
        best_method_pf = current_pf

        # Test each method
        for method_value in range(method_count):
            test_params = self.current_params.copy()
            test_params[method_param] = method_value

            method_pf = self._test_params_quick(test_params)
            print(f"    Method {method_value}: PF = {method_pf:.3f}")

            if method_pf > best_method_pf:
                best_method_pf = method_pf
                best_method = method_value

        print(f"  Best method: {best_method} with PF = {best_method_pf:.3f}")

        if best_method == 0:
            # Method 0 is usually "off" - no edge from this cluster
            return PhaseResult(
                phase=cluster.phase,
                cluster_name=cluster.name,
                stage=cluster.stage,
                baseline_pf=current_pf,
                optimized_pf=current_pf,
                improvement_percent=0.0,
                best_params={method_param: 0},
                success=True,
                has_edge=False,
                duration_seconds=time.time() - phase_start,
            )

        # Optimize params for the best method
        opt_params = []
        for param_name in cluster.parameters:
            if param_name != method_param:
                opt_params.append(self._get_param_range(param_name))

        # Set the method and run walk-forward on remaining params
        test_base_params = self.current_params.copy()
        test_base_params[method_param] = best_method

        if opt_params:
            wf_report = self._run_walk_forward(
                phase_name=f"{cluster.name}_method{best_method}",
                base_params=test_base_params,
                opt_params=opt_params,
            )
            optimized_pf = wf_report.combined_forward_pf if wf_report else best_method_pf
            best_params = wf_report.recommended_params if wf_report else {}
        else:
            optimized_pf = best_method_pf
            best_params = {}
            wf_report = None

        best_params[method_param] = best_method
        improvement = (optimized_pf - current_pf) / current_pf if current_pf > 0 else 0

        return PhaseResult(
            phase=cluster.phase,
            cluster_name=cluster.name,
            stage=cluster.stage,
            walk_forward_report=wf_report,
            baseline_pf=current_pf,
            optimized_pf=optimized_pf,
            improvement_percent=improvement * 100,
            best_params=best_params,
            success=True,
            has_edge=improvement > 0.01,
            duration_seconds=time.time() - phase_start,
        )

    def _run_walk_forward(
        self,
        phase_name: str,
        base_params: Dict[str, Any],
        opt_params: List[OptimizationParameter],
    ) -> Optional[WalkForwardReport]:
        """Run walk-forward optimization for given parameters"""
        try:
            # Generate .set file with:
            # 1. All base_params as FIXED values
            # 2. opt_params with optimization ranges
            set_file_path = self._generate_phase_set_file(phase_name, base_params, opt_params)

            # Create config
            config = WalkForwardConfig(
                entry_type=self.entry_type,
                start_date=self.start_date,
                end_date=self.end_date,
                walk_forward=WalkForwardSettings(
                    optimization_months=4,
                    forward_months=2,
                    step_months=2,
                ),
                criteria=PassFailCriteria(),
                params=opt_params,
            )

            # Validate
            errors = config.validate()
            if errors:
                print(f"    Config errors: {errors}")
                return None

            # Run optimizer with base_params from previous stages
            optimizer = WalkForwardOptimizer(config, base_params=base_params)

            # Set the .set file path for MT5 to use
            optimizer.set_file_path = set_file_path

            report = optimizer.run()

            # Save intermediate report
            output_path = self.output_dir / f"{self.entry_type}_{phase_name}"
            output_path.mkdir(parents=True, exist_ok=True)
            optimizer.save_report(str(output_path))

            return report

        except Exception as e:
            print(f"    Walk-forward error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_phase_set_file(
        self,
        phase_name: str,
        base_params: Dict[str, Any],
        opt_params: List[OptimizationParameter],
    ) -> Path:
        """
        Generate a .set file for a specific phase with:
        - Base params as FIXED values
        - Optimization params with ranges

        Args:
            phase_name: Name of the phase (for filename)
            base_params: Fixed parameters from previous stages
            opt_params: Parameters to optimize in this phase

        Returns:
            Path to the generated .set file
        """
        # Start with default params
        generator = SetFileGenerator()

        # Apply all base/fixed params
        generator.update_params(base_params)

        # Generate filename
        set_filename = f"staged_{self.entry_type}_{phase_name}.set"
        set_path = self.set_file_dir / set_filename

        # Write the .set file
        # Note: The optimization ranges will be written by mt5_optimization
        # Here we just set the base values
        generator.generate(
            str(set_path),
            comment=f"Phase: {phase_name} - Base params with {len(opt_params)} params to optimize"
        )

        print(f"    [SET FILE] Phase config: {set_filename}")
        return set_path

    def _test_params_quick(self, params: Dict[str, Any]) -> float:
        """
        Quick backtest to get approximate PF for parameter set.

        This is a simplified version for method comparison.
        In production, you'd run a proper backtest.
        """
        # TODO: Implement quick backtest
        # For now, return a placeholder
        # In production, this would call MT5 for a single backtest
        return 1.0

    def _get_param_range(self, param_name: str) -> OptimizationParameter:
        """Get default optimization range for a parameter"""
        # Default ranges for common parameters
        default_ranges = {
            # SL/TP
            "ATRPeriod": (10, 2, 20),
            "ATRStopLossMultiplier": (1.0, 0.5, 3.5),
            "TakeProfitStopMultiplier": (1.5, 0.5, 4.0),
            "SpreadMultiplier2": (1.0, 0.5, 3.0),
            "UseHighLowOfPrevCandleIfStopTooTight": (0, 1, 1),  # bool

            # Entry filters
            "MinCandleSize": (5, 5, 20),
            "PercentOfCandle": (30, 10, 70),
            "CheckRoom": (0, 1, 1),
            "ATRMuliplierForRoom": (1.0, 0.5, 3.0),
            "RewardMultiplierForRoom": (1.0, 0.5, 2.5),

            # HTF
            "HigherTimeFrame": (5, 1, 15),  # M5, M15, H1, etc.
            "HigherTFTwo": (15, 1, 60),
            "HTFFastEMA": (8, 2, 21),
            "HTFSlowEMA": (21, 5, 55),
            "TrendMethod": (0, 1, 5),

            # EMA Angles
            "EMAAngleOfSlope": (0, 1, 1),
            "AngleOf13": (10, 5, 30),
            "AngleOf21": (10, 5, 30),
            "AngleOf55": (5, 5, 20),
            "AngleOfFastRSI": (5, 5, 20),
            "AngleOfL50": (5, 5, 20),

            # TDI
            "TDICheck": (0, 1, 1),
            "InpOverbought": (60, 5, 80),
            "InpOversold": (40, 5, 20),

            # Other filters
            "UseBBLine": (0, 1, 1),
            "UsePSAR": (0, 1, 1),
            "UseCloudColor": (0, 1, 1),
            "BBexpand": (0, 1, 1),
            "TradeScore": (0, 1, 5),
            "FastMove": (0, 1, 1),
            "CaptureBigCandle": (0, 1, 1),
            "CaptureMultiplier": (1.5, 0.5, 3.0),
            "NeedLiqSweep": (0, 1, 1),
            "Session": (0, 1, 4),

            # Time
            "StartHour": (7, 1, 12),
            "StartMin": (0, 15, 45),
            "EndHour": (20, 1, 23),
            "EndMin": (0, 15, 45),
            "IncludeBreak": (0, 1, 1),

            # Trade Management
            "BreakEvenMethod": (0, 1, 10),
            "BEProfit": (5, 5, 30),
            "BreakEvenAtXPercent": (30, 10, 70),
            "TrailMethod": (0, 1, 14),
            "ATRTrailMultiplier": (1.0, 0.5, 2.5),
            "TrailAfterXCandles": (3, 1, 10),

            # News
            "minutesBefore": (15, 5, 60),
            "minutesAfter": (15, 5, 60),
            "MinBeforeNewsToCloseTrades": (5, 5, 30),
            "NoTradeOnStats": (0, 1, 1),

            # Risk
            "MaxDailyLossPercent": (4, 1, 5),
            "MaxDailyGainPercent": (3, 1, 5),
            "UseMaxDailyLoss": (0, 1, 1),
            "UseMaxDailyGain": (0, 1, 1),
            "DrawDownMethod": (0, 1, 3),
            "DrawDownSetting": (5, 1, 10),
        }

        if param_name in default_ranges:
            start, step, stop = default_ranges[param_name]
            return OptimizationParameter(
                name=param_name,
                start=start,
                stop=stop,
                step=step,
                description=f"Optimization range for {param_name}"
            )
        else:
            # Default: treat as boolean
            return OptimizationParameter(
                name=param_name,
                start=0,
                stop=1,
                step=1,
                description=f"Binary toggle for {param_name}"
            )

    def _save_report(self):
        """Save the final report to disk"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"staged_report_{self.entry_type}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(self.report.to_dict(), f, indent=2)

        print(f"\nReport saved to: {filepath}")

        # Also save summary
        summary_file = self.output_dir / f"staged_summary_{self.entry_type}_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(self.report.to_summary())


def run_staged_optimization(
    entry_type: str,
    start_date: str = "2024.07.01",
    end_date: str = "2025.12.31",
    output_dir: str = "results",
) -> StagedOptimizationReport:
    """
    Convenience function to run staged optimization.

    Args:
        entry_type: Entry pattern name
        start_date: Overall data start date
        end_date: Overall data end date
        output_dir: Directory to save reports

    Returns:
        StagedOptimizationReport with results
    """
    optimizer = StagedOptimizer(
        entry_type=entry_type,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
    )
    return optimizer.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Staged Walk-Forward Optimizer")
    parser.add_argument("entry", choices=list(ENTRY_TYPES.keys()),
                       help="Entry type to optimize")
    parser.add_argument("--start", default="2024.07.01",
                       help="Start date (YYYY.MM.DD)")
    parser.add_argument("--end", default="2025.12.31",
                       help="End date (YYYY.MM.DD)")
    parser.add_argument("-o", "--output", default="results",
                       help="Output directory")

    args = parser.parse_args()

    report = run_staged_optimization(
        entry_type=args.entry,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output,
    )

    print(f"\nFinal Status: {report.final_status.value}")
