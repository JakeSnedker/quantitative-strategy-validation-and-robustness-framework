# Project Roadmap

## Vision

Build a **complete systematic strategy development framework** that allows rapid testing and validation of new trading entry strategies. The system should take a strategy concept from idea to validated, tradeable parameters with minimal manual intervention.

---

## Current State (March 2026)

### Completed
- [x] Walk-forward optimization engine with sliding windows
- [x] MT5 batch mode automation
- [x] Monte Carlo simulation with visualization
- [x] 5-stage optimization architecture (designed)
- [x] Stage 1 Foundation testing (Phase 1: ATR SL, Phase 2: L_O_TH SL)
- [x] Parameter stability testing framework
- [x] Pass/fail criteria with FTMO compliance
- [x] CLI interface for all major operations
- [x] Professional documentation and README

### In Progress
- [ ] Stage 1 Phase 3: TP method comparison
- [ ] Stage 2: Entry refinement filter testing
- [ ] Full 5-stage validation for TrendEng

---

## Roadmap

### Phase 1: Complete 5-Stage Validation (Current)

**Goal:** Prove the full pipeline works end-to-end with TrendEng entry.

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 1 | Foundation (SL/TP structure) | In Progress |
| Stage 2 | Entry Refinement (8 filter clusters) | Pending |
| Stage 3 | Time & Context (sessions, news) | Pending |
| Stage 4 | Trade Management (BE/Trail methods) | Pending |
| Stage 5 | Final Validation + Monte Carlo | Pending |

**Deliverable:** Validated TrendEng parameters or documented "no edge" conclusion.

---

### Phase 2: Second Entry Validation

**Goal:** Run complete 5-stage validation on TrendEngWick to verify system works across different entry types.

- [ ] Full 5-stage run for TrendEngWick
- [ ] Compare results to TrendEng
- [ ] Document any system improvements needed
- [ ] Refine automation based on learnings

**Deliverable:** Validated TrendEngWick parameters + refined validation system.

---

### Phase 3: Plug-and-Play Entry System

**Goal:** Create a system where new entry strategies can be easily defined, tested, and validated.

#### 3.1 Entry Definition Format
```yaml
# Example entry definition
name: "NewEntryPattern"
magic_number: 15
conditions:
  long:
    - "close > ema_21"
    - "rsi_14 crosses above 30"
    - "volume > volume_sma_20"
  short:
    - "close < ema_21"
    - "rsi_14 crosses below 70"
    - "volume > volume_sma_20"
```

#### 3.2 Code Generation
- [ ] **PineScript Generator**: Auto-generate TradingView indicator for visual verification
- [ ] **MQL5 Generator**: Auto-generate entry logic block that plugs into master EA
- [ ] Entry template system with standardized interface

#### 3.3 Integration
- [ ] Master EA with modular entry slot
- [ ] Auto-registration of new entries
- [ ] Unified parameter structure

**Deliverable:** `python cli.py new-entry my_strategy.yaml` generates both PineScript and MQL5 code.

---

### Phase 4: Enhanced Validation

**Goal:** Add advanced validation techniques.

- [ ] Multi-timeframe correlation analysis
- [ ] Regime detection (trending vs ranging markets)
- [ ] Cross-asset validation (test on multiple symbols)
- [ ] Portfolio-level Monte Carlo (multiple strategies combined)
- [ ] Automated report generation (PDF/HTML)

---

### Phase 5: Production System

**Goal:** Make the system production-ready for continuous strategy development.

- [ ] Web dashboard for monitoring optimizations
- [ ] Database storage for all test results
- [ ] Strategy version control and comparison
- [ ] Automated nightly validation runs
- [ ] Alert system for strategy degradation
- [ ] Integration with live trading performance tracking

---

## Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRATEGY DEVELOPMENT PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │    DEFINE    │────►│   GENERATE   │────►│   VALIDATE   │                │
│  │              │     │              │     │              │                │
│  │  YAML/JSON   │     │  PineScript  │     │  5-Stage     │                │
│  │  Entry Spec  │     │  MQL5 Code   │     │  Walk-Fwd    │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│                                                   │                          │
│                                                   ▼                          │
│                              ┌─────────────────────────────────┐            │
│                              │           OUTPUT                 │            │
│                              │                                  │            │
│                              │  ✓ Validated Parameters          │            │
│                              │  ✓ Monte Carlo Risk Profile      │            │
│                              │  ✓ Ready-to-Trade .set File      │            │
│                              │  ✗ "No Edge Found" Report        │            │
│                              │                                  │            │
│                              └─────────────────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to validate new entry | < 24 hours (automated) |
| False positive rate (overfit strategies passing) | < 5% |
| Documentation coverage | 100% of public APIs |
| Test coverage | > 80% |

---

## Technical Debt / Known Issues

- [ ] HTML report parsing for individual trades needs improvement
- [ ] Single backtest mode needs Optimization=0 fix
- [ ] Monte Carlo integration with validation backtest incomplete
- [ ] Need better error handling for MT5 connection issues

---

## Contributing

This is currently a personal project for systematic trading strategy development. The framework is designed to be extensible for new entry patterns while maintaining rigorous validation standards.

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1 | Feb 2026 | Initial optimizer with LLM guidance |
| 0.2 | Mar 2026 | Walk-forward automation |
| 0.3 | Mar 2026 | 5-stage architecture + Monte Carlo |
| 0.4 | TBD | Complete TrendEng validation |
| 0.5 | TBD | Plug-and-play entry system |
| 1.0 | TBD | Production-ready framework |
