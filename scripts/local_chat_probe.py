#!/usr/bin/env python3
"""Fire a real chat question at the LOCAL IBA stack and print the answer.

Every URL here is hardcoded to localhost — this script never talks to prod,
unlike `iba_test_client` (used by other scripts, e.g. test_concurrency_production.py,
which CAN point at https://alpha.keycenter.ai). No dependency on that package.

Why this doesn't just read the SSE stream or GET /v1/conversations/.../messages:
as of 2026-07-28, two app-level bugs (not touched by this script — out of scope,
app code is off-limits) mean neither path reliably surfaces the answer locally:
  1. iba-service's SSE relay forwards Redis bytes verbatim; iba-workflows
     publishes events as {"type":..., "data":...} but the relay/frontend expect
     {"event":..., "payload":{...}}. Live browser rendering silently stalls.
  2. iba-service's /v6/internal/persist-event crashes (AttributeError) when the
     event payload is a bare string instead of a dict, so the answer never
     reaches conversation history either.

Both bugs are upstream of the Redis buffer, not in it: the worker still writes
the real, complete answer into Redis correctly. This script reads that buffer
directly (same Redis instance the app uses, read-only) and normalizes the
event shape client-side, bypassing both broken relay layers without touching
any app code.

Usage:
    uv run python scripts/local_chat_probe.py --query "data btp erba tahun 2026"
    uv run python scripts/local_chat_probe.py --query "..." --wait 120
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import redis
import requests

KEYCLOAK_URL = "http://localhost:6808"
KEYCLOAK_REALM = "iba"
KEYCLOAK_CLIENT_ID = "iba-service"
KEYCLOAK_CLIENT_SECRET = "iba-service"
IBA_BASE_URL = "http://localhost:6800/services/iba"
REDIS_URL = "redis://localhost:6637"
DEFAULT_DOMAIN_ID = "ace2c3ec-e668-54a3-b8c2-7b86590ffb6f"


def login(email: str, password: str) -> str:
    resp = requests.post(
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "username": email,
            "password": password,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def dispatch(token: str, query: str, domain_id: str) -> str:
    resp = requests.post(
        f"{IBA_BASE_URL}/v6/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "domain_id": domain_id},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["message_id"]


def normalize(raw: dict) -> dict:
    """iba-workflows' {"type","data","sequence"} -> readable {"event","payload"}."""
    event_type = raw.get("type", "")
    data = raw.get("data")
    payload: dict = {}
    if event_type in ("token", "message", "reasoning"):
        payload["answer"] = data if isinstance(data, str) else (data or {}).get("answer", "")
    elif event_type == "tool_call":
        d = data if isinstance(data, dict) else {}
        payload["tool_name"] = d.get("tool_name", "")
        payload["tool_args"] = d.get("tool_args", {})
    elif event_type == "error":
        payload["error_message"] = data if isinstance(data, str) else str(data)
    elif event_type in ("ask_user", "upload_complete", "visualization"):
        payload["data"] = data
    return {"event": event_type, "payload": payload}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", required=True)
    ap.add_argument("--user", default="admin@acme.com")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--domain-id", default=DEFAULT_DOMAIN_ID)
    ap.add_argument("--wait", type=int, default=90, help="max seconds to wait for a 'done' event")
    args = ap.parse_args()

    print(f"[local-only] keycloak={KEYCLOAK_URL} iba={IBA_BASE_URL} redis={REDIS_URL}")

    token = login(args.user, args.password)
    print(f"login OK ({args.user})")

    message_id = dispatch(token, args.query, args.domain_id)
    print(f"dispatched, message_id={message_id}")

    r = redis.from_url(REDIS_URL, decode_responses=True)

    meta_raw = None
    for _ in range(20):
        meta_raw = r.get(f"sse:meta:{message_id}")
        if meta_raw:
            break
        time.sleep(0.5)
    if not meta_raw:
        print("ERROR: sse:meta never appeared in Redis -- dispatch likely failed upstream", file=sys.stderr)
        sys.exit(1)

    meta = json.loads(meta_raw)
    buffer_key = f"sse:buf:{meta['user_id']}:{meta['domain_id']}:{meta['conversation_id']}:{message_id}"
    print(f"conversation_id={meta['conversation_id']}")
    print(f"watching redis key: {buffer_key}\n")

    seen = 0
    answer = ""
    tool_calls: list[str] = []
    visualizations: list[dict] = []
    deadline = time.monotonic() + args.wait
    done = False

    while time.monotonic() < deadline:
        items = r.lrange(buffer_key, seen, -1)
        for raw_str in items:
            seen += 1
            try:
                raw = json.loads(raw_str)
            except json.JSONDecodeError:
                continue
            ev = normalize(raw)
            etype = ev["event"]
            payload = ev["payload"]
            if etype == "token":
                answer += payload.get("answer", "")
            elif etype == "message":
                answer = payload.get("answer", answer)
            elif etype == "tool_call":
                tool_calls.append(payload.get("tool_name", ""))
                print(f"  [tool_call] {payload.get('tool_name', '')}")
            elif etype == "visualization":
                visualizations.append(payload.get("data"))
                print("  [visualization] chart payload received")
            elif etype == "error":
                print(f"  [error] {payload.get('error_message', '')}")
            elif etype == "done":
                done = True
        if done:
            break
        time.sleep(1.5)

    print("\n" + "=" * 70)
    if not done:
        print(f"TIMEOUT after {args.wait}s -- worker may still be running, or crashed. Check:")
        print("  docker logs seeknal-worker-m9")
        print(f"  redis-cli -h localhost -p 6637 LRANGE {buffer_key} 0 -1")
    print(f"tool_calls: {tool_calls}")
    print(f"visualizations: {len(visualizations)}")
    print("-" * 70)
    print(answer if answer else "(no answer text captured)")
    print("=" * 70)


if __name__ == "__main__":
    main()
