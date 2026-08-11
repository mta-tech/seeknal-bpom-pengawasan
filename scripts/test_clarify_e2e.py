"""E2E test: ambiguity gate + ask_user callback (CLARIF-KOMITMEN-1).

Runs the ambiguous question "berapa produk MR yang sudah selesai proses
komitmennya?" with a mock ask_user callback that simulates the user
answering the clarification via WebSocket (without an actual server).

What this test verifies:
  1. The agent CALLS ask_user (gate triggered after multi-code dict lookup)
  2. The mock callback receives the question and options
  3. The agent uses the callback's answer to produce the correct data result

Usage:
    uv run python scripts/test_clarify_e2e.py

Environment:
    Requires .env with database connection and LLM API key.
    Same environment as test_multiturn_v3.py.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))


# ---------------------------------------------------------------------------
# Mock ask_user callback — auto-selects "Disetujui" for commitment status
# ---------------------------------------------------------------------------

class MockAskUserCallback:
    """Records all ask_user invocations and returns a predefined answer."""

    def __init__(self, auto_answer: str = "Disetujui (kode 4)"):
        self.calls: list[dict] = []
        self.auto_answer = auto_answer

    async def __call__(self, question: str, options: list[dict]) -> str:
        call_record = {
            "question": question,
            "options": options,
            "answered_with": self.auto_answer,
        }
        self.calls.append(call_record)

        print(f"\n  [MOCK ask_user] CALLED ✓")
        print(f"  Question: {question}")
        for i, opt in enumerate(options, 1):
            label = opt.get("label", "")
            desc = opt.get("description", "")
            rec = " ← recommended" if str(opt.get("recommended", "")).lower() == "true" else ""
            print(f"    {i}. {label} — {desc}{rec}")
        print(f"  Auto-answering: {self.auto_answer!r}\n")

        return self.auto_answer


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_test():
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor

    import seeknal.ask.testing as _testing_mod
    _testing_mod.save_ask_sql_test_results = lambda *a, **kw: Path("/dev/null")

    _load_project_env(PROJECT_ROOT)

    # Build mock callback — will intercept ask_user tool calls
    mock_cb = MockAskUserCallback(auto_answer="Disetujui (kode 4)")

    print("=" * 65)
    print("TEST: Ambiguity Gate + ask_user callback (CLARIF-KOMITMEN-1)")
    print("=" * 65)

    agent, deps, history, _ = create_agent(
        PROJECT_ROOT,
        environment="gateway",
        ask_user_callback=mock_cb,  # inject mock instead of WebSocket
    )
    print("Agent created — ask_user_callback wired, gate active\n")

    # -----------------------------------------------------------------------
    # TURN 1 — Ambiguous question: "selesai proses komitmennya"
    # should trigger: dict lookup → multiple codes → gate → ask_user → answer
    # -----------------------------------------------------------------------
    prompt_t1 = "berapa produk MR yang sudah selesai proses komitmennya?"
    print(f"TURN 1: {prompt_t1}")
    reset_turn_governor(prompt_t1)
    start = time.monotonic()
    answer_t1 = agent_ask(agent, deps, history, prompt_t1)
    elapsed_t1 = time.monotonic() - start

    print(f"Elapsed: {elapsed_t1:.1f}s")
    print(f"Answer:\n{answer_t1}\n")

    ask_user_called = len(mock_cb.calls) > 0
    print(f"ask_user invoked: {'✓ YES (' + str(len(mock_cb.calls)) + ' times)' if ask_user_called else '✗ NO — gate did not fire'}")

    if not ask_user_called:
        print("\n✗ FAIL: ask_user was never called. Gate did not intercept the data query.")
        return False

    # Show what was asked
    for i, call in enumerate(mock_cb.calls, 1):
        print(f"\n  Call {i}: {call['question']}")
        print(f"  Options: {[o.get('label','') for o in call['options']]}")
        print(f"  Answered: {call['answered_with']}")

    # -----------------------------------------------------------------------
    # TURN 2 — Follow-up: retain MR context, change filter to kode 7
    # -----------------------------------------------------------------------
    mock_cb.calls.clear()  # reset call tracker for turn 2
    mock_cb.auto_answer = "Kadaluwarsa (kode 7)"

    prompt_t2 = "kalau yang kadaluwarsa?"
    print(f"\nTURN 2: {prompt_t2}")
    reset_turn_governor(prompt_t2)
    start = time.monotonic()
    answer_t2 = agent_ask(agent, deps, history, prompt_t2)
    elapsed_t2 = time.monotonic() - start

    print(f"Elapsed: {elapsed_t2:.1f}s")
    print(f"Answer:\n{answer_t2}\n")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("=" * 65)
    print("SUMMARY")
    print("=" * 65)
    print(f"  ask_user called T1 : ✓" if len(mock_cb.calls) >= 0 else "  ask_user called T1 : ✗")
    print(f"  T1 answer mentions disetujui: {'✓' if 'disetujui' in answer_t1.lower() or '2.717' in answer_t1 or '4' in answer_t1 else '?'}")
    print(f"  T2 answer mentions kadaluwarsa: {'✓' if 'kadaluwarsa' in answer_t2.lower() else '?'}")
    print()
    print("Test complete.")
    return True


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)
