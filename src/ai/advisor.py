"""AI Advisor using the Anthropic Claude API.

Analyzes lap telemetry data, compares laps, and provides driving tips
and car setup recommendations.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional

import anthropic

import config
from ..telemetry.analyzer import LapAnalyzer


SYSTEM_PROMPT = """\
You are an expert motorsport engineer and driving coach with deep knowledge of:
- Racing car setup (suspension, aerodynamics, tyres, brakes, differential)
- Driving techniques (braking points, apex geometry, throttle application)
- Data analysis (interpreting telemetry channels, identifying improvement areas)
- Multiple racing simulators (Assetto Corsa, ACC, Le Mans Ultimate / rFactor 2)

When given telemetry data, you provide:
1. Specific, actionable driving advice (corner by corner where possible)
2. Car setup recommendations with realistic values
3. Comparison insights when multiple laps are provided
4. Tyre and brake management advice

Be concise but thorough. Use racing terminology. Format your response with
clear sections using markdown headers. Prioritize the most impactful improvements first.
"""


class AIAdvisor:
    """Sends lap summaries to Claude and returns driving + setup advice."""

    def __init__(self, analyzer: Optional[LapAnalyzer] = None):
        self._analyzer = analyzer or LapAnalyzer()
        self._client: Optional[anthropic.Anthropic] = None
        self._model = config.get("ai_model") or "claude-opus-4-6"

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = config.get("anthropic_api_key")
            if not api_key:
                raise ValueError(
                    "Anthropic API key not set. Configure it in Settings."
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def invalidate_client(self) -> None:
        """Call after changing API key."""
        self._client = None

    # ------------------------------------------------------------------
    # Public analysis methods (blocking)
    # ------------------------------------------------------------------

    def analyze_lap(
        self,
        lap_file: Path,
        user_comment: str = "",
    ) -> str:
        """Analyze a single lap and return AI feedback."""
        df = self._analyzer.load_lap(lap_file)
        if df is None:
            return "Error: Could not load lap file."

        summary = self._analyzer.summary_for_ai(df, lap_file)
        prompt = _build_single_lap_prompt(summary, user_comment)
        return self._chat(prompt)

    def compare_laps(
        self,
        ref_file: Path,
        lap_file: Path,
        user_comment: str = "",
    ) -> str:
        """Compare a lap against a reference lap."""
        ref_df = self._analyzer.load_lap(ref_file)
        lap_df = self._analyzer.load_lap(lap_file)
        if ref_df is None or lap_df is None:
            return "Error: Could not load one or both lap files."

        ref_summary = self._analyzer.summary_for_ai(ref_df, ref_file)
        lap_summary = self._analyzer.summary_for_ai(lap_df, lap_file)

        delta = self._analyzer.compute_delta(ref_df, lap_df)
        max_time_gained = float(delta.min())   # most negative = biggest gain
        max_time_lost   = float(delta.max())
        final_delta     = float(delta[-1])

        prompt = _build_comparison_prompt(
            ref_summary, lap_summary,
            final_delta, max_time_gained, max_time_lost,
            user_comment,
        )
        return self._chat(prompt)

    def setup_advice(
        self,
        lap_file: Path,
        issues: str = "",
    ) -> str:
        """Generate car setup recommendations based on telemetry."""
        df = self._analyzer.load_lap(lap_file)
        if df is None:
            return "Error: Could not load lap file."

        summary = self._analyzer.summary_for_ai(df, lap_file)
        prompt = _build_setup_prompt(summary, issues)
        return self._chat(prompt)

    # ------------------------------------------------------------------
    # Async wrapper for UI integration
    # ------------------------------------------------------------------

    def analyze_lap_async(
        self,
        lap_file: Path,
        on_result: Callable[[str], None],
        on_error: Callable[[str], None],
        user_comment: str = "",
    ) -> None:
        def run():
            try:
                result = self.analyze_lap(lap_file, user_comment)
                on_result(result)
            except Exception as e:
                on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def compare_laps_async(
        self,
        ref_file: Path,
        lap_file: Path,
        on_result: Callable[[str], None],
        on_error: Callable[[str], None],
        user_comment: str = "",
    ) -> None:
        def run():
            try:
                result = self.compare_laps(ref_file, lap_file, user_comment)
                on_result(result)
            except Exception as e:
                on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def setup_advice_async(
        self,
        lap_file: Path,
        on_result: Callable[[str], None],
        on_error: Callable[[str], None],
        issues: str = "",
    ) -> None:
        def run():
            try:
                result = self.setup_advice(lap_file, issues)
                on_result(result)
            except Exception as e:
                on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def custom_question_async(
        self,
        question: str,
        lap_file: Optional[Path],
        on_result: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        def run():
            try:
                context = ""
                if lap_file is not None:
                    df = self._analyzer.load_lap(lap_file)
                    if df is not None:
                        context = "\n\nTelemetry context:\n" + self._analyzer.summary_for_ai(df, lap_file)
                prompt = f"{question}{context}"
                result = self._chat(prompt)
                on_result(result)
            except Exception as e:
                on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _chat(self, user_message: str) -> str:
        client = self._get_client()
        response = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_single_lap_prompt(summary: str, comment: str) -> str:
    parts = [
        "Please analyze the following lap telemetry data and provide detailed driving advice.",
        "",
        summary,
    ]
    if comment:
        parts += ["", f"Driver's note: {comment}"]
    parts += [
        "",
        "Provide:",
        "1. Key areas where time can be gained",
        "2. Specific driving technique improvements",
        "3. Any concerning patterns (tyre abuse, inconsistent braking, etc.)",
    ]
    return "\n".join(parts)


def _build_comparison_prompt(
    ref_summary: str,
    lap_summary: str,
    final_delta: float,
    max_gain: float,
    max_loss: float,
    comment: str,
) -> str:
    delta_str = f"{final_delta:+.3f}s"
    parts = [
        f"Compare these two laps. The analyzed lap is {delta_str} relative to the reference.",
        f"Maximum time gained at any point: {max_gain:.3f}s",
        f"Maximum time lost at any point: {max_loss:.3f}s",
        "",
        "=== REFERENCE LAP ===",
        ref_summary,
        "",
        "=== ANALYZED LAP ===",
        lap_summary,
    ]
    if comment:
        parts += ["", f"Driver's note: {comment}"]
    parts += [
        "",
        "Provide:",
        "1. Where is the analyzed lap losing/gaining time vs reference?",
        "2. What specific changes in driving technique would close the gap?",
        "3. Are there any areas where the analyzed lap is better (to keep)?",
    ]
    return "\n".join(parts)


def _build_setup_prompt(summary: str, issues: str) -> str:
    parts = [
        "Based on the following telemetry data, provide car setup recommendations.",
        "",
        summary,
    ]
    if issues:
        parts += ["", f"Reported issues: {issues}"]
    parts += [
        "",
        "Provide specific setup changes for:",
        "1. Suspension (springs, dampers, ARBs, ride height)",
        "2. Aerodynamics (wing angles, diffuser if applicable)",
        "3. Tyres (pressures, camber, toe)",
        "4. Brakes (bias, pads, brake ducts)",
        "5. Differential",
        "",
        "Give numerical values where possible (e.g. 'increase front spring from ~150 to 170 N/mm').",
    ]
    return "\n".join(parts)
