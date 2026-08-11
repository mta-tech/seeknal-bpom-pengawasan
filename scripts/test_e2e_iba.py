"""
E2E test runner via IBA stack — loads YAML scenarios and runs them through
the full IBA API (Keycloak auth → POST /v6/chat → GET /v6/sse).

Logic ported from test_multiturn_v3.py (direct SDK) but uses HTTP requests
through the IBA application layer, mirroring what a real user experiences.

Usage:
    uv run python scripts/test_e2e_iba.py
    uv run python scripts/test_e2e_iba.py --scenario CB-8
    uv run python scripts/test_e2e_iba.py --path seeknal/tests/v1/singleturn
    uv run python scripts/test_e2e_iba.py --path seeknal/tests/v1/multiturn
    uv run python scripts/test_e2e_iba.py --user admin@acme.com --password admin123
    uv run python scripts/test_e2e_iba.py --base-url http://localhost:6800
    uv run python scripts/test_e2e_iba.py --stream-timeout 600
    uv run python scripts/test_e2e_iba.py --config scripts/iba_test_config.yml
"""

from __future__ import annotations

import argparse
import json
import logging
import os
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
from iba_test_client.metrics import RequestMetrics

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("e2e-iba")


# ---------------------------------------------------------------------------
# Data structures — same as test_multiturn_v3.py
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
class TurnResult:
    turn_num: int
    prompt: str
    answer: str
    elapsed_s: float
    tool_calls: int
    sqls: list[str]
    passed: bool
    failures: list[str]
    note: str = ""
    timed_out: bool = False
    error: str = ""
    metrics: RequestMetrics | None = None


@dataclass
class ScenarioResult:
    name: str
    scenario_id: str
    turns: list[TurnResult]

    @property
    def passed(self) -> bool:
        return all(t.passed for t in self.turns)


# ---------------------------------------------------------------------------
# YAML loader — identical to test_multiturn_v3.py
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


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def _load_config(config_path: Path) -> dict:
    """Load test config from YAML file."""
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_domain_id(config: dict, db_config: dict) -> str:
    """Auto-discover the v6 seeknal domain_id from the database."""
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

    log.error("Could not auto-discover domain_id: no seeknal-local-dev domain found")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Scenario filter — same as test_multiturn_v3.py
# ---------------------------------------------------------------------------


def _filter_scenarios(
    scenarios: list[Scenario], select: str | None
) -> list[Scenario]:
    if not select:
        return scenarios
    select_lower = select.lower()
    filtered = [
        s
        for s in scenarios
        if select_lower in s.name.lower() or select_lower in s.scenario_id.lower()
    ]
    if not filtered:
        log.warning("No scenarios matched filter: '%s'", select)
    return filtered


# ---------------------------------------------------------------------------
# Scenario runner — adapted from test_multiturn_v3.py for IBA API
# ---------------------------------------------------------------------------


def run_scenario(
    scenario: Scenario,
    client: IBAChatClient,
    domain_id: str,
    stream_timeout: int = 300,
    auth_latency_ms: float = 0.0,
) -> ScenarioResult:
    """Run a single scenario through the IBA API.

    Logic mirrors test_multiturn_v3.py.run_scenario() but uses HTTP requests
    instead of direct SDK calls.

    Args:
        scenario: The scenario to run.
        client: Authenticated IBAChatClient.
        domain_id: Target domain UUID.
        stream_timeout: Max seconds per SSE stream.
        auth_latency_ms: Pre-measured auth latency.

    Returns:
        ScenarioResult with per-turn results.
    """
    log.info("=" * 60)
    log.info("SCENARIO [%s] %s", scenario.scenario_id, scenario.name)
    log.info("  %s", scenario.description)
    log.info("  Turns: %d  |  stream_timeout: %ds", len(scenario.turns), stream_timeout)
    log.info("=" * 60)

    turn_results: list[TurnResult] = []
    conversation_id = ""  # shared across turns for multi-turn

    for i, turn in enumerate(scenario.turns, start=1):
        log.info("-" * 50)
        log.info("TURN %d/%d  prompt: %s", i, len(scenario.turns), turn.prompt[:80])
        if turn.note:
            log.info("  note: %s", turn.note)

        start = time.monotonic()
        answer_obj: Answer = client.ask(
            query=turn.prompt,
            domain_id=domain_id,
            conversation_id=conversation_id,
            stream_timeout=stream_timeout,
            auth_latency_ms=auth_latency_ms,
        )
        elapsed = time.monotonic() - start

        # Carry conversation_id forward for multi-turn
        if answer_obj.conversation_id:
            conversation_id = answer_obj.conversation_id

        # Log metrics
        m = answer_obj.metrics
        if m:
            log.info(
                "TURN %d done — %.1fs | tools=%d | sql=%d | status=%d",
                i, elapsed, m.tool_calls, len(m.sqls), m.status_code,
            )
        for j, sql in enumerate(answer_obj.sqls, 1):
            log.info("  SQL %d:\n%s", j, "\n".join(f"    {line}" for line in sql.splitlines()))

        # Assert — same logic as test_multiturn_v3.py
        failures = []
        if answer_obj.error and not answer_obj.timed_out:
            failures.append(f"error: {answer_obj.error}")

        if not answer_obj.timed_out and not answer_obj.error:
            answer_lower = answer_obj.answer.lower()
            for expected in turn.assert_contains:
                if str(expected).lower() not in answer_lower:
                    failures.append(f"missing: '{expected}'")

        if answer_obj.timed_out:
            failures.append("turn timed out")

        passed = not failures
        status = "PASS" if passed else "FAIL"
        log.info("TURN %d %s", i, status)
        for f in failures:
            log.warning("  FAIL: %s", f)
        log.info("  Answer (200c): %s", answer_obj.answer[:200])

        turn_results.append(
            TurnResult(
                turn_num=i,
                prompt=turn.prompt,
                answer=answer_obj.answer,
                elapsed_s=elapsed,
                tool_calls=answer_obj.tool_calls,
                sqls=answer_obj.sqls,
                passed=passed,
                failures=failures,
                note=turn.note,
                timed_out=answer_obj.timed_out,
                error=answer_obj.error or "",
                metrics=answer_obj.metrics,
            )
        )

    return ScenarioResult(
        name=scenario.name,
        scenario_id=scenario.scenario_id,
        turns=turn_results,
    )


# ---------------------------------------------------------------------------
# Summary & Output — same structure as test_multiturn_v3.py
# ---------------------------------------------------------------------------


def print_summary(results: list[ScenarioResult]) -> None:
    print("\n" + "=" * 60)
    print("E2E IBA TEST SUMMARY")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        passed_turns = sum(1 for t in r.turns if t.passed)
        total_time = sum(t.elapsed_s for t in r.turns)
        label = f"[{r.scenario_id}] {r.name}"
        print(
            f"  [{status}] {label:<42s}  {passed_turns}/{len(r.turns)} turns  {total_time:.1f}s"
        )
        for t in r.turns:
            ts = "v" if t.passed else "x"
            timeout_flag = " [TIMEOUT]" if t.timed_out else ""
            error_flag = f" [ERROR: {t.error[:60]}]" if t.error and not t.timed_out else ""
            metrics_info = ""
            if t.metrics:
                metrics_info = f"  total={t.metrics.total_latency_ms:.0f}ms"
            print(
                f"    {ts} Turn {t.turn_num}: {t.elapsed_s:.1f}s"
                f"  tools={t.tool_calls}  sql={len(t.sqls)}"
                f"{timeout_flag}{error_flag}{metrics_info}"
                f"  '{t.prompt[:40]}'"
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


def save_json(
    results: list[ScenarioResult],
    base_url: str,
    select: str | None = None,
    version: str = "e2e-iba",
) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = PROJECT_ROOT / "seeknal" / "tests" / "outputs" / today / version
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = f"e2e_iba_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / filename

    payload = {
        "mode": "e2e-iba",
        "project_path": str(PROJECT_ROOT),
        "base_url": base_url,
        "timestamp": timestamp.isoformat(),
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
                        "answer": t.answer,
                        "passed": t.passed,
                        "timed_out": t.timed_out,
                        "error": t.error,
                        "elapsed_s": round(t.elapsed_s, 2),
                        "tool_calls": t.tool_calls,
                        "sqls": t.sqls,
                        "failures": t.failures,
                        "note": t.note,
                        "metrics": t.metrics.to_dict() if t.metrics else None,
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
            "passed_turns": sum(
                sum(1 for t in r.turns if t.passed) for r in results
            ),
            "failed_turns": sum(
                sum(1 for t in r.turns if not t.passed) for r in results
            ),
        },
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
        description="E2E test runner via IBA stack — YAML scenarios through Keycloak + IBA API"
    )
    parser.add_argument(
        "--scenario",
        help="Run only scenario by name (matches filename stem or scenario_id)",
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
        help="Path to test config YAML (default: scripts/iba_test_config.yml)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="IBA service base URL (overrides config)",
    )
    parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="Keycloak email for authentication (overrides config)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="Keycloak password for authentication (overrides config)",
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
        default=300,
        metavar="SECONDS",
        help="Max seconds to wait for SSE stream per turn (default: 300)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="e2e-iba",
        help="Version label for output path (default: e2e-iba)",
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

    user_email = args.user or (users[0]["email"] if users else "admin@acme.com")
    user_password = args.password or (
        users[0]["password"] if users else "admin123"
    )

    yaml_path = Path(args.path) if args.path else PROJECT_ROOT / "seeknal" / "tests" / "v1"

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

    log.info("Project     : %s", PROJECT_ROOT)
    log.info("IBA URL     : %s", base_url)
    log.info("Keycloak    : %s (realm: %s)", kc_url, kc_realm)
    log.info("User        : %s", user_email)
    log.info("Domain ID   : %s", domain_id)
    log.info("YAML path   : %s", yaml_path)
    log.info("Scenarios   : %d", len(scenarios))
    log.info("Version     : %s", args.version)
    log.info("Stream timeout: %ds", args.stream_timeout)

    # Authenticate
    kc = KeycloakClient(kc_url, kc_realm, kc_client_id, kc_client_secret)
    auth_start = time.monotonic()
    try:
        token = kc.get_valid_token(user_email, user_password)
    except Exception as exc:
        log.error("Keycloak login failed: %s", exc)
        sys.exit(1)
    auth_latency_ms = (time.monotonic() - auth_start) * 1000
    log.info("Auth OK — %.0fms (sub=%s)", auth_latency_ms, kc.get_account_id(token)[:12])

    # Create client
    client = IBAChatClient(token, base_url, service_path)

    # Filter and run
    scenarios = _filter_scenarios(scenarios, args.scenario)
    log.info("Running %d scenario(s)", len(scenarios))

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        result = run_scenario(
            scenario,
            client,
            domain_id,
            stream_timeout=args.stream_timeout,
            auth_latency_ms=auth_latency_ms,
        )
        results.append(result)

    # Output
    print_summary(results)
    path = save_json(results, base_url, select=args.scenario, version=args.version)
    log.info("Output saved: %s", path)
