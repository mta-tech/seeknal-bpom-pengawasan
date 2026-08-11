"""
Benchmark: runs every test prompt against the live agent and reports
elapsed time, tool call count, and SQL executed per question.

SQL is shown by default. Use --hide-sql to suppress it.
Use --workers N to run N tests in parallel (default: 1 = sequential).

Usage:
    uv run python scripts/bench.py
    uv run python scripts/bench.py --select nie_total_2023
    uv run python scripts/bench.py --workers 3
    uv run python scripts/bench.py --workers 3 --select nie
    uv run python scripts/bench.py --hide-sql
    uv run python scripts/bench.py --timeout 120
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))


@dataclass
class BenchResult:
    name: str
    prompt: str
    elapsed_s: float
    requests: int = 0
    tool_calls: int = 0
    sqls: list[str] = field(default_factory=list)
    answer_preview: str = ""
    output: str = ""   # buffered per-test console text
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error

    def row(self) -> str:
        status = "✓" if self.passed else "✗"
        return (
            f"  {status} {self.name:<38s} "
            f"{self.elapsed_s:6.1f}s  "
            f"req={self.requests:<3d}  "
            f"tools={self.tool_calls:<3d}  "
            f"sql={len(self.sqls):<2d}"
        )


def _extract_sqls(history) -> list[str]:
    """Pull every execute_sql call's SQL text out of pydantic-ai message history."""
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


def _run_one(name: str, prompt: str, show_sql: bool) -> BenchResult:
    """Run a single test. Designed to be called from a thread pool worker."""
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor

    _load_project_env(PROJECT_ROOT)

    buf = io.StringIO()

    def out(line: str = "") -> None:
        buf.write(line + "\n")

    out(f"  → {name}")
    out(f"    {prompt[:80]}")

    start = time.monotonic()
    try:
        agent, deps, history, _ = create_agent(PROJECT_ROOT, environment="gateway")
        reset_turn_governor(prompt)

        answer = agent_ask(agent, deps, history, prompt)
        elapsed = time.monotonic() - start

        from pydantic_ai.messages import ModelResponse, ToolCallPart
        requests = sum(1 for m in history if isinstance(m, ModelResponse))
        tool_calls = sum(
            1 for m in history
            for p in getattr(m, "parts", [])
            if isinstance(p, ToolCallPart)
        )
        sqls = _extract_sqls(history)

        out(f"    {elapsed:.1f}s  req={requests}  tools={tool_calls}  sql_count={len(sqls)}")

        if show_sql and sqls:
            for i, sql in enumerate(sqls, 1):
                out(f"    --- SQL {i} ---")
                for line in sql.splitlines():
                    out(f"    {line}")

        out(f"    Answer: {answer[:160]}")

        return BenchResult(
            name=name,
            prompt=prompt,
            elapsed_s=elapsed,
            requests=requests,
            tool_calls=tool_calls,
            sqls=sqls,
            answer_preview=answer[:120] if answer else "",
            output=buf.getvalue(),
        )

    except Exception as exc:
        elapsed = time.monotonic() - start
        out(f"    ERROR: {exc}")
        return BenchResult(
            name=name,
            prompt=prompt,
            elapsed_s=elapsed,
            error=str(exc)[:200],
            output=buf.getvalue(),
        )


def run_bench(
    select: str | None = None,
    timeout: float = 180.0,
    show_sql: bool = True,
    workers: int = 1,
) -> list[BenchResult]:
    test_dir = PROJECT_ROOT / "seeknal" / "tests"
    files = sorted(test_dir.glob("*.yml"))
    if select:
        tokens = [t.strip() for t in select.split(",") if t.strip()]
        files = [f for f in files if any(t in f.stem for t in tokens)]

    cases: list[tuple[str, str]] = []
    for test_file in files:
        data = yaml.safe_load(test_file.read_text(encoding="utf-8"))
        prompt = (data.get("prompt") or data.get("question") or "").strip()
        name = data.get("name") or test_file.stem
        if prompt:
            cases.append((name, prompt))

    if not cases:
        return []

    workers = max(1, min(workers, len(cases)))
    print(f"Running {len(cases)} test(s) with {workers} worker(s)\n")

    results_by_name: dict[str, BenchResult] = {}

    if workers == 1:
        for name, prompt in cases:
            result = _run_one(name, prompt, show_sql)
            print(result.output, end="")
            print()
            results_by_name[name] = result
    else:
        print(f"  Starting: {', '.join(n for n, _ in cases)}\n")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_name = {
                pool.submit(_run_one, name, prompt, show_sql): name
                for name, prompt in cases
            }
            for future in concurrent.futures.as_completed(future_to_name):
                result = future.result(timeout=timeout)
                print(result.output, end="")
                print()
                results_by_name[result.name] = result

    # Return in original test file order
    return [results_by_name[name] for name, _ in cases if name in results_by_name]


def print_summary(results: list[BenchResult]) -> None:
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print("=" * 72)
    print("BENCHMARK RESULTS")
    print("=" * 72)
    for r in results:
        print(r.row())
        if r.error:
            print(f"    error: {r.error[:80]}")

    if not results:
        print("  (no tests ran)")
        return

    times = [r.elapsed_s for r in passed]
    print()
    print(f"  Total  : {len(results)} tests")
    print(f"  Passed : {len(passed)}")
    print(f"  Failed : {len(failed)}")
    if times:
        print(f"  Fastest: {min(times):.1f}s  ({passed[times.index(min(times))].name})")
        print(f"  Slowest: {max(times):.1f}s  ({passed[times.index(max(times))].name})")
        print(f"  Average: {sum(times)/len(times):.1f}s")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark seeknal ask per question")
    parser.add_argument("--select", help="Run only tests whose name contains this string")
    parser.add_argument("--timeout", type=float, default=180.0, help="Per-test timeout seconds")
    parser.add_argument("--hide-sql", action="store_true", help="Suppress SQL output")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers (default: 1)")
    args = parser.parse_args()

    print(f"\nProject: {PROJECT_ROOT}")

    results = run_bench(
        select=args.select,
        timeout=args.timeout,
        show_sql=not args.hide_sql,
        workers=args.workers,
    )
    print_summary(results)
