"""
Custom E2E test — capture ALL events (SSE, tool calls, SQLs).
Based on test_e2e_iba.py but with detailed event logging.

Usage:
    uv run python scripts/test_capture_events.py
    uv run python scripts/test_capture_events.py --question "Berapa total ERBA?"
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

import requests
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from iba_test_client.auth import KeycloakClient
from iba_test_client.chat import IBAChatClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("capture-events")


@dataclass
class CapturedEvent:
    """Single SSE event captured."""
    event_type: str
    payload: dict
    timestamp: float


@dataclass
class ToolCallInfo:
    """Captured tool call details."""
    tool_name: str
    tool_args: dict
    sql: str = ""
    timestamp: float = 0.0


@dataclass
class TestResult:
    """Complete test result with all captured events."""
    question: str
    answer: str = ""
    events: list[CapturedEvent] = field(default_factory=list)
    tool_calls: list[ToolCallInfo] = field(default_factory=list)
    sqls: list[str] = field(default_factory=list)
    error: str = ""
    timed_out: bool = False
    elapsed_s: float = 0.0


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_domain_id(config: dict, db_config: dict) -> str:
    """Auto-discover domain_id from database."""
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


def capture_events_from_stream(
    client: IBAChatClient,
    message_id: str,
    sse_token: str,
    timeout: int = 300,
) -> tuple[list[CapturedEvent], list[ToolCallInfo], list[str], str, bool]:
    """Stream SSE and capture ALL events with details."""
    url = client._api_url(f"/v6/sse?message_id={message_id}&sse_token={sse_token}")
    headers = {
        "Authorization": f"Bearer {client.token}",
        "Accept": "text/event-stream",
    }

    events: list[CapturedEvent] = []
    tool_calls: list[ToolCallInfo] = []
    sqls: list[str] = []
    answer = ""
    error = ""
    timed_out = False
    deadline = time.monotonic() + timeout

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=timeout + 60)
        r.raise_for_status()

        for line in r.iter_lines(decode_unicode=True):
            if time.monotonic() > deadline:
                timed_out = True
                break

            if not line or not line.startswith("data: "):
                continue

            try:
                event_data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            event_type = event_data.get("event", "")
            payload = event_data.get("payload", {})
            ts = time.monotonic()

            # Reset deadline on ANY event
            deadline = time.monotonic() + timeout

            # Capture event
            events.append(CapturedEvent(
                event_type=event_type,
                payload=payload,
                timestamp=ts,
            ))

            # Log event details
            if event_type == "token":
                answer += payload.get("answer", "")
                log.info("  [SSE] token: %s", payload.get("answer", "")[:50])
            elif event_type == "reasoning":
                log.info("  [SSE] reasoning: %s", payload.get("answer", "")[:80])
            elif event_type == "tool_call":
                tool_name = payload.get("tool_name", "")
                tool_args = payload.get("tool_args", {})
                sql = tool_args.get("sql", "") if isinstance(tool_args, dict) else ""
                tool_calls.append(ToolCallInfo(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    sql=sql,
                    timestamp=ts,
                ))
                if sql:
                    sqls.append(sql)
                log.info("  [SSE] tool_call: %s", tool_name)
                if sql:
                    log.info("    SQL: %s", sql[:100])
            elif event_type == "tool_result":
                result_preview = str(payload.get("result", ""))[:100]
                log.info("  [SSE] tool_result: %s", result_preview)
            elif event_type == "message":
                answer = payload.get("answer", answer)
                log.info("  [SSE] message: %s", payload.get("answer", "")[:80])
            elif event_type == "done":
                log.info("  [SSE] done")
                break
            elif event_type == "error":
                error = payload.get("error_message", "unknown")
                log.warning("  [SSE] error: %s", error)
            elif event_type == "heartbeat":
                log.debug("  [SSE] heartbeat")
            else:
                log.info("  [SSE] %s: %s", event_type, str(payload)[:80])

    except requests.exceptions.Timeout:
        timed_out = True
        error = f"SSE timeout after {timeout}s"
    except Exception as exc:
        error = f"SSE error: {type(exc).__name__}: {exc}"

    return events, tool_calls, sqls, answer, timed_out


def run_question(
    question: str,
    client: IBAChatClient,
    domain_id: str,
    stream_timeout: int = 300,
) -> TestResult:
    """Run a single question and capture all events."""
    log.info("=" * 70)
    log.info("QUESTION: %s", question)
    log.info("=" * 70)

    start = time.monotonic()
    result = TestResult(question=question)

    # Phase 1: Initiate chat
    log.info("Phase 1: POST /v6/chat")
    chat_resp = client.send_message(question, domain_id)
    if chat_resp.error:
        result.error = chat_resp.error
        result.elapsed_s = time.monotonic() - start
        log.error("Chat initiation failed: %s", chat_resp.error)
        return result

    log.info("  message_id: %s", chat_resp.message_id)
    log.info("  sse_token: %s", chat_resp.sse_token[:20] + "...")

    # Phase 2: Stream SSE
    log.info("Phase 2: GET /v6/sse (streaming)")
    events, tool_calls, sqls, answer, timed_out = capture_events_from_stream(
        client, chat_resp.message_id, chat_resp.sse_token, timeout=stream_timeout
    )

    result.events = events
    result.tool_calls = tool_calls
    result.sqls = sqls
    result.answer = answer
    result.timed_out = timed_out
    result.elapsed_s = time.monotonic() - start

    # Summary
    log.info("-" * 70)
    log.info("RESULT SUMMARY:")
    log.info("  Total events: %d", len(events))
    log.info("  Tool calls: %d", len(tool_calls))
    log.info("  SQLs: %d", len(sqls))
    log.info("  Timed out: %s", timed_out)
    log.info("  Elapsed: %.1fs", result.elapsed_s)
    log.info("  Answer (200c): %s", answer[:200])

    if tool_calls:
        log.info("  TOOL CALLS DETAIL:")
        for i, tc in enumerate(tool_calls, 1):
            log.info("    %d. %s", i, tc.tool_name)
            if tc.sql:
                log.info("       SQL: %s", tc.sql[:120])

    return result


def print_full_report(results: list[TestResult]):
    """Print comprehensive report of all captured events."""
    print("\n" + "=" * 80)
    print("FULL EVENT CAPTURE REPORT")
    print("=" * 80)

    for r in results:
        print(f"\n{'='*70}")
        print(f"QUESTION: {r.question}")
        print(f"{'='*70}")
        print(f"Elapsed: {r.elapsed_s:.1f}s")
        print(f"Answer: {r.answer[:300]}")
        print(f"\n--- SSE EVENTS ({len(r.events)}) ---")
        for i, evt in enumerate(r.events, 1):
            preview = str(evt.payload)[:80] if evt.payload else ""
            print(f"  {i:3d}. [{evt.event_type}] {preview}")

        print(f"\n--- TOOL CALLS ({len(r.tool_calls)}) ---")
        for i, tc in enumerate(r.tool_calls, 1):
            print(f"  {i}. {tc.tool_name}")
            if tc.sql:
                print(f"     SQL: {tc.sql[:150]}")

        print(f"\n--- SQLs ({len(r.sqls)}) ---")
        for i, sql in enumerate(r.sqls, 1):
            print(f"  {i}. {sql[:150]}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    total_events = sum(len(r.events) for r in results)
    total_tools = sum(len(r.tool_calls) for r in results)
    total_sqls = sum(len(r.sqls) for r in results)
    print(f"  Questions: {len(results)}")
    print(f"  Total SSE events: {total_events}")
    print(f"  Total tool calls: {total_tools}")
    print(f"  Total SQLs: {total_sqls}")

    # Tool type breakdown
    tool_types: dict[str, int] = {}
    for r in results:
        for tc in r.tool_calls:
            tool_types[tc.tool_name] = tool_types.get(tc.tool_name, 0) + 1
    if tool_types:
        print(f"\n  TOOL TYPE BREAKDOWN:")
        for name, count in sorted(tool_types.items()):
            print(f"    {name}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture ALL SSE events from IBA")
    parser.add_argument("--question", type=str, help="Single question to ask")
    parser.add_argument("--config", type=str, default="scripts/iba_test_config.yml")
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--user", type=str, default=None)
    parser.add_argument("--password", type=str, default=None)
    parser.add_argument("--domain-id", type=str, default=None)
    parser.add_argument("--stream-timeout", type=int, default=300)
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
    user_password = args.password or (users[0]["password"] if users else "admin123")

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

    # Authenticate
    log.info("Authenticating with Keycloak...")
    kc = KeycloakClient(kc_url, kc_realm, kc_client_id, kc_client_secret)
    try:
        token = kc.get_valid_token(user_email, user_password)
        log.info("Auth OK")
    except Exception as exc:
        log.error("Keycloak login failed: %s", exc)
        sys.exit(1)

    client = IBAChatClient(token, base_url, service_path)

    # Questions to test
    questions = [
        args.question if args.question else "Berapa total produk ERBA yang terdaftar?",
    ]

    results = []
    for q in questions:
        result = run_question(q, client, domain_id, stream_timeout=args.stream_timeout)
        results.append(result)

    print_full_report(results)
