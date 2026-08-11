"""
Smoke test — satu skenario konseptual untuk memverifikasi bahwa infrastruktur
multi-turn bekerja sebelum menjalankan test yang butuh koneksi database.

Skenario ini menjawab dari context files (business_glossary.md) sehingga
tidak memerlukan SSH tunnel atau koneksi ke warehouse.

Usage:
    uv run python scripts/test_smoke.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
# Satu skenario smoke test — konseptual, tanpa query database
# ---------------------------------------------------------------------------

SMOKE_SCENARIO = Scenario(
    name="konsep_nie_vs_permohonan_dengan_data",
    description=(
        "Smoke test 4 turn: konseptual + koneksi DB. "
        "T1-T3 dari context file (tanpa DB), T4 query langsung ke warehouse "
        "untuk membuktikan koneksi WAREHOUSE_URL aktif."
    ),
    turns=[
        Turn(
            prompt="apa itu NIE?",
            assert_contains=["Nomor Izin Edar", "izin edar"],
            note=(
                "T1: Konseptual — dari business_glossary.md, tidak butuh DB. "
                "Assert: harus sebut kepanjangan NIE."
            ),
        ),
        Turn(
            prompt="apa bedanya dengan permohonan?",
            assert_contains=["permohonan", "pengajuan"],
            note=(
                "T2: Referensi implisit ke NIE dari T1 — agent ingat konteks. "
                "Assert: harus sebut permohonan sebagai pengajuan."
            ),
        ),
        Turn(
            prompt="dari keduanya, mana yang dihitung pakai produk_id?",
            assert_contains=["permohonan", "produk_id"],
            note=(
                "T3: 'Keduanya' = NIE (T1) + permohonan (T2) — cross-turn context. "
                "Assert: harus sebut permohonan dan produk_id."
            ),
        ),
        Turn(
            prompt="berapa total NIE pangan olahan di sistem ERBA yang terbit tahun 2023?",
            assert_contains=["30.276", "2023", "ERBA"],
            note=(
                "T4: BUTUH KONEKSI DB — agent harus eksekusi SQL ke warehouse. "
                "Bukti koneksi aktif: sql > 0 di output, angka 30.276 harus muncul. "
                "Assert: angka 30.276, sebut ERBA dan 2023."
            ),
        ),
    ],
)


# ---------------------------------------------------------------------------
# Runner — logic identik dengan test_multiturn.py
# ---------------------------------------------------------------------------

@dataclass
class TurnResult:
    turn_num: int
    prompt: str
    answer: str
    elapsed_s: float
    llm_requests: int
    tool_calls: int
    sqls: list[str]
    passed: bool
    failures: list[str]
    note: str = ""


def _extract_sqls(history) -> list[str]:
    """Ekstrak SQL yang dikirim LLM ke tool execute_sql — identik dengan bench.py."""
    from pydantic_ai.messages import ToolCallPart
    sqls = []
    for m in history:
        for p in getattr(m, "parts", []):
            if isinstance(p, ToolCallPart) and p.tool_name == "execute_sql":
                args = p.args if isinstance(p.args, dict) else {}
                sql = args.get("sql", "").strip()
                if sql:
                    sqls.append(sql)
    return sqls


def run_smoke() -> list[TurnResult]:
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor
    from pydantic_ai.messages import ModelResponse, ToolCallPart

    _load_project_env(PROJECT_ROOT)

    scenario = SMOKE_SCENARIO

    print(f"\n{'='*60}")
    print(f"Smoke Test: {scenario.name}")
    print(f"  {scenario.description}")
    print(f"  Turns: {len(scenario.turns)}")
    print(f"{'='*60}\n")

    # Agent dan history dibuat sekali — dibagi ke semua turn
    agent, deps, history, _ = create_agent(
        PROJECT_ROOT,
        environment="gateway",
    )

    turn_results: list[TurnResult] = []

    for i, turn in enumerate(scenario.turns, start=1):
        print(f"  Turn {i}: {turn.prompt}")
        print(f"  Note : {turn.note}")

        prev_len = len(history)
        reset_turn_governor(turn.prompt)
        start = time.monotonic()
        answer = agent_ask(agent, deps, history, turn.prompt)
        elapsed = time.monotonic() - start

        new_msgs = history[prev_len:]
        llm_requests = sum(1 for m in new_msgs if isinstance(m, ModelResponse))
        tool_calls = sum(
            1 for m in new_msgs
            for p in (m.parts if hasattr(m, "parts") else [])
            if isinstance(p, ToolCallPart)
        )
        sqls = _extract_sqls(new_msgs)

        failures = []
        answer_lower = answer.lower()
        for expected in turn.assert_contains:
            if expected.lower() not in answer_lower:
                failures.append(f"missing: '{expected}'")

        passed = not failures
        status = "✓" if passed else "✗"
        print(f"  {status} {elapsed:.1f}s  req={llm_requests}  tools={tool_calls}  sql={len(sqls)}")
        if sqls:
            for j, sql in enumerate(sqls, 1):
                print(f"  --- SQL {j} ---")
                for line in sql.splitlines():
                    print(f"    {line}")
        if failures:
            for f in failures:
                print(f"    FAIL: {f}")
        print(f"  Answer:\n    {answer[:200]}...")
        print()

        turn_results.append(TurnResult(
            turn_num=i,
            prompt=turn.prompt,
            answer=answer,
            elapsed_s=elapsed,
            llm_requests=llm_requests,
            tool_calls=tool_calls,
            sqls=sqls,
            passed=passed,
            failures=failures,
            note=turn.note,
        ))

    return turn_results


def print_summary(turn_results: list[TurnResult]) -> None:
    print("=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)

    all_passed = all(t.passed for t in turn_results)
    total_time = sum(t.elapsed_s for t in turn_results)
    passed_count = sum(1 for t in turn_results if t.passed)

    for t in turn_results:
        ts = "✓" if t.passed else "✗"
        print(f"  {ts} Turn {t.turn_num}: {t.elapsed_s:.1f}s  req={t.llm_requests}  tools={t.tool_calls}  sql={len(t.sqls)}  '{t.prompt[:45]}'")
        for f in t.failures:
            print(f"       FAIL: {f}")

    print()
    final = "PASS" if all_passed else "FAIL"
    print(f"  Result : [{final}]  {passed_count}/{len(turn_results)} turns  {total_time:.1f}s total")
    print("=" * 60)

    if all_passed:
        print("\n  Infrastruktur multi-turn berjalan normal.")
        print("  Agent mempertahankan konteks lintas turn.")
        print("  Siap untuk menjalankan test_multiturn_v3.py (butuh tunnel DB aktif).")
    else:
        print("\n  Ada turn yang gagal. Periksa:")
        print("  - Apakah context files tersedia di context/business_glossary.md?")
        print("  - Apakah GOOGLE_API_KEY atau LLM provider sudah di-set di .env?")
        print("  - Apakah seeknal package terinstall? (uv run python scripts/test_smoke.py)")


def save_json(turn_results: list[TurnResult]) -> Path:
    output_dir = PROJECT_ROOT / "seeknal" / "tests" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = f"smoke_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / filename

    scenario = SMOKE_SCENARIO
    all_passed = all(t.passed for t in turn_results)

    payload = {
        "project_path": str(PROJECT_ROOT),
        "timestamp": timestamp.isoformat(),
        "mode": "multiturn-smoke",
        "scenario": scenario.name,
        "results": [
            {
                "turn_num": t.turn_num,
                "prompt": t.prompt,
                "passed": t.passed,
                "elapsed_s": round(t.elapsed_s, 2),
                "llm_requests": t.llm_requests,
                "tool_calls": t.tool_calls,
                "sqls": t.sqls,
                "failures": t.failures,
                "note": t.note,
                "answer": t.answer,
            }
            for t in turn_results
        ],
        "summary": {
            "total_turns": len(turn_results),
            "passed": sum(1 for t in turn_results if t.passed),
            "failed": sum(1 for t in turn_results if not t.passed),
            "scenario_passed": all_passed,
            "total_elapsed_s": round(sum(t.elapsed_s for t in turn_results), 2),
        },
    }

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    results = run_smoke()
    print_summary(results)
    path = save_json(results)
    print(f"\n  Output saved: {path}")
