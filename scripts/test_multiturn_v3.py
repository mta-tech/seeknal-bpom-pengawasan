"""
Multi-turn conversation tests v3 — load scenarios from YAML files.

Logic identical to test_multiturn_v2.py. Only difference: scenarios are
loaded from YAML files in a directory instead of hardcoded.

Supports parallel execution via --workers for running independent scenarios
simultaneously. Each scenario creates its own agent (fully isolated);
one failure never blocks or breaks another.

=== TIMEOUT SETTINGS ===

Two independent timeout mechanisms:

1. --turn-timeout N (seconds, default 0 = no limit)
   Per-turn timeout using SIGALRM. Works ONLY in sequential mode (--workers 1).
   Kills a single turn if it takes longer than N seconds.
   Does NOT work in parallel mode (SIGALRM is process-wide).

2. --timeout N (seconds, default 300)
   Per-scenario wall-clock timeout in parallel mode (--workers > 1).
   Uses concurrent.futures.Future.result(timeout=N).
   If a worker thread does not finish within N seconds, the scenario is
   marked as TIMEOUT and the main thread moves on. The worker thread
   continues in the background but its result is discarded.

Combine both: --turn-timeout 120 --workers 1  (sequential with per-turn limit)
             --timeout 300 --workers 4         (parallel with 5m per-scenario wall)

Output goes to seeknal/tests/outputs/<YYYY-MM-DD>/<TEST_DATA_VERSION>/
where TEST_DATA_VERSION is read from .env (default: "v1").
CB-5
Usage:
    uv run python scripts/test_multiturn_v3.py
    uv run python scripts/test_multiturn_v3.py --scenario nie
    uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn
    uv run python scripts/test_multiturn_v3.py --workers 4
    uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/singleturn --turn-timeout 3600 --workers 30
    uv run python scripts/test_multiturn_v3.py --turn-timeout 120 --version v2 --workers 1
    uv run python scripts/test_multiturn_v3.py --workers 4 --timeout 600 --path seeknal/tests/v1/multiturn
    uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn --scenario MT-013
    uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/singleturn --scenario CB-8
    uv run python scripts/test_multiturn_v3.py --path seeknal/tests/v1/multiturn --scenario stress_test_50_turn
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))

DEFAULT_YAML_PATH = PROJECT_ROOT / "seeknal" / "tests" / "v1"

# ---------------------------------------------------------------------------
# Logger — satu handler ke stdout dengan timestamp
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("multiturn-v3")


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
    scenario_id: str = ""


# ---------------------------------------------------------------------------
# YAML Loader — baca semua .yml dari direktori
# ---------------------------------------------------------------------------

def _load_yaml_tests(path: Path) -> list[Scenario]:
    if not path.is_dir():
        log.error("Path not found: %s", path)
        sys.exit(1)

    yml_files = sorted(path.rglob("*.yml"))
    if not yml_files:
        log.error("No .yml files found in %s", path)
        sys.exit(1)

    scenarios: list[Scenario] = []
    for yml_file in yml_files:
        with open(yml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "turns" not in data:
            log.warning("Skipping %s: missing 'turns' field", yml_file.name)
            continue

        turns = [
            Turn(
                prompt=t["prompt"],
                assert_contains=t.get("assert_contains", []),
                note=t.get("note", ""),
            )
            for t in data["turns"]
            if "prompt" in t
        ]
        if not turns:
            log.warning("Skipping %s: empty turns list", yml_file.name)
            continue

        scenarios.append(Scenario(
            name=data.get("name", yml_file.stem),
            scenario_id=data.get("scenario_id", yml_file.stem),
            description=data.get("description", ""),
            turns=turns,
        ))

    log.info("Loaded %d test(s) from %s", len(scenarios), path)
    return scenarios


# ---------------------------------------------------------------------------
# Runner — logic identik dengan test_multiturn_v2.py
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
    timed_out: bool = False
    ask_user_calls: int = 0


@dataclass
class ScenarioResult:
    name: str
    scenario_id: str
    turns: list[TurnResult]

    @property
    def passed(self) -> bool:
        return all(t.passed for t in self.turns)


def _extract_sqls(messages) -> list[str]:
    from pydantic_ai.messages import ToolCallPart
    sqls = []
    for m in messages:
        for p in getattr(m, "parts", []):
            if isinstance(p, ToolCallPart) and p.tool_name == "execute_sql":
                args = p.args if isinstance(p.args, dict) else {}
                sql = args.get("sql", "").strip()
                if sql:
                    sqls.append(sql)
    return sqls


def _run_turn_with_timeout(agent_ask, agent, deps, history, prompt, turn_timeout: int):
    if turn_timeout <= 0:
        return agent_ask(agent, deps, history, prompt)

    def _handler(signum, frame):
        raise TimeoutError(f"Turn melebihi batas waktu {turn_timeout}s")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(turn_timeout)
    try:
        return agent_ask(agent, deps, history, prompt)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def run_scenario(scenario: Scenario, turn_timeout: int = 0) -> ScenarioResult:
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor
    from pydantic_ai.messages import ModelResponse, ToolCallPart

    import seeknal.ask.testing as _testing_mod
    _testing_mod.save_ask_sql_test_results = lambda *a, **kw: Path("/dev/null")

    _load_project_env(PROJECT_ROOT)

    log.info("=" * 60)
    log.info("SCENARIO [%s] %s", scenario.scenario_id, scenario.name)
    log.info("  %s", scenario.description)
    log.info("  Turns: %d  |  turn_timeout: %ds", len(scenario.turns), turn_timeout)
    log.info("=" * 60)

    agent, deps, history, _ = create_agent(
        PROJECT_ROOT,
        environment="gateway",
    )
    log.info("Agent created — history shared across all turns in this scenario")

    turn_results: list[TurnResult] = []

    for i, turn in enumerate(scenario.turns, start=1):
        log.info("-" * 50)
        log.info("TURN %d/%d  prompt: %s", i, len(scenario.turns), turn.prompt[:80])
        if turn.note:
            log.info("  note: %s", turn.note)

        prev_len = len(history)

        reset_turn_governor(turn.prompt)
        start = time.monotonic()
        timed_out = False
        answer = ""

        try:
            answer = _run_turn_with_timeout(agent_ask, agent, deps, history, turn.prompt, turn_timeout)
        except TimeoutError as exc:
            timed_out = True
            answer = f"[TIMEOUT] {exc}"
            log.warning("TURN %d TIMEOUT: %s", i, exc)
        except Exception as exc:
            answer = f"[ERROR] {type(exc).__name__}: {exc}"
            log.error("TURN %d ERROR: %s", i, exc, exc_info=True)

        elapsed = time.monotonic() - start

        new_msgs = history[prev_len:]
        turn_llm_requests = sum(1 for m in new_msgs if isinstance(m, ModelResponse))
        turn_tool_calls = sum(
            1 for m in new_msgs
            for p in getattr(m, "parts", [])
            if isinstance(p, ToolCallPart)
        )
        turn_sqls = _extract_sqls(new_msgs)

        log.info(
            "TURN %d done — %.1fs | llm_req=%d | tool_calls=%d | sql=%d",
            i, elapsed, turn_llm_requests, turn_tool_calls, len(turn_sqls),
        )

        for j, sql in enumerate(turn_sqls, 1):
            log.info("  SQL %d:\n%s", j, "\n".join(f"    {line}" for line in sql.splitlines()))

        failures = []
        if not timed_out:
            answer_lower = answer.lower()
            for expected in turn.assert_contains:
                if expected.lower() not in answer_lower:
                    failures.append(f"missing: '{expected}'")

        if timed_out:
            failures.append("turn timed out")

        passed = not failures
        status = "✓ PASS" if passed else "✗ FAIL"
        log.info("TURN %d %s", i, status)
        for f in failures:
            log.warning("  FAIL: %s", f)
        log.info("  Answer (200c): %s", answer[:200])

        turn_results.append(TurnResult(
            turn_num=i,
            prompt=turn.prompt,
            answer=answer,
            elapsed_s=elapsed,
            llm_requests=turn_llm_requests,
            tool_calls=turn_tool_calls,
            sqls=turn_sqls,
            passed=passed,
            failures=failures,
            note=turn.note,
            timed_out=timed_out,
        ))

    return ScenarioResult(name=scenario.name, scenario_id=scenario.scenario_id, turns=turn_results)


def _filter_scenarios(scenarios: list[Scenario], select: str | None) -> list[Scenario]:
    if not select:
        return scenarios
    select_lower = select.lower()
    filtered = [
        s for s in scenarios
        if select_lower in s.name.lower() or select_lower in s.scenario_id.lower()
    ]
    if not filtered:
        log.warning("No scenarios matched filter: '%s'", select)
    return filtered


# ---------------------------------------------------------------------------
# Sequential runner (unchanged behaviour)
# ---------------------------------------------------------------------------

def run_all(scenarios: list[Scenario], select: str | None = None, turn_timeout: int = 0) -> list[ScenarioResult]:
    scenarios = _filter_scenarios(scenarios, select)
    log.info("Running %d scenario(s) sequentially", len(scenarios))
    results: list[ScenarioResult] = []
    for scenario in scenarios:
        result = run_scenario(scenario, turn_timeout=turn_timeout)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Parallel worker — seperti bench.py _run_one() tapi untuk multi-turn scenario
# ---------------------------------------------------------------------------

def _run_scenario_worker(scenario: Scenario, turn_timeout: int) -> tuple[ScenarioResult, str]:
    """Run a single scenario in a worker thread. Returns (Result, captured_output)."""
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor
    from pydantic_ai.messages import ModelResponse, ToolCallPart

    import seeknal.ask.testing as _testing_mod
    _testing_mod.save_ask_sql_test_results = lambda *a, **kw: Path("/dev/null")

    _load_project_env(PROJECT_ROOT)

    buf = io.StringIO()

    def out(msg: str = "") -> None:
        buf.write(msg + "\n")

    out(f">>> [{scenario.scenario_id}] {scenario.name}  ({len(scenario.turns)} turns)")

    try:
        agent, deps, history, _ = create_agent(PROJECT_ROOT, environment="gateway")

        turn_results: list[TurnResult] = []
        for i, turn in enumerate(scenario.turns, start=1):
            prev_len = len(history)
            reset_turn_governor(turn.prompt)
            start = time.monotonic()
            timed_out = False
            answer = ""

            try:
                answer = agent_ask(agent, deps, history, turn.prompt)
            except TimeoutError as exc:
                timed_out = True
                answer = f"[TIMEOUT] {exc}"
            except Exception as exc:
                answer = f"[ERROR] {type(exc).__name__}: {exc}"

            elapsed = time.monotonic() - start

            new_msgs = history[prev_len:]
            turn_llm_requests = sum(1 for m in new_msgs if isinstance(m, ModelResponse))
            turn_tool_calls = sum(
                1 for m in new_msgs
                for p in getattr(m, "parts", [])
                if isinstance(p, ToolCallPart)
            )
            turn_sqls = _extract_sqls(new_msgs)

            failures = []
            if not timed_out:
                answer_lower = answer.lower()
                for expected in turn.assert_contains:
                    if expected.lower() not in answer_lower:
                        failures.append(f"missing: '{expected}'")
            if timed_out:
                failures.append("turn timed out")

            passed = not failures
            status = "✓" if passed else "✗"

            out(f"  T{i} [{status}] {elapsed:6.1f}s  llm={turn_llm_requests:<3d}  tools={turn_tool_calls:<3d}  sql={len(turn_sqls):<2d}  '{turn.prompt[:50]}'")
            for f in failures:
                out(f"         {f}")
            for sql in turn_sqls:
                out(f"         SQL: {sql[:120]}")

            turn_results.append(TurnResult(
                turn_num=i,
                prompt=turn.prompt,
                answer=answer,
                elapsed_s=elapsed,
                llm_requests=turn_llm_requests,
                tool_calls=turn_tool_calls,
                sqls=turn_sqls,
                passed=passed,
                failures=failures,
                note=turn.note,
                timed_out=timed_out,
            ))

        result = ScenarioResult(name=scenario.name, scenario_id=scenario.scenario_id, turns=turn_results)
        total_time = sum(t.elapsed_s for t in turn_results)
        passed_turns = sum(1 for t in turn_results if t.passed)
        out(f"  → {passed_turns}/{len(turn_results)} passed  {total_time:.1f}s total")
        return result, buf.getvalue()

    except Exception as exc:
        out(f"  ERROR: {exc}")
        return ScenarioResult(name=scenario.name, scenario_id=scenario.scenario_id, turns=[]), buf.getvalue()


def run_all_parallel(
    scenarios: list[Scenario],
    select: str | None = None,
    turn_timeout: int = 0,
    workers: int = 2,
    timeout: float = 300.0,
) -> list[ScenarioResult]:
    """Run scenarios in parallel using a thread pool. Isolated per scenario."""
    scenarios = _filter_scenarios(scenarios, select)

    if not scenarios:
        return []

    workers = max(1, min(workers, len(scenarios)))
    print(f"\nRunning {len(scenarios)} scenario(s) with {workers} worker(s) in parallel\n")

    results_by_scenario_id: dict[str, ScenarioResult] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_sid = {
            pool.submit(_run_scenario_worker, s, turn_timeout): s.scenario_id
            for s in scenarios
        }

        for future in concurrent.futures.as_completed(future_to_sid):
            sid = future_to_sid[future]
            try:
                result, captured = future.result(timeout=timeout)
                print(captured, end="")
                print()
                results_by_scenario_id[sid] = result
            except concurrent.futures.TimeoutError:
                print(f"  ✗ [{sid}] TIMEOUT — exceeded {timeout}s\n")
                results_by_scenario_id[sid] = ScenarioResult(name=sid, scenario_id=sid, turns=[])
            except Exception as exc:
                print(f"  ✗ [{sid}] WORKER ERROR: {exc}\n")
                results_by_scenario_id[sid] = ScenarioResult(name=sid, scenario_id=sid, turns=[])

    # Return in original order
    return [results_by_scenario_id[s.scenario_id] for s in scenarios if s.scenario_id in results_by_scenario_id]


# ---------------------------------------------------------------------------
# Summary & Output
# ---------------------------------------------------------------------------

def print_summary(results: list[ScenarioResult]) -> None:
    print("\n" + "=" * 60)
    print("MULTI-TURN V3 SUMMARY")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        passed_turns = sum(1 for t in r.turns if t.passed)
        total_time = sum(t.elapsed_s for t in r.turns)
        label = f"[{r.scenario_id}] {r.name}"
        print(f"  [{status}] {label:<42s}  {passed_turns}/{len(r.turns)} turns  {total_time:.1f}s")
        for t in r.turns:
            ts = "✓" if t.passed else "✗"
            timeout_flag = " [TIMEOUT]" if t.timed_out else ""
            print(
                f"    {ts} Turn {t.turn_num}: {t.elapsed_s:.1f}s"
                f"  llm={t.llm_requests}  tools={t.tool_calls}  sql={len(t.sqls)}"
                f"{timeout_flag}  '{t.prompt[:40]}'"
            )
            for f in t.failures:
                print(f"       FAIL: {f}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    total_turns = sum(len(r.turns) for r in results)
    passed_turns = sum(sum(1 for t in r.turns if t.passed) for r in results)
    print()
    print(f"  Scenarios : {passed}/{total} passed")
    print(f"  Turns     : {passed_turns}/{total_turns} passed")
    print("=" * 60)


def save_json(results: list[ScenarioResult], select: str | None = None, version: str = "v1") -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = PROJECT_ROOT / "seeknal" / "tests" / "outputs" / today / version
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = f"multiturn_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / filename

    payload = {
        "project_path": str(PROJECT_ROOT),
        "timestamp": timestamp.isoformat(),
        "mode": "multiturn-v3",
        "version": version,
        "filter": select,
        "scenarios": [
            {
                "scenario_id": r.scenario_id,
                "name": r.name,
                "passed": r.passed,
                "turns": [
                    {
                        "turn_num": t.turn_num,
                        "prompt": t.prompt,
                        "passed": t.passed,
                        "timed_out": t.timed_out,
                        "elapsed_s": round(t.elapsed_s, 2),
                        "llm_requests": t.llm_requests,
                        "tool_calls": t.tool_calls,
                        "sqls": t.sqls,
                        "failures": t.failures,
                        "note": t.note,
                        "answer": t.answer,
                    }
                    for t in r.turns
                ],
                "summary": {
                    "total_turns": len(r.turns),
                    "passed_turns": sum(1 for t in r.turns if t.passed),
                    "failed_turns": sum(1 for t in r.turns if not t.passed),
                    "total_elapsed_s": round(sum(t.elapsed_s for t in r.turns), 2),
                },
            }
            for r in results
        ],
        "summary": {
            "total_scenarios": len(results),
            "passed_scenarios": sum(1 for r in results if r.passed),
            "failed_scenarios": sum(1 for r in results if not r.passed),
            "total_turns": sum(len(r.turns) for r in results),
            "passed_turns": sum(sum(1 for t in r.turns if t.passed) for r in results),
            "failed_turns": sum(sum(1 for t in r.turns if not t.passed) for r in results),
        },
    }

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-turn conversation tests v3 — load scenarios from YAML files"
    )
    parser.add_argument(
        "--scenario",
        help="Run only scenario by name (matches filename stem or scenario_id)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help=f"Path to YAML test directory (default: {DEFAULT_YAML_PATH})",
    )
    parser.add_argument(
        "--turn-timeout",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Per-turn SIGALRM timeout (sequential mode only, workers=1). 0 = no limit.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Override version for output path (default: from .env TEST_DATA_VERSION)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help="Number of parallel workers (default: 1 = sequential). Each scenario runs in its own thread.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        metavar="SECONDS",
        help="Per-scenario wall-clock timeout for parallel mode via future.result() (default: 300s). "
             "Worker thread is abandoned if it exceeds this limit, scenario marked TIMEOUT, "
             "other scenarios keep running.",
    )
    parser.add_argument(
        "--hide-sql",
        action="store_true",
        help="Suppress SQL output in captured per-scenario output (parallel mode only)",
    )
    args = parser.parse_args()

    # Load project env first to get TEST_DATA_VERSION
    from seeknal.cli.ask import _load_project_env
    _load_project_env(PROJECT_ROOT)

    version = args.version or os.getenv("TEST_DATA_VERSION", "v1")
    yaml_path = Path(args.path) if args.path else DEFAULT_YAML_PATH

    scenarios = _load_yaml_tests(yaml_path)

    log.info("Project  : %s", PROJECT_ROOT)
    log.info("YAML path: %s", yaml_path)
    log.info("Scenarios: %d", len(scenarios))
    log.info("Version  : %s", version)
    log.info("Workers  : %d", args.workers)
    log.info("turn-timeout: %ds", args.turn_timeout)

    if args.workers > 1:
        results = run_all_parallel(
            scenarios,
            select=args.scenario,
            turn_timeout=args.turn_timeout,
            workers=args.workers,
            timeout=args.timeout,
        )
    else:
        results = run_all(scenarios, select=args.scenario, turn_timeout=args.turn_timeout)

    print_summary(results)
    path = save_json(results, select=args.scenario, version=version)
    log.info("Output saved: %s", path)
