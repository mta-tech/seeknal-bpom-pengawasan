"""Production load test runner for the IBA v6 API on alpha.keycenter.ai.

This script validates that the IBA agent system can correctly answer BPOM-
related questions through the full IBA stack: Keycloak authentication (ROPC),
POST /v6/chat for message initiation, and GET /v6/sse for streaming responses.

The script measures latency (p50/p95/p99), throughput, error rates, and
assertion pass/fail rates for each test case defined in YAML files.

Execution Modes
---------------
sequential (default):
    Sends one YAML scenario at a time with a configurable stagger delay
    between requests. Automatically retries empty answers with exponential
    backoff. Best for reliable validation of all test cases.

--parallel:
    Launches all selected scenarios concurrently using asyncio.gather.
    Uses a single Keycloak token. Useful for burst/concurrency testing.

--multi-user:
    Each user in ``test_users`` authenticates independently and fires
    one YAML scenario in parallel. Scenarios are distributed round-robin
    across users (1 scenario per user). Tests true multi-user concurrent
    access.

--multi-user --distribute:
    Like ``--multi-user`` but distributes ALL scenarios evenly across
    users as sequential batches. Each user gets ``ceil(N/users)``
    scenarios and runs them one-by-one with ``--stagger-ms`` delay
    between each. All users run their batches in parallel. If there are
    fewer scenarios than users, the extra users are silently skipped
    (no auth, no error). Best for full test coverage with multiple
    auth tokens and controlled server load.

--multiturn:
    Each user runs ALL turns of their assigned scenario sequentially,
    carrying the conversation_id between turns to simulate a real
    multi-turn conversation. All users run their full scenario in
    parallel with each other.

Key Findings (2026-06-15)
-------------------------
The production worker has ``max_concurrency=1`` (HTTP transport), meaning
it processes one request at a time. When 20 requests are sent simultaneously:

- First 6-7 succeed (processed immediately)
- Remaining 13-14 receive empty answers (worker backlog)
- Empty answers arrive after ~15 seconds (one SSE heartbeat interval)

Solution: Sequential execution with 10s stagger + 60s retry wait achieves
20/20 pass rate.

Output
------
JSON results are saved to ``seeknal/tests/outputs/<date>/<version>/``.
The aggregate section contains p50/p95/p99 latency, throughput, and
error rate. Per-request entries include answer text, tool call count,
assertion results, and full latency breakdown.

Usage
-----
    # Sequential (default) — reliable, all 20 cases
    uv run python scripts/test_concurrency_production.py

    # Parallel burst — single user, all cases at once
    uv run python scripts/test_concurrency_production.py --parallel

    # Multi-user — N users, one case each, fired simultaneously
    uv run python scripts/test_concurrency_production.py --multi-user --stagger-ms 500 --stream-timeout 600

    # Multi-user distributed — all cases split evenly across N users, each runs batch sequentially
    uv run python scripts/test_concurrency_production.py --multi-user --distribute --path seeknal/tests/v1/singleturn --stagger-ms 25000 --stream-timeout 1800

    # Multiturn — N users each run a full multi-turn scenario
    uv run python scripts/test_concurrency_production.py --multiturn --path seeknal/tests/v1/production/multiturn --stagger 500

    # Realistic load — random arrival + think-time between turns
    uv run python scripts/test_concurrency_production.py --multiturn --stagger 30000 --turn-delay-ms 8000 --random-arrival

    # Quick test — only 5 cases, no retry
    uv run python scripts/test_concurrency_production.py --concurrency 5 --no-retry-empty
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from iba_test_client.auth import KeycloakClient
from iba_test_client.chat import Answer, IBAChatClient
from iba_test_client.metrics import (
    LatencyTracker,
    RequestMetrics,
    compute_aggregate,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("concurrency-prod")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    prompt: str
    assert_contains: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Scenario:
    name: str
    scenario_id: str
    turns: list[Turn]
    description: str = ""


@dataclass
class RequestResult:
    scenario_id: str
    user_id: str
    turn_num: int
    prompt: str
    answer: str
    passed: bool
    failures: list[str]
    metrics: RequestMetrics
    conversation_id: str = ""
    attempt: int = 1


@dataclass
class ConcurrencyResult:
    mode: str
    config: dict
    requests: list[RequestResult]
    aggregate: dict


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _load_yaml_tests(path: Path) -> list[Scenario]:
    """Load test scenarios from YAML files in the given directory.

    Each YAML file must contain a ``turns`` list with at least one turn
    having a ``prompt`` field. Optional fields include ``assert_contains``
    (list of expected strings) and ``note`` (developer annotation).

    Args:
        path: Directory containing .yml test scenario files.

    Returns:
        List of Scenario objects sorted by filename.
    """
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
        if turns:
            scenarios.append(
                Scenario(
                    name=data.get("name", yml_file.stem),
                    scenario_id=data.get("scenario_id", yml_file.stem),
                    description=data.get("description", ""),
                    turns=turns,
                )
            )

    log.info("Loaded %d test(s) from %s", len(scenarios), path)
    return scenarios


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        log.error("Config not found: %s", config_path)
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Single turn runner
# ---------------------------------------------------------------------------


def _run_single_turn_sync(
    client: IBAChatClient,
    prompt: str,
    domain_id: str,
    conversation_id: str,
    stream_timeout: int,
    assert_contains: list[str],
    scenario_id: str,
    user_id: str,
    turn_num: int,
    attempt: int = 1,
) -> RequestResult:
    """Execute a single chat turn synchronously and evaluate assertions.

    Sends a prompt to the IBA API, waits for the SSE stream to complete,
    and checks whether the response contains all expected strings.

    Args:
        client: Authenticated IBAChatClient instance.
        prompt: The user's question text.
        domain_id: Target domain UUID for the chat request.
        conversation_id: Existing conversation ID (empty string for new).
        stream_timeout: Max seconds to wait for SSE stream completion.
        assert_contains: List of strings that must appear in the answer.
        scenario_id: Identifier for the test scenario (for logging).
        user_id: Identifier for the user (for logging).
        turn_num: Turn number within the scenario (1-indexed).
        attempt: Retry attempt number (for tracking in results).

    Returns:
        RequestResult with answer text, pass/fail status, and metrics.
    """
    answer = client.ask(
        query=prompt,
        domain_id=domain_id,
        conversation_id=conversation_id,
        stream_timeout=stream_timeout,
    )
    failures = []
    if answer.error and not answer.timed_out:
        failures.append(f"error: {answer.error}")
    if not answer.timed_out and not answer.error:
        answer_lower = answer.answer.lower()
        for expected in assert_contains:
            if str(expected).lower() not in answer_lower:
                failures.append(f"missing: '{expected}'")
    if answer.timed_out:
        failures.append("turn timed out")

    return RequestResult(
        scenario_id=scenario_id,
        user_id=user_id,
        turn_num=turn_num,
        prompt=prompt,
        answer=answer.answer,
        passed=not failures,
        failures=failures,
        metrics=answer.metrics or RequestMetrics(),
        conversation_id=answer.conversation_id,
        attempt=attempt,
    )


# ---------------------------------------------------------------------------
# Multi-user runner: each user authenticates independently
# ---------------------------------------------------------------------------


async def run_multi_user(
    users: list[dict],
    kc: KeycloakClient,
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list[Scenario],
    stream_timeout: int,
    stagger_ms: int = 0,
) -> list[RequestResult]:
    """Run test cases with multiple users, each authenticating independently.

    Each user in the provided list logs in with their own Keycloak credentials
    and fires one scenario in parallel. Scenarios are distributed round-robin
    across users so all test cases are covered even with more users than cases.

    This mode simulates realistic multi-user concurrent access where each user
    has their own authentication token and session.

    Args:
        users: List of dicts with 'email' and 'password' keys.
        kc: KeycloakClient instance for authentication.
        base_url: IBA API base URL.
        service_path: API service path prefix.
        domain_id: Target domain UUID.
        scenarios: List of test scenarios to distribute across users.
        stream_timeout: Max seconds to wait for SSE stream completion.
        stagger_ms: Milliseconds between launching each user (0 = all at once).

    Returns:
        List of RequestResult objects, one per user.
    """
    loop = asyncio.get_event_loop()
    n = len(users)

    log.info("Authenticating %d users...", n)
    tokens: list[str] = []
    for u in users:
        try:
            token = kc.get_valid_token(u["email"], u["password"])
            tokens.append(token)
            log.info("  Login OK: %s", u["email"])
        except Exception as exc:
            log.error("  Login FAILED: %s — %s", u["email"], exc)
            tokens.append("")

    log.info(
        "Running %d users in PARALLEL (stagger=%dms between launches, round-robin over %d cases)",
        n, stagger_ms, len(scenarios),
    )

    async def _run_user(idx: int) -> RequestResult:
        token = tokens[idx]
        user_email = users[idx]["email"]
        scenario = scenarios[idx % len(scenarios)]
        turn = scenario.turns[0]

        if not token:
            return RequestResult(
                scenario_id=scenario.scenario_id,
                user_id=user_email,
                turn_num=1,
                prompt=turn.prompt,
                answer="",
                passed=False,
                failures=["login failed"],
                metrics=RequestMetrics(),
            )

        if stagger_ms > 0 and idx > 0:
            await asyncio.sleep(idx * stagger_ms / 1000.0)

        log.info(
            "[launch %d/%d] %s → %s: %s",
            idx + 1, n, user_email, scenario.scenario_id, turn.prompt[:50],
        )

        client = IBAChatClient(token, base_url, service_path)
        return await loop.run_in_executor(
            None,
            lambda s=scenario, e=user_email: _run_single_turn_sync(
                client,
                s.turns[0].prompt,
                domain_id,
                "",
                stream_timeout,
                s.turns[0].assert_contains,
                s.scenario_id,
                e,
                1,
            ),
        )

    raw = await asyncio.gather(*[_run_user(i) for i in range(n)], return_exceptions=True)

    results: list[RequestResult] = []
    for i, r in enumerate(raw):
        if isinstance(r, RequestResult):
            status = "PASS" if r.passed else ("EMPTY" if not r.answer and not r.metrics.error else "FAIL")
            log.info(
                "  [%s] %s / %s  (%.0fms, tools=%d, ans=%d)",
                status, r.user_id, r.scenario_id,
                r.metrics.total_latency_ms, r.metrics.tool_calls, len(r.answer),
            )
            results.append(r)
        else:
            log.error("  [ERROR] user %d raised exception: %s", i, r)

    return results


# ---------------------------------------------------------------------------
# Multi-user distributed runner
# ---------------------------------------------------------------------------


async def run_multi_user_distributed(
    users: list[dict],
    kc: "KeycloakClient",
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list,
    stream_timeout: int,
    stagger_ms: int = 500,
    collector: list | None = None,
) -> list:
    """Distribute all scenarios evenly across users; each user runs their chunk sequentially.

    If scenarios < users, extra users are silently skipped (no auth, no error).
    If scenarios > users, each user gets math.ceil(n/users) scenarios.
    All users run their batches in parallel with each other.

    Args:
        collector: Optional external list. Results are appended to it as each
                   batch completes, so the caller can recover partial results
                   on KeyboardInterrupt before this coroutine returns.
    """
    n_users = len(users)
    n_cases = len(scenarios)
    loop = asyncio.get_event_loop()

    if n_cases == 0:
        return []

    chunk_size = math.ceil(n_cases / n_users)
    batches: list[list] = [scenarios[i : i + chunk_size] for i in range(0, n_cases, chunk_size)]
    while len(batches) < n_users:
        batches.append([])

    active_count = sum(1 for b in batches if b)
    log.info(
        "Distributing %d scenarios across %d users (%d active, ~%d per user)",
        n_cases, n_users, active_count, chunk_size,
    )
    if active_count < n_users:
        log.info(
            "  Note: %d user(s) have no scenarios and will be skipped",
            n_users - active_count,
        )

    tokens: list[str] = []
    for i, u in enumerate(users):
        if not batches[i]:
            tokens.append("")
            continue
        try:
            token = kc.get_valid_token(u["email"], u["password"])
            tokens.append(token)
            log.info("  Login OK: %s (%d cases)", u["email"], len(batches[i]))
        except Exception as exc:
            log.error("  Login FAILED: %s — %s", u["email"], exc)
            tokens.append("")

    async def _run_user_batch(user_idx: int) -> list:
        batch = batches[user_idx]
        if not batch:
            return []

        token = tokens[user_idx]
        email = users[user_idx]["email"]

        if not token:
            return [
                RequestResult(
                    scenario_id=s.scenario_id,
                    user_id=email,
                    turn_num=1,
                    prompt=s.turns[0].prompt,
                    answer="",
                    passed=False,
                    failures=["login failed"],
                    metrics=RequestMetrics(),
                )
                for s in batch
            ]

        client = IBAChatClient(token, base_url, service_path)
        results = []
        for j, scenario in enumerate(batch):
            log.info(
                "[user %d/%d | case %d/%d] %s → %s",
                user_idx + 1, n_users, j + 1, len(batch),
                email, scenario.scenario_id,
            )
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda s=scenario, e=email: _run_single_turn_sync(
                        client,
                        s.turns[0].prompt,
                        domain_id,
                        "",
                        stream_timeout,
                        s.turns[0].assert_contains,
                        s.scenario_id,
                        e,
                        1,
                    ),
                )
            except Exception as exc:
                log.error(
                    "  [CRASH] %s / %s: %s — continuing batch",
                    email, scenario.scenario_id, exc,
                )
                result = RequestResult(
                    scenario_id=scenario.scenario_id,
                    user_id=email,
                    turn_num=1,
                    prompt=scenario.turns[0].prompt,
                    answer="",
                    passed=False,
                    failures=[f"exception: {exc}"],
                    metrics=RequestMetrics(),
                )
            status = "PASS" if result.passed else ("EMPTY" if not result.answer and not result.metrics.error else "FAIL")
            log.info(
                "  [%s] %s / %s  (%.0fms, tools=%d, ans=%d)",
                status, email, scenario.scenario_id,
                result.metrics.total_latency_ms, result.metrics.tool_calls, len(result.answer),
            )
            results.append(result)
            if j < len(batch) - 1 and stagger_ms > 0:
                await asyncio.sleep(stagger_ms / 1000.0)
        return results

    flat: list = []

    async def _collect(user_idx: int) -> None:
        batch_result = await _run_user_batch(user_idx)
        flat.extend(batch_result)
        if collector is not None:
            collector.extend(batch_result)

    results_or_errors = await asyncio.gather(
        *[_collect(i) for i in range(n_users)],
        return_exceptions=True,
    )
    for i, r in enumerate(results_or_errors):
        if isinstance(r, Exception):
            log.error("  [ERROR] user %d batch raised exception: %s", i, r)

    return flat


# ---------------------------------------------------------------------------
# Multi-user multiturn runner
# ---------------------------------------------------------------------------


async def run_multiturn_users(
    users: list[dict],
    kc: KeycloakClient,
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list[Scenario],
    stream_timeout: int,
    stagger_ms: int = 0,
    turn_delay_ms: int = 0,
    random_arrival: bool = False,
) -> list[RequestResult]:
    """Run multi-turn scenarios with multiple users in parallel.

    Each user runs ALL turns of their assigned scenario sequentially,
    carrying the conversation_id between turns to maintain context.
    All users run their full scenario in parallel with each other.

    This mode simulates realistic multi-turn conversations where users
    ask follow-up questions within the same conversation session.

    Args:
        users: List of dicts with 'email' and 'password' keys.
        kc: KeycloakClient instance for authentication.
        base_url: IBA API base URL.
        service_path: API service path prefix.
        domain_id: Target domain UUID.
        scenarios: List of test scenarios (assigned round-robin to users).
        stream_timeout: Max seconds to wait for SSE stream completion.
        stagger_ms: Milliseconds between launching each user.
        turn_delay_ms: Think-time pause between turns (simulates reading).
        random_arrival: If True, users arrive at random times within the
                        stagger window instead of linearly staggered.

    Returns:
        List of RequestResult objects, one per turn per user.
    """
    loop = asyncio.get_event_loop()
    n = len(users)

    log.info("Authenticating %d users...", n)
    tokens: list[str] = []
    for u in users:
        try:
            token = kc.get_valid_token(u["email"], u["password"])
            tokens.append(token)
            log.info("  Login OK: %s", u["email"])
        except Exception as exc:
            log.error("  Login FAILED: %s — %s", u["email"], exc)
            tokens.append("")

    arrival_mode = "random within window" if random_arrival else "linear stagger"
    log.info(
        "Running %d users in PARALLEL — arrival=%s (window=%ds), turn_delay=%dms",
        n, arrival_mode, stagger_ms * n // 1000, turn_delay_ms,
    )

    async def _run_user_scenario(idx: int) -> list[RequestResult]:
        token = tokens[idx]
        user_email = users[idx]["email"]
        scenario = scenarios[idx % len(scenarios)]
        total_turns = len(scenario.turns)

        if not token:
            turn = scenario.turns[0]
            return [RequestResult(
                scenario_id=scenario.scenario_id,
                user_id=user_email,
                turn_num=1,
                prompt=turn.prompt,
                answer="",
                passed=False,
                failures=["login failed"],
                metrics=RequestMetrics(),
            )]

        # Arrival delay: random within window OR linear
        if stagger_ms > 0:
            window_sec = stagger_ms * n / 1000.0
            if random_arrival:
                arrival_sec = random.uniform(0, window_sec)
            else:
                arrival_sec = idx * stagger_ms / 1000.0
            if arrival_sec > 0:
                log.info(
                    "[user %d/%d] %s arrives in %.1fs",
                    idx + 1, n, user_email, arrival_sec,
                )
                await asyncio.sleep(arrival_sec)

        client = IBAChatClient(token, base_url, service_path)
        conversation_id = ""
        turn_results: list[RequestResult] = []

        for turn_num, turn in enumerate(scenario.turns, 1):
            # Think-time between turns (simulates user reading the previous answer)
            if turn_delay_ms > 0 and turn_num > 1:
                log.debug("[user %d/%d][T%d] %s reading... %.1fs",
                          idx + 1, n, turn_num, user_email, turn_delay_ms / 1000.0)
                await asyncio.sleep(turn_delay_ms / 1000.0)

            log.info(
                "[user %d/%d][T%d/%d] %s → %s: %s",
                idx + 1, n, turn_num, total_turns,
                user_email, scenario.scenario_id, turn.prompt[:50],
            )
            result = await loop.run_in_executor(
                None,
                lambda t=turn, cid=conversation_id: _run_single_turn_sync(
                    client,
                    t.prompt,
                    domain_id,
                    cid,
                    stream_timeout,
                    t.assert_contains,
                    scenario.scenario_id,
                    user_email,
                    turn_num,
                ),
            )
            conversation_id = result.conversation_id
            turn_results.append(result)

        return turn_results

    raw = await asyncio.gather(
        *[_run_user_scenario(i) for i in range(n)], return_exceptions=True
    )

    all_results: list[RequestResult] = []
    for i, r in enumerate(raw):
        if isinstance(r, list):
            for tr in r:
                status = "PASS" if tr.passed else (
                    "EMPTY" if not tr.answer and not tr.metrics.error else "FAIL"
                )
                log.info(
                    "  [%s] T%d  %s / %s  (%.0fms, tools=%d, ans=%d)",
                    status, tr.turn_num, tr.user_id, tr.scenario_id,
                    tr.metrics.total_latency_ms, tr.metrics.tool_calls, len(tr.answer),
                )
            all_results.extend(r)
        else:
            log.error("  [ERROR] user %d raised exception: %s", i, r)

    return all_results


# ---------------------------------------------------------------------------
# Main runner: sequential + smart retry
# ---------------------------------------------------------------------------


async def run_all(
    token: str,
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list[Scenario],
    stream_timeout: int,
    concurrency: int,
    stagger_ms: int = 0,
    retry_empty: bool = True,
    max_retries: int = 2,
    retry_wait: int = 60,
    parallel: bool = False,
) -> list[RequestResult]:
    """Run test cases in sequential or parallel mode with smart retry.

    In sequential mode (default), cases are sent one at a time with a
    configurable stagger delay. Empty answers are automatically retried
    after waiting for the worker to recover.

    In parallel mode (--parallel), all cases are launched concurrently
    using asyncio.gather with optional stagger between launches.

    The smart retry mechanism detects empty answers (common when the
    production worker is overloaded) and retries them after a configurable
    wait period (default: 60s) to let the worker clear its backlog.

    Args:
        token: Keycloak JWT access token.
        base_url: IBA API base URL.
        service_path: API service path prefix.
        domain_id: Target domain UUID.
        scenarios: List of test scenarios to run.
        stream_timeout: Max seconds to wait for SSE stream completion.
        concurrency: Number of cases to run (capped by available scenarios).
        stagger_ms: Milliseconds between each request launch.
        retry_empty: Whether to retry cases with empty answers.
        max_retries: Maximum retry attempts for empty answers.
        retry_wait: Seconds to wait before each retry batch.
        parallel: If True, launch all cases concurrently.

    Returns:
        List of RequestResult objects for all executed cases.
    """
    client = IBAChatClient(token, base_url, service_path)
    loop = asyncio.get_event_loop()

    selected = scenarios[:concurrency]

    if parallel:
        log.info(
            "Running %d cases in PARALLEL (launch stagger=%dms, retry_empty=%s, max_retries=%d, retry_wait=%ds)",
            len(selected), stagger_ms, retry_empty, max_retries, retry_wait,
        )

        async def _launch_with_stagger(scenario: Scenario, idx: int) -> RequestResult:
            if stagger_ms > 0 and idx > 0:
                await asyncio.sleep(idx * stagger_ms / 1000.0)
            log.info("[launch %d/%d] %s: %s", idx + 1, len(selected), scenario.scenario_id, scenario.turns[0].prompt[:60])
            return await loop.run_in_executor(
                None,
                lambda s=scenario: _run_single_turn_sync(
                    client,
                    s.turns[0].prompt,
                    domain_id,
                    "",
                    stream_timeout,
                    s.turns[0].assert_contains,
                    s.scenario_id,
                    "user-0",
                    1,
                ),
            )

        tasks = [_launch_with_stagger(s, i) for i, s in enumerate(selected)]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        results: list[RequestResult] = []
        for i, r in enumerate(raw):
            if isinstance(r, RequestResult):
                status = "PASS" if r.passed else ("EMPTY" if not r.answer and not r.metrics.error else "FAIL")
                log.info(
                    "  [%s] %s  (%.0fms, tools=%d, answer_len=%d)",
                    status, r.scenario_id, r.metrics.total_latency_ms, r.metrics.tool_calls, len(r.answer),
                )
                results.append(r)
            else:
                log.error("  [ERROR] case %d raised exception: %s", i + 1, r)
    else:
        log.info(
            "Running %d cases sequentially (stagger=%dms, retry_empty=%s, max_retries=%d, retry_wait=%ds)",
            len(selected), stagger_ms, retry_empty, max_retries, retry_wait,
        )

        results = []

        for i, scenario in enumerate(selected):
            turn = scenario.turns[0]
            log.info("[%d/%d] %s: %s", i + 1, len(selected), scenario.scenario_id, turn.prompt[:60])

            result = await loop.run_in_executor(
                None,
                lambda s=scenario, idx=i: _run_single_turn_sync(
                    client,
                    s.turns[0].prompt,
                    domain_id,
                    "",
                    stream_timeout,
                    s.turns[0].assert_contains,
                    s.scenario_id,
                    "user-0",
                    1,
                ),
            )

            status = "PASS" if result.passed else ("EMPTY" if not result.answer and not result.metrics.error else "FAIL")
            log.info(
                "  → %s  (%.0fms, tools=%d, answer_len=%d)",
                status, result.metrics.total_latency_ms, result.metrics.tool_calls, len(result.answer),
            )

            results.append(result)

            # Stagger between requests
            if stagger_ms > 0 and i < len(selected) - 1:
                await asyncio.sleep(stagger_ms / 1000.0)

    # Retry empty answers
    if retry_empty:
        for attempt_num in range(2, max_retries + 2):
            empty_cases = [r for r in results if r.answer == "" and not r.metrics.error]
            if not empty_cases:
                break

            log.info("=" * 50)
            log.info(
                "RETRY attempt %d: %d cases with empty answers (waiting %ds for worker recovery)",
                attempt_num, len(empty_cases), retry_wait,
            )
            log.info("=" * 50)

            # Wait for worker to recover
            log.info("Waiting %ds for worker to clear backlog...", retry_wait)
            await asyncio.sleep(retry_wait)

            scenario_map = {s.scenario_id: s for s in scenarios}

            for i, old_result in enumerate(empty_cases):
                scenario = scenario_map.get(old_result.scenario_id)
                if not scenario:
                    continue

                turn = scenario.turns[0]
                log.info(
                    "[retry %d] [%d/%d] %s: %s",
                    attempt_num, i + 1, len(empty_cases), scenario.scenario_id, turn.prompt[:60],
                )

                new_result = await loop.run_in_executor(
                    None,
                    lambda s=scenario: _run_single_turn_sync(
                        client,
                        s.turns[0].prompt,
                        domain_id,
                        "",
                        stream_timeout,
                        s.turns[0].assert_contains,
                        s.scenario_id,
                        "user-0",
                        1,
                        attempt=attempt_num,
                    ),
                )

                status = "PASS" if new_result.passed else ("EMPTY" if not new_result.answer and not new_result.metrics.error else "FAIL")
                log.info(
                    "  → %s  (%.0fms, tools=%d, answer_len=%d)",
                    status, new_result.metrics.total_latency_ms, new_result.metrics.tool_calls, len(new_result.answer),
                )

                # Replace old result
                results = [new_result if r.scenario_id == old_result.scenario_id else r for r in results]

                # Small stagger between retries
                if i < len(empty_cases) - 1:
                    await asyncio.sleep(5)

    return results


# ---------------------------------------------------------------------------
# Summary & output
# ---------------------------------------------------------------------------


def print_summary(result: ConcurrencyResult) -> None:
    """Print a formatted summary of test results to stdout.

    Displays aggregate metrics (latency percentiles, throughput, error rate)
    and per-request details including pass/fail status, latency, tool call
    count, answer length, and retry attempt number.

    Args:
        result: ConcurrencyResult object containing all test results.
    """
    print("\n" + "=" * 70)
    print("PRODUCTION TEST SUMMARY")
    print("=" * 70)
    print(f"  Mode       : {result.mode}")
    print(f"  Target     : {result.config.get('base_url', 'N/A')}")
    print(f"  Domain ID  : {result.config.get('domain_id', 'N/A')}")
    print(f"  Timeout    : {result.config.get('stream_timeout', 0)}s")
    print()

    agg = result.aggregate
    print(f"  Total requests : {agg.get('total_requests', 0)}")
    print(f"  Successful     : {agg.get('successful', 0)}")
    print(f"  Failed         : {agg.get('failed', 0)}")
    print(f"  Error rate     : {agg.get('error_rate_percent', 0)}%")
    print()
    print(f"  Latency p50    : {agg.get('latency_p50_ms', 0):.0f}ms")
    print(f"  Latency p95    : {agg.get('latency_p95_ms', 0):.0f}ms")
    print(f"  Latency p99    : {agg.get('latency_p99_ms', 0):.0f}ms")
    print(f"  Latency min    : {agg.get('latency_min_ms', 0):.0f}ms")
    print(f"  Latency max    : {agg.get('latency_max_ms', 0):.0f}ms")
    print(f"  Latency avg    : {agg.get('latency_avg_ms', 0):.0f}ms")
    print(f"  Throughput     : {agg.get('throughput_req_per_sec', 0):.2f} req/s")
    print()

    passed = sum(1 for r in result.requests if r.passed)
    failed_count = len(result.requests) - passed
    empty_count = sum(1 for r in result.requests if r.answer == "" and not r.metrics.error)
    print(f"  Assertions     : {passed}/{len(result.requests)} passed")
    print(f"  Empty answers  : {empty_count}")
    print()

    multiturn = result.mode == "multi-user-multiturn"
    for r in result.requests:
        status = "PASS" if r.passed else "FAIL"
        latency = r.metrics.total_latency_ms
        answer_len = len(r.answer)
        retry_flag = f" (r{r.attempt})" if r.attempt > 1 else ""
        empty_flag = " EMPTY" if answer_len == 0 and not r.metrics.error else ""
        turn_tag = f" T{r.turn_num}" if multiturn else ""
        print(
            f"    [{status}]{empty_flag:<6} {r.scenario_id:<12s}{turn_tag:<4}  {latency:>8.0f}ms  "
            f"tools={r.metrics.tool_calls:<3d}  ans={answer_len:<5d}{retry_flag}  '{r.prompt[:35]}'"
        )
        for f in r.failures:
            print(f"           FAIL: {f}")

    print("=" * 70)


def save_json(result: ConcurrencyResult, version: str = "concurrency-production") -> Path:
    """Save test results to a JSON file.

    Creates a structured JSON file containing per-request results (prompt,
    answer, passed, failures, metrics) and aggregate statistics (latency
    percentiles, throughput, error rate).

    Output path: seeknal/tests/outputs/<YYYY-MM-DD>/<version>/concurrency_<timestamp>.json

    Args:
        result: ConcurrencyResult object containing all test results.
        version: Version label for the output directory name.

    Returns:
        Path to the saved JSON file.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = PROJECT_ROOT / "seeknal" / "tests" / "outputs" / today / version
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = f"concurrency_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / filename

    payload = {
        "mode": result.mode,
        "config": result.config,
        "timestamp": timestamp.isoformat(),
        "per_request": [
            {
                "scenario_id": r.scenario_id,
                "user_id": r.user_id,
                "turn": r.turn_num,
                "prompt": r.prompt,
                "answer": r.answer[:500],
                "passed": r.passed,
                "failures": r.failures,
                "attempt": r.attempt,
                "answer_length": len(r.answer),
                "metrics": r.metrics.to_dict(),
            }
            for r in result.requests
        ],
        "aggregate": result.aggregate,
    }

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Production test — sequential with smart retry"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Number of cases to run (default: 20)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="scripts/iba_test_config_production.yml",
        help="Path to test config YAML",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to YAML test directory (overrides config)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="IBA base URL (overrides config)",
    )
    parser.add_argument(
        "--domain-id",
        type=str,
        default=None,
        help="Domain UUID (overrides config)",
    )
    parser.add_argument(
        "--stream-timeout",
        type=int,
        default=1800,
        help="Max seconds of inactivity per SSE stream (default: 3600)",
    )
    parser.add_argument(
        "--stagger-ms",
        type=int,
        default=10000,
        help="Milliseconds between each sequential request (default: 10000)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run all cases in parallel (asyncio.gather) instead of sequentially",
    )
    parser.add_argument(
        "--multi-user",
        action="store_true",
        help="Each user in test_users authenticates independently and fires one case in parallel",
    )
    parser.add_argument(
        "--distribute",
        action="store_true",
        help="With --multi-user: distribute ALL scenarios evenly across users (instead of 1 per user). Extra users with no scenarios are silently skipped.",
    )
    parser.add_argument(
        "--multiturn",
        action="store_true",
        help="Each user runs ALL turns of their assigned scenario (multiturn conversation, sequential turns per user, parallel across users)",
    )
    parser.add_argument(
        "--turn-delay-ms",
        type=int,
        default=0,
        help="Milliseconds to wait between turns within a user session (simulates reading time, default: 0)",
    )
    parser.add_argument(
        "--random-arrival",
        action="store_true",
        help="Users arrive at random times within the stagger window instead of linearly (simulates organic traffic)",
    )
    parser.add_argument(
        "--no-retry-empty",
        action="store_true",
        help="Disable retry for empty answers",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Max retry attempts for empty answers (default: 2)",
    )
    parser.add_argument(
        "--retry-wait",
        type=int,
        default=60,
        help="Seconds to wait before retry batch (default: 60)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="concurrency-production",
        help="Version label for output path",
    )
    args = parser.parse_args()

    # Load config
    config_path = PROJECT_ROOT / args.config
    config = _load_config(config_path)

    iba_config = config.get("iba", {})
    kc_config = config.get("keycloak", {})
    users = config.get("test_users", [])

    base_url = args.base_url or iba_config.get("base_url", "https://alpha.keycenter.ai/api")
    service_path = iba_config.get("service_path", "")
    kc_url = kc_config.get("url", "https://auth.keycenter.ai/auth")
    kc_realm = kc_config.get("realm", "keycenter")
    kc_client_id = kc_config.get("client_id", "web")
    kc_client_secret = kc_config.get("client_secret", "")

    domain_id = args.domain_id or config.get("domain_id", "")
    if not domain_id:
        log.error("No domain_id provided in config or CLI")
        sys.exit(1)

    yaml_path = (
        Path(args.path) if args.path
        else PROJECT_ROOT / config.get("seeknal", {}).get("yaml_path", "seeknal/tests/v1/production")
    )

    # Load scenarios
    scenarios = _load_yaml_tests(yaml_path)
    if not scenarios:
        log.error("No scenarios loaded")
        sys.exit(1)

    concurrency = min(args.concurrency, len(scenarios))

    if args.multiturn:
        mode_label = "MULTI-USER MULTITURN"
    elif args.multi_user:
        mode_label = "MULTI-USER PARALLEL"
    elif args.parallel:
        mode_label = "PARALLEL"
    else:
        mode_label = "SEQUENTIAL + SMART RETRY"

    log.info("=" * 60)
    log.info("PRODUCTION TEST — %s", mode_label)
    log.info("=" * 60)
    log.info("  Base URL     : %s", base_url)
    log.info("  Keycloak     : %s (realm: %s)", kc_url, kc_realm)
    log.info("  Domain ID    : %s", domain_id)
    log.info("  Mode         : %s", mode_label)
    if args.multiturn or args.multi_user:
        log.info("  Users        : %d", len(users))
        log.info("  Cases (pool) : %d (round-robin)", len(scenarios))
        if args.multiturn:
            total_turns = sum(len(s.turns) for s in scenarios)
            avg_turns = total_turns / len(scenarios) if scenarios else 0
            log.info("  Turns/case   : %.1f avg (%d total in pool)", avg_turns, total_turns)
            log.info("  Turn delay   : %dms (think time between turns)", args.turn_delay_ms)
            arrival_mode = "random within window" if args.random_arrival else "linear"
            log.info("  Arrival      : %s (window: %ds)", arrival_mode, args.stagger_ms * len(users) // 1000)
    else:
        log.info("  Cases        : %d", concurrency)
    log.info("  Timeout      : %ds", args.stream_timeout)
    log.info("  Stagger      : %dms (between launches)", args.stagger_ms)
    if not args.multiturn and not args.multi_user:
        log.info("  Retry empty  : %s (max: %d, wait: %ds)", not args.no_retry_empty, args.max_retries, args.retry_wait)
    log.info("=" * 60)

    # Authenticate + run
    kc = KeycloakClient(kc_url, kc_realm, kc_client_id, kc_client_secret)

    if args.multiturn:
        if not users:
            log.error("No test_users defined in config for multiturn mode")
            sys.exit(1)

        async def _main():
            return await run_multiturn_users(
                users,
                kc,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.stream_timeout,
                stagger_ms=args.stagger_ms,
                turn_delay_ms=args.turn_delay_ms,
                random_arrival=args.random_arrival,
            )

        loop = asyncio.new_event_loop()
        raw_results = loop.run_until_complete(_main())
        mode_str = "multi-user-multiturn"
        config_extra = {
            "users": len(users),
            "cases_pool": len(scenarios),
            "turn_delay_ms": args.turn_delay_ms,
            "random_arrival": args.random_arrival,
        }
    elif args.multi_user and args.distribute:
        if not users:
            log.error("No test_users defined in config for --multi-user --distribute mode")
            sys.exit(1)

        _distributed_partial: list = []

        async def _main():
            return await run_multi_user_distributed(
                users,
                kc,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.stream_timeout,
                stagger_ms=args.stagger_ms,
                collector=_distributed_partial,
            )

        loop = asyncio.new_event_loop()
        mode_str = "multi-user-distributed"
        config_extra = {
            "users": len(users),
            "total_cases": len(scenarios),
            "cases_per_user": math.ceil(len(scenarios) / len(users)) if users else 0,
        }
        try:
            raw_results = loop.run_until_complete(_main())
        except KeyboardInterrupt:
            log.warning(
                "\nInterrupted — saving %d partial result(s) collected so far...",
                len(_distributed_partial),
            )
            raw_results = _distributed_partial
            mode_str += "-partial"
    elif args.multi_user:
        if not users:
            log.error("No test_users defined in config for multi-user mode")
            sys.exit(1)

        async def _main():
            return await run_multi_user(
                users,
                kc,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.stream_timeout,
                stagger_ms=args.stagger_ms,
            )

        loop = asyncio.new_event_loop()
        raw_results = loop.run_until_complete(_main())
        mode_str = "multi-user-parallel"
        config_extra = {"users": len(users), "cases_pool": len(scenarios)}
    else:
        user = users[0] if users else {"email": "user-test@pom.go.id", "password": "12345678"}
        auth_start = time.monotonic()
        try:
            token = kc.get_valid_token(user["email"], user["password"])
        except Exception as exc:
            log.error("Keycloak login failed: %s", exc)
            sys.exit(1)
        auth_latency_ms = (time.monotonic() - auth_start) * 1000
        log.info("Auth OK — %.0fms (sub=%s)", auth_latency_ms, kc.get_account_id(token)[:12])

        async def _main():
            return await run_all(
                token,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.stream_timeout,
                concurrency,
                stagger_ms=args.stagger_ms,
                retry_empty=not args.no_retry_empty,
                max_retries=args.max_retries,
                retry_wait=args.retry_wait,
                parallel=args.parallel,
            )

        loop = asyncio.new_event_loop()
        raw_results = loop.run_until_complete(_main())
        mode_str = "parallel" if args.parallel else "sequential-with-smart-retry"
        config_extra = {
            "cases": concurrency,
            "parallel": args.parallel,
            "retry_empty": not args.no_retry_empty,
            "max_retries": args.max_retries,
            "retry_wait": args.retry_wait,
            "user": user["email"],
        }

    # Compute aggregate
    all_metrics = [r.metrics for r in raw_results]
    aggregate = compute_aggregate(all_metrics)

    result = ConcurrencyResult(
        mode=mode_str,
        config={
            "base_url": base_url,
            "domain_id": domain_id,
            "stream_timeout": args.stream_timeout,
            "stagger_ms": args.stagger_ms,
            **config_extra,
        },
        requests=raw_results,
        aggregate=aggregate,
    )

    print_summary(result)
    path = save_json(result, version=args.version)
    log.info("Output saved: %s", path)
