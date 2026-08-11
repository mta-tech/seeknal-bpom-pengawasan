"""
Multi-turn conversation tests. Each scenario is a list of turns; history
is carried forward so the agent can reference previous answers.

Usage:
    uv run python scripts/test_multiturn.py
    uv run python scripts/test_multiturn.py --scenario nie_followup
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))


@dataclass
class Turn:
    prompt: str
    assert_contains: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Scenario:
    name: str
    turns: list[Turn]
    description: str = ""


# ---------------------------------------------------------------------------
# Define scenarios
# ---------------------------------------------------------------------------

SCENARIOS: list[Scenario] = [
    Scenario(
        name="nie_followup",
        description="Ask NIE total 2023, then drill down by skala industri, then by risiko",
        turns=[
            Turn(
                prompt="berapa total NIE yang terbit tahun 2023?",
                assert_contains=["2023"],
                note="Baseline total — agent must use tanggal, not tanggal_bayar",
            ),
            Turn(
                prompt="sekarang tampilkan per skala industri",
                assert_contains=["Besar", "Importir", "Menengah"],
                note="Follow-up — agent must reuse year=2023 context from turn 1",
            ),
            Turn(
                prompt="dan mana yang paling banyak dari UMKM?",
                assert_contains=["UMKM", "Menengah"],
                note="Agent must know UMKM = Mikro+Kecil+Menengah and rank them",
            ),
        ],
    ),
    Scenario(
        name="permohonan_vs_nie",
        description="Compare permohonan vs NIE for the same year — tests routing consistency",
        turns=[
            Turn(
                prompt="berapa permohonan izin edar tahun 2023?",
                assert_contains=["2023", "permohonan"],
                note="Permohonan — must use produk_id and tanggal_bayar",
            ),
            Turn(
                prompt="bandingkan dengan jumlah NIE yang terbit di tahun yang sama",
                assert_contains=["NIE", "2023"],
                note="Agent must run a different query (tanggal, nomor) not reuse permohonan result",
            ),
            Turn(
                prompt="apa perbedaan antara keduanya?",
                assert_contains=["izin edar", "permohonan"],
                note="Agent should explain NIE=issued license, permohonan=application submitted",
            ),
        ],
    ),
    Scenario(
        name="forecast_context",
        description="Ask forecast, then ask about actual data for context",
        turns=[
            Turn(
                prompt="berapa prediksi permohonan bulan Juni 2027?",
                assert_contains=["2027", "prediksi"],
                note="Must query forecast_permohonan, not product tables",
            ),
            Turn(
                prompt="dan bagaimana tren aktual permohonan di tahun 2023?",
                assert_contains=["2023"],
                note="Must switch to product tables for actual data",
            ),
            Turn(
                prompt="apakah tren aktual konsisten dengan arah prediksi?",
                assert_contains=["prediksi", "aktual"],
                note="Agent must compare both data points from previous turns",
            ),
        ],
    ),
    Scenario(
        name="code_resolution_check",
        description="Verify agent resolves coded columns without being told to",
        turns=[
            Turn(
                prompt="berapa NIE per jenis permohonan tahun 2023?",
                assert_contains=["Permohonan Baru", "2023"],
                note="Must show 'Permohonan Baru' not '301'",
            ),
            Turn(
                prompt="dari yang baru, berapa yang termasuk UMKM?",
                assert_contains=["UMKM"],
                note="Must filter jenis_permohonan='301' and join with trader scale",
            ),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class TurnResult:
    turn_num: int
    prompt: str
    answer: str
    elapsed_s: float
    tool_calls: int
    passed: bool
    failures: list[str]
    note: str = ""


@dataclass
class ScenarioResult:
    name: str
    turns: list[TurnResult]

    @property
    def passed(self) -> bool:
        return all(t.passed for t in self.turns)


def run_scenario(scenario: Scenario) -> ScenarioResult:
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor
    from pydantic_ai.messages import ToolCallPart

    _load_project_env(PROJECT_ROOT)

    agent, deps, history, _ = create_agent(
        PROJECT_ROOT,
        environment="gateway",
    )

    turn_results: list[TurnResult] = []

    for i, turn in enumerate(scenario.turns, start=1):
        print(f"    Turn {i}: {turn.prompt[:70]}")
        if turn.note:
            print(f"    Note : {turn.note}")

        reset_turn_governor(turn.prompt)
        start = time.monotonic()
        answer = agent_ask(agent, deps, history, turn.prompt)
        elapsed = time.monotonic() - start

        tool_calls = sum(
            1 for m in history
            for p in (m.parts if hasattr(m, "parts") else [])
            if isinstance(p, ToolCallPart)
        )

        # Check assertions
        failures = []
        answer_lower = answer.lower()
        for expected in turn.assert_contains:
            if expected.lower() not in answer_lower:
                failures.append(f"missing: '{expected}'")

        passed = not failures
        status = "✓" if passed else "✗"
        print(f"    {status} {elapsed:.1f}s  tools={tool_calls}")
        if failures:
            for f in failures:
                print(f"      FAIL: {f}")
        print(f"    Answer: {answer[:120]}...")
        print()

        turn_results.append(TurnResult(
            turn_num=i,
            prompt=turn.prompt,
            answer=answer,
            elapsed_s=elapsed,
            tool_calls=tool_calls,
            passed=passed,
            failures=failures,
            note=turn.note,
        ))

    return ScenarioResult(name=scenario.name, turns=turn_results)


def run_all(select: str | None = None) -> list[ScenarioResult]:
    scenarios = SCENARIOS
    if select:
        scenarios = [s for s in scenarios if select in s.name]

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.name}")
        print(f"  {scenario.description}")
        print(f"{'='*60}")
        result = run_scenario(scenario)
        results.append(result)

    return results


def print_summary(results: list[ScenarioResult]) -> None:
    print("\n" + "=" * 60)
    print("MULTI-TURN SUMMARY")
    print("=" * 60)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        passed_turns = sum(1 for t in r.turns if t.passed)
        total_time = sum(t.elapsed_s for t in r.turns)
        print(f"  [{status}] {r.name:<30s} {passed_turns}/{len(r.turns)} turns  {total_time:.1f}s total")
        for t in r.turns:
            ts = "✓" if t.passed else "✗"
            print(f"    {ts} Turn {t.turn_num}: {t.elapsed_s:.1f}s  tools={t.tool_calls}  {t.prompt[:50]}")
            for f in t.failures:
                print(f"         FAIL: {f}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\n  Scenarios: {passed}/{total} passed")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-turn conversation tests")
    parser.add_argument("--scenario", help="Run only scenario whose name contains this string")
    args = parser.parse_args()

    print(f"\nProject: {PROJECT_ROOT}")
    results = run_all(select=args.scenario)
    print_summary(results)
