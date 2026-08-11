"""Test: apakah ask_user dipanggil untuk pertanyaan ambigu?

Menjalankan beberapa pertanyaan dengan mock ask_user callback dan
melaporkan: dipanggil atau tidak + pilihan apa yang muncul.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))


QUESTIONS = [
    # (label, prompt, auto_answer)
    ("KOMITMEN-SELESAI",  "berapa produk MR yang sudah selesai proses komitmennya?",       "auto"),
    ("KOMITMEN-DISETUJUI","berapa produk MR yang komitmennya sudah disetujui BPOM?",       "auto"),
    ("KADALUWARSA",       "berapa produk MR yang kadaluwarsa?",                            "auto"),
    ("AKTIF",             "berapa izin edar yang aktif saat ini?",                         "auto"),
    ("KEMASAN-TUNGGAL",   "berapa produk dengan kemasan tunggal?",                         "auto"),
    ("FORMULA-BAYI",      "berapa total produk formula bayi terdaftar di BPOM?",           "auto"),
    ("PERMOHONAN-2025",   "berapa permohonan tahun 2025?",                                 "auto"),
    ("TOTAL-PRODUK",      "berapa total produk pangan olahan terdaftar?",                  "auto"),  # tidak ambigu
]


class MockAskUserCallback:
    def __init__(self):
        self.calls: list[dict] = []

    async def __call__(self, question: str, options: list[dict]) -> str:
        self.calls.append({"question": question, "options": options})
        # Auto-pilih opsi pertama
        first_label = options[0].get("label", "opsi 1") if options else "opsi 1"
        return first_label

    def reset(self):
        self.calls.clear()


def run_single(agent, deps, history, prompt, mock_cb, label):
    from seeknal.ask.agents.tools._context import reset_turn_governor
    mock_cb.reset()
    reset_turn_governor(prompt)

    t0 = time.monotonic()
    answer = agent.run_sync(prompt, deps=deps, message_history=history)
    elapsed = time.monotonic() - t0

    called = len(mock_cb.calls) > 0
    status = "✓ DIPANGGIL" if called else "✗ TIDAK DIPANGGIL"

    print(f"\n{'─'*60}")
    print(f"[{label}] {prompt}")
    print(f"  ask_user: {status}  ({elapsed:.0f}s)")

    if called:
        for i, c in enumerate(mock_cb.calls, 1):
            print(f"  Pertanyaan #{i}: {c['question']}")
            for j, opt in enumerate(c['options'], 1):
                rec = " ← recommended" if str(opt.get("recommended","")).lower() == "true" else ""
                print(f"    {j}. [{opt.get('label','')}] {opt.get('description','')}{rec}")
    else:
        snippet = answer.output[:120].replace("\n", " ") if hasattr(answer, "output") else str(answer)[:120]
        print(f"  Jawaban langsung: {snippet}...")

    return called, mock_cb.calls[:]


def main():
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    import seeknal.ask.testing as _testing_mod
    _testing_mod.save_ask_sql_test_results = lambda *a, **kw: Path("/dev/null")

    _load_project_env(PROJECT_ROOT)

    mock_cb = MockAskUserCallback()

    print("=" * 60)
    print("TEST: ask_user gate — dipanggil atau tidak?")
    print("=" * 60)

    results = []
    for label, prompt, _ in QUESTIONS:
        agent, deps, history, _ = create_agent(
            PROJECT_ROOT,
            environment="gateway",
            ask_user_callback=mock_cb,
        )
        try:
            called, calls = run_single(agent, deps, history, prompt, mock_cb, label)
            results.append((label, called, calls))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((label, None, []))

    print(f"\n{'='*60}")
    print("RINGKASAN")
    print(f"{'='*60}")
    called_count = sum(1 for _, c, _ in results if c)
    print(f"ask_user dipanggil: {called_count}/{len(results)} pertanyaan\n")
    for label, called, calls in results:
        icon = "✓" if called else "✗"
        n_options = len(calls[0]["options"]) if calls else 0
        opts = f"({n_options} opsi)" if called else ""
        print(f"  {icon} {label} {opts}")


if __name__ == "__main__":
    main()
