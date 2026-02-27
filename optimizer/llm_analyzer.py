"""
LLM Analyzer for optimization decisions.
Integrates with Claude, OpenAI, or local Ollama models.
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

from config import get_config, LLMConfig
from results_parser import BacktestResults


@dataclass
class OptimizationSuggestion:
    """LLM's suggestion for next optimization step"""
    reasoning: str
    parameter_changes: Dict[str, Any]
    exploration_type: str  # "explore" or "exploit"
    confidence: float  # 0.0 to 1.0
    should_continue: bool = True
    stop_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def analyze(
        self,
        results: BacktestResults,
        history: List[Dict[str, Any]],
        current_params: Dict[str, Any],
        goal: str
    ) -> OptimizationSuggestion:
        """Analyze results and suggest next parameters"""
        pass


class AnthropicProvider(LLMProvider):
    """Claude API provider"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

    def analyze(
        self,
        results: BacktestResults,
        history: List[Dict[str, Any]],
        current_params: Dict[str, Any],
        goal: str
    ) -> OptimizationSuggestion:
        prompt = self._build_prompt(results, history, current_params, goal)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return self._parse_response(response.content[0].text)

    def _build_prompt(
        self,
        results: BacktestResults,
        history: List[Dict[str, Any]],
        current_params: Dict[str, Any],
        goal: str
    ) -> str:
        return build_analysis_prompt(results, history, current_params, goal)

    def _parse_response(self, response: str) -> OptimizationSuggestion:
        return parse_llm_response(response)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

    def analyze(
        self,
        results: BacktestResults,
        history: List[Dict[str, Any]],
        current_params: Dict[str, Any],
        goal: str
    ) -> OptimizationSuggestion:
        prompt = build_analysis_prompt(results, history, current_params, goal)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )

        return parse_llm_response(response.choices[0].message.content)


class OllamaProvider(LLMProvider):
    """Local Ollama provider"""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama2"):
        try:
            import requests
            self.host = host.rstrip("/")
            self.model = model
            self.requests = requests
        except ImportError:
            raise ImportError("requests package required. Install with: pip install requests")

    def analyze(
        self,
        results: BacktestResults,
        history: List[Dict[str, Any]],
        current_params: Dict[str, Any],
        goal: str
    ) -> OptimizationSuggestion:
        prompt = build_analysis_prompt(results, history, current_params, goal)

        response = self.requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
        )
        response.raise_for_status()

        return parse_llm_response(response.json()["response"])


def build_analysis_prompt(
    results: BacktestResults,
    history: List[Dict[str, Any]],
    current_params: Dict[str, Any],
    goal: str
) -> str:
    """Build the analysis prompt for the LLM"""

    # Format history summary
    history_text = ""
    if history:
        history_text = "\n\nPrevious test results:\n"
        for i, h in enumerate(history[-5:], 1):  # Last 5 tests
            history_text += f"""
Test {i}:
- Profit Factor: {h.get('profit_factor', 'N/A')}
- Win Rate: {h.get('win_rate', 'N/A')}%
- Max DD: {h.get('max_drawdown_percent', 'N/A')}%
- Changes made: {h.get('changes', 'N/A')}
"""

    # Key parameters to focus on
    key_params = {
        "ATRStopLossMultiplier": current_params.get("ATRStopLossMultiplier"),
        "ATRPeriod": current_params.get("ATRPeriod"),
        "TakeProfitStopMultiplier": current_params.get("TakeProfitStopMultiplier"),
        "BreakEvenMethod": current_params.get("BreakEvenMethod"),
        "BreakEvenXPointsinProf": current_params.get("BreakEvenXPointsinProf"),
        "TrailMethod": current_params.get("TrailMethod"),
        "ATRTrailMultiplier": current_params.get("ATRTrailMultiplier"),
        "TrendMethod": current_params.get("TrendMethod"),
        "BBexpand": current_params.get("BBexpand"),
        "Tradescore": current_params.get("Tradescore"),
        "CheckRoom": current_params.get("CheckRoom"),
        "RewardMultiplierForRoom": current_params.get("RewardMultiplierForRoom"),
    }

    prompt = f"""You are an expert quantitative trading analyst optimizing an automated trading strategy.

## Current Test Results
{results.to_summary()}

## Current Parameters
{json.dumps(key_params, indent=2)}
{history_text}

## Optimization Goal
{goal}

## Your Task
Analyze the results and suggest parameter changes for the next test.

Consider:
1. If profit factor < 1.0, focus on reducing losses (tighter stops, break-even)
2. If win rate is low but avg win is high, this might be acceptable
3. If max drawdown is too high, prioritize risk management parameters
4. Balance exploration (trying new values) with exploitation (refining what works)

## Response Format
Respond with a JSON object only, no other text:
{{
    "reasoning": "Brief explanation of your analysis and recommendation",
    "parameter_changes": {{
        "ParameterName": new_value,
        ...
    }},
    "exploration_type": "explore" or "exploit",
    "confidence": 0.0 to 1.0,
    "should_continue": true or false,
    "stop_reason": null or "reason to stop optimizing"
}}

Only suggest changes to parameters that are likely to improve results.
If results are already good and stable, set should_continue to false.
"""

    return prompt


def parse_llm_response(response: str) -> OptimizationSuggestion:
    """Parse LLM response into OptimizationSuggestion"""

    # Try to extract JSON from response
    try:
        # Find JSON in response
        json_match = response
        if "```json" in response:
            json_match = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_match = response.split("```")[1].split("```")[0]
        elif "{" in response:
            start = response.index("{")
            end = response.rindex("}") + 1
            json_match = response[start:end]

        data = json.loads(json_match)

        return OptimizationSuggestion(
            reasoning=data.get("reasoning", "No reasoning provided"),
            parameter_changes=data.get("parameter_changes", {}),
            exploration_type=data.get("exploration_type", "explore"),
            confidence=float(data.get("confidence", 0.5)),
            should_continue=data.get("should_continue", True),
            stop_reason=data.get("stop_reason"),
        )

    except (json.JSONDecodeError, ValueError, IndexError) as e:
        # Return a default suggestion if parsing fails
        return OptimizationSuggestion(
            reasoning=f"Failed to parse LLM response: {e}. Raw response: {response[:200]}",
            parameter_changes={},
            exploration_type="explore",
            confidence=0.0,
            should_continue=True,
            stop_reason=None,
        )


def get_llm_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """Get the configured LLM provider"""

    if config is None:
        config = get_config().llm

    provider = config.provider.lower()

    if provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        return AnthropicProvider(config.anthropic_api_key, config.anthropic_model)

    elif provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        return OpenAIProvider(config.openai_api_key, config.openai_model)

    elif provider == "ollama":
        return OllamaProvider(config.ollama_host, config.ollama_model)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


class OptimizationAnalyzer:
    """
    High-level analyzer that manages the optimization process.
    Tracks history and makes intelligent suggestions.
    """

    def __init__(self, goal: str, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize the analyzer.

        Args:
            goal: Optimization goal (e.g., "Maximize profit factor while keeping DD < 5%")
            llm_provider: LLM provider to use. Auto-detects from config if not provided.
        """
        self.goal = goal
        self.llm = llm_provider or get_llm_provider()
        self.history: List[Dict[str, Any]] = []

    def analyze(
        self,
        results: BacktestResults,
        current_params: Dict[str, Any]
    ) -> OptimizationSuggestion:
        """
        Analyze results and get next suggestion.

        Args:
            results: Backtest results to analyze
            current_params: Current parameter values

        Returns:
            OptimizationSuggestion with recommended changes
        """
        suggestion = self.llm.analyze(
            results=results,
            history=self.history,
            current_params=current_params,
            goal=self.goal
        )

        # Record in history
        self.history.append({
            "profit_factor": results.profit_factor,
            "win_rate": results.win_rate,
            "max_drawdown_percent": results.max_drawdown_percent,
            "total_trades": results.total_trades,
            "net_profit": results.total_net_profit,
            "params": current_params.copy(),
            "changes": suggestion.parameter_changes,
            "reasoning": suggestion.reasoning,
        })

        return suggestion

    def get_best_result(self) -> Optional[Dict[str, Any]]:
        """Get the best result from history based on profit factor"""
        if not self.history:
            return None
        return max(self.history, key=lambda x: x.get("profit_factor", 0))

    def save_history(self, filepath: str) -> None:
        """Save optimization history to JSON file"""
        with open(filepath, 'w') as f:
            json.dump({
                "goal": self.goal,
                "history": self.history,
            }, f, indent=2)

    def load_history(self, filepath: str) -> None:
        """Load optimization history from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.history = data.get("history", [])


if __name__ == "__main__":
    # Test the analyzer
    print("LLM Analyzer Module")
    print("=" * 50)

    # Create a mock result for testing
    mock_results = BacktestResults(
        total_trades=100,
        winning_trades=38,
        losing_trades=62,
        win_rate=38.0,
        profit_factor=1.15,
        total_net_profit=1500.0,
        max_drawdown_percent=6.2,
        average_win=150.0,
        average_loss=75.0,
    )

    mock_params = {
        "ATRStopLossMultiplier": 2.0,
        "TakeProfitStopMultiplier": 2.0,
        "BreakEvenMethod": 0,
        "TrailMethod": 0,
    }

    print("\nMock Results:")
    print(mock_results.to_summary())

    print("\nTo test with real LLM, set up your .env file and run:")
    print("  analyzer = OptimizationAnalyzer('Maximize PF, keep DD < 5%')")
    print("  suggestion = analyzer.analyze(results, params)")
