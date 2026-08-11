"""
Concurrency test runner — test IBA system under simultaneous user load.

Supports multiple modes for testing different concurrency patterns:
- same-user:  1 user sends N parallel questions
- multi-user: N different users each send 1 question in parallel
- burst:      N users each run a full multi-turn scenario concurrently
- sustained:  N users send requests continuously for T seconds

Usage:
    uv run python scripts/test_concurrency.py --mode same-user --concurrency 5
    uv run python scripts/test_concurrency.py --mode multi-user --users 5
    uv run python scripts/test_concurrency.py --mode burst --users 3 --turns 3
    uv run python scripts/test_concurrency.py --mode sustained --users 5 --duration 60
    uv run python scripts/test_concurrency.py --mode multi-user --users 5 --scenario CB-8
    uv run python scripts/test_concurrency.py --mode burst --users 3 --path seeknal/tests/v1/singleturn
    uv run python scripts/test_concurrency.py --mode same-user --concurrency 10 --prompt "berapa NIE 2023?"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("concurrency-test")


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
    turns: list[Turn]
    description: str = ""
    scenario_id: str = ""


@dataclass
class RequestResult:
    user_id: str
    turn_num: int
    prompt: str
    answer: str
    passed: bool
    failures: list[str]
    metrics: RequestMetrics
    conversation_id: str = ""


@dataclass
class ConcurrencyResult:
    mode: str
    config: dict
    requests: list[RequestResult]
    aggregate: dict


# ---------------------------------------------------------------------------
# YAML loader — same as test_multiturn_v3.py and test_e2e_iba.py
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
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_domain_id(config: dict, db_config: dict) -> str:
    import psycopg

    dsn = (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        f"?sslmode=disable"
    )
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM domains WHERE agent_id = 'seeknal-local-dev' LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                return row[0]
    log.error("Could not auto-discover domain_id")
    sys.exit(1)


def _filter_scenarios(
    scenarios: list[Scenario], select: str | None
) -> list[Scenario]:
    if not select:
        return scenarios
    select_lower = select.lower()
    return [
        s
        for s in scenarios
        if select_lower in s.name.lower() or select_lower in s.scenario_id.lower()
    ]


# ---------------------------------------------------------------------------
# Async workers
# ---------------------------------------------------------------------------


def _make_sync_client(token: str, base_url: str, service_path: str) -> IBAChatClient:
    return IBAChatClient(token, base_url, service_path)


async def _run_single_turn(
    client: IBAChatClient,
    prompt: str,
    domain_id: str,
    conversation_id: str,
    stream_timeout: int,
    assert_contains: list[str],
    user_id: str,
    turn_num: int,
) -> RequestResult:
    """Run a single turn in a thread pool (sync → async wrapper)."""
    loop = asyncio.get_event_loop()

    def _do_turn() -> tuple[Answer, list[str]]:
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
        return answer, failures

    answer, failures = await loop.run_in_executor(None, _do_turn)

    return RequestResult(
        user_id=user_id,
        turn_num=turn_num,
        prompt=prompt,
        answer=answer.answer,
        passed=not failures,
        failures=failures,
        metrics=answer.metrics or RequestMetrics(),
        conversation_id=answer.conversation_id,
    )


async def _run_scenario_for_user(
    token: str,
    base_url: str,
    service_path: str,
    domain_id: str,
    scenario: Scenario,
    stream_timeout: int,
    user_id: str,
) -> list[RequestResult]:
    """Run a full scenario for one user (sequential turns, like test_multiturn_v3)."""
    client = _make_sync_client(token, base_url, service_path)
    results = []
    conversation_id = ""

    for i, turn in enumerate(scenario.turns, start=1):
        result = await _run_single_turn(
            client,
            turn.prompt,
            domain_id,
            conversation_id,
            stream_timeout,
            turn.assert_contains,
            user_id,
            i,
        )
        if result.conversation_id:
            conversation_id = result.conversation_id
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Mode: same-user — 1 user, N parallel questions
# ---------------------------------------------------------------------------


async def _mode_same_user(
    token: str,
    base_url: str,
    service_path: str,
    domain_id: str,
    concurrency: int,
    prompt: str,
    scenarios: list[Scenario],
    stream_timeout: int,
) -> list[RequestResult]:
    """Send N identical questions from the same user simultaneously."""
    client = _make_sync_client(token, base_url, service_path)

    # Use provided prompt, or take first turn from first scenario
    if not prompt and scenarios:
        prompt = scenarios[0].turns[0].prompt
    if not prompt:
        log.error("No prompt provided and no scenarios loaded")
        return []

    log.info("Same-user mode: %d parallel requests with prompt: %s", concurrency, prompt[:60])

    tasks = [
        _run_single_turn(
            client, prompt, domain_id, "", stream_timeout, [], f"user-0-q{i}", 1
        )
        for i in range(concurrency)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, RequestResult)]


# ---------------------------------------------------------------------------
# Mode: multi-user — N users, 1 question each (parallel)
# ---------------------------------------------------------------------------


async def _mode_multi_user(
    tokens: list[str],
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list[Scenario],
    stream_timeout: int,
) -> list[RequestResult]:
    """N different users each send their first question simultaneously."""
    if not scenarios:
        log.error("No scenarios loaded")
        return []

    log.info("Multi-user mode: %d users, 1 question each", len(tokens))

    tasks = []
    for i, token in enumerate(tokens):
        scenario = scenarios[i % len(scenarios)]
        prompt = scenario.turns[0].prompt
        assert_contains = scenario.turns[0].assert_contains
        tasks.append(
            _run_single_turn(
                _make_sync_client(token, base_url, service_path),
                prompt,
                domain_id,
                "",
                stream_timeout,
                assert_contains,
                f"user-{i}",
                1,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, RequestResult)]


# ---------------------------------------------------------------------------
# Mode: burst — N users each run a multi-turn scenario concurrently
# ---------------------------------------------------------------------------


async def _mode_burst(
    tokens: list[str],
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list[Scenario],
    turns_per_user: int,
    stream_timeout: int,
) -> list[RequestResult]:
    """N users each run a multi-turn scenario in parallel.

    Within each user, turns are sequential (to test conversation continuity).
    Across users, everything is parallel.
    """
    if not scenarios:
        log.error("No scenarios loaded")
        return []

    log.info(
        "Burst mode: %d users, %d turns each",
        len(tokens),
        turns_per_user,
    )

    tasks = []
    for i, token in enumerate(tokens):
        scenario = scenarios[i % len(scenarios)]
        # Limit turns to turns_per_user or scenario's actual turns
        limited_turns = scenario.turns[:turns_per_user]
        limited_scenario = Scenario(
            name=scenario.name,
            scenario_id=scenario.scenario_id,
            description=scenario.description,
            turns=limited_turns,
        )
        tasks.append(
            _run_scenario_for_user(
                token,
                base_url,
                service_path,
                domain_id,
                limited_scenario,
                stream_timeout,
                f"user-{i}",
            )
        )

    nested_results = await asyncio.gather(*tasks, return_exceptions=True)
    flat = []
    for r in nested_results:
        if isinstance(r, list):
            flat.extend(r)
    return flat


# ---------------------------------------------------------------------------
# Mode: sustained — N users send requests continuously for T seconds
# ---------------------------------------------------------------------------


async def _mode_sustained(
    tokens: list[str],
    base_url: str,
    service_path: str,
    domain_id: str,
    scenarios: list[Scenario],
    duration: int,
    stream_timeout: int,
) -> list[RequestResult]:
    """N users send requests continuously for `duration` seconds.

    Each user loops through available scenarios, sending one question at a time,
    waiting for the response before sending the next.
    """
    if not scenarios:
        log.error("No scenarios loaded")
        return []

    log.info(
        "Sustained mode: %d users, %ds duration",
        len(tokens),
        duration,
    )

    all_results: list[RequestResult] = []
    deadline = time.monotonic() + duration

    async def _user_loop(token: str, user_idx: int):
        client = _make_sync_client(token, base_url, service_path)
        turn_counter = 0
        while time.monotonic() < deadline:
            scenario = scenarios[turn_counter % len(scenarios)]
            prompt = scenario.turns[0].prompt
            assert_contains = scenario.turns[0].assert_contains
            result = await _run_single_turn(
                client,
                prompt,
                domain_id,
                "",
                stream_timeout,
                assert_contains,
                f"user-{user_idx}",
                turn_counter + 1,
            )
            all_results.append(result)
            turn_counter += 1

    tasks = [_user_loop(token, i) for i, token in enumerate(tokens)]
    await asyncio.gather(*tasks, return_exceptions=True)

    return all_results


# ---------------------------------------------------------------------------
# Summary & Output
# ---------------------------------------------------------------------------


def print_summary(result: ConcurrencyResult) -> None:
    print("\n" + "=" * 60)
    print("CONCURRENCY TEST SUMMARY")
    print("=" * 60)
    print(f"  Mode     : {result.mode}")
    print(f"  Config   : {json.dumps(result.config)}")
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

    # Per-request details
    passed = sum(1 for r in result.requests if r.passed)
    failed = len(result.requests) - passed
    print(f"  Assertions     : {passed}/{len(result.requests)} passed")
    if failed:
        print()
        for r in result.requests:
            if not r.passed:
                print(
                    f"    FAIL [{r.user_id}] T{r.turn_num}: "
                    f"{r.failures}  '{r.prompt[:50]}'"
                )

    print("=" * 60)


def save_json(result: ConcurrencyResult, version: str = "concurrency") -> Path:
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
                "user_id": r.user_id,
                "turn": r.turn_num,
                "prompt": r.prompt,
                "answer": r.answer[:500],
                "passed": r.passed,
                "failures": r.failures,
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
        description="Concurrency test runner — test IBA under simultaneous user load"
    )
    parser.add_argument(
        "--mode",
        choices=["same-user", "multi-user", "burst", "sustained"],
        required=True,
        help="Concurrency test mode",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of parallel requests (same-user mode, default: 5)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=5,
        help="Number of simulated users (multi-user/burst/sustained, default: 5)",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Turns per user in burst mode (default: 3)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds for sustained mode (default: 60)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="",
        help="Custom prompt for same-user mode",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Filter scenarios by name/id",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to YAML test directory (default: seeknal/tests/v1)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="scripts/iba_test_config.yml",
        help="Path to test config YAML",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="IBA service base URL (overrides config)",
    )
    parser.add_argument(
        "--domain-id",
        type=str,
        default=None,
        help="Domain UUID (overrides auto-discovery)",
    )
    parser.add_argument(
        "--stream-timeout",
        type=int,
        default=900,
        help="Max seconds of inactivity per SSE stream (default: 900). "
             "Heartbeats reset this timer, so the stream stays alive while "
             "the worker processes queued requests.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="concurrency",
        help="Version label for output path",
    )
    args = parser.parse_args()

    # Load config
    config_path = PROJECT_ROOT / args.config
    config = _load_config(config_path)

    iba_config = config.get("iba", {})
    kc_config = config.get("keycloak", {})
    db_config = config.get("database", {})
    users = config.get("test_users", [])

    base_url = args.base_url or iba_config.get("base_url", "http://localhost:6800")
    service_path = iba_config.get("service_path", "/services/iba")
    kc_url = kc_config.get("url", "http://localhost:6808")
    kc_realm = kc_config.get("realm", "iba")
    kc_client_id = kc_config.get("client_id", "iba-service")
    kc_client_secret = kc_config.get("client_secret", "iba-service")

    yaml_path = (
        Path(args.path) if args.path else PROJECT_ROOT / "seeknal" / "tests" / "v1"
    )

    # Resolve domain_id
    if args.domain_id:
        domain_id = args.domain_id
    elif config.get("domain_id", "auto") != "auto":
        domain_id = config["domain_id"]
    elif db_config:
        domain_id = _get_domain_id(config, db_config)
    else:
        log.error("No domain_id provided and no DB config for auto-discovery")
        sys.exit(1)

    # Load scenarios
    scenarios = _load_yaml_tests(yaml_path)
    if args.scenario:
        scenarios = _filter_scenarios(scenarios, args.scenario)

    log.info("Mode        : %s", args.mode)
    log.info("IBA URL     : %s", base_url)
    log.info("Domain ID   : %s", domain_id)
    log.info("Scenarios   : %d", len(scenarios))

    # Authenticate
    kc = KeycloakClient(kc_url, kc_realm, kc_client_id, kc_client_secret)

    # For multi-user/burst/sustained, we need multiple user accounts.
    # If only 1 user in config, replicate the same token N times.
    num_users = {
        "same-user": 1,
        "multi-user": args.users,
        "burst": args.users,
        "sustained": args.users,
    }[args.mode]

    tokens = []
    for i in range(num_users):
        user = users[i % len(users)] if users else {"email": "admin@acme.com", "password": "admin123"}
        try:
            token = kc.get_valid_token(user["email"], user["password"])
            tokens.append(token)
        except Exception as exc:
            log.error("Login failed for user %s: %s", user["email"], exc)
            sys.exit(1)

    log.info("Authenticated: %d user(s)", len(tokens))

    # Run
    async def _main():
        if args.mode == "same-user":
            raw = await _mode_same_user(
                tokens[0],
                base_url,
                service_path,
                domain_id,
                args.concurrency,
                args.prompt,
                scenarios,
                args.stream_timeout,
            )
        elif args.mode == "multi-user":
            raw = await _mode_multi_user(
                tokens,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.stream_timeout,
            )
        elif args.mode == "burst":
            raw = await _mode_burst(
                tokens,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.turns,
                args.stream_timeout,
            )
        elif args.mode == "sustained":
            raw = await _mode_sustained(
                tokens,
                base_url,
                service_path,
                domain_id,
                scenarios,
                args.duration,
                args.stream_timeout,
            )
        else:
            raw = []

        return raw

    loop = asyncio.new_event_loop()
    raw_results = loop.run_until_complete(_main())

    all_metrics = [r.metrics for r in raw_results]
    aggregate = compute_aggregate(all_metrics)

    result = ConcurrencyResult(
        mode=args.mode,
        config={
            "concurrency": args.concurrency,
            "users": args.users,
            "turns": args.turns,
            "duration": args.duration,
            "prompt": args.prompt,
            "stream_timeout": args.stream_timeout,
        },
        requests=raw_results,
        aggregate=aggregate,
    )

    print_summary(result)
    path = save_json(result, version=args.version)
    log.info("Output saved: %s", path)
