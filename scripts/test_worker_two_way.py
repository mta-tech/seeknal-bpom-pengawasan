"""Interactive two-way WebSocket demo for gateway ask_user (SEEK4 Phase 4).

Usage:
    uv run python scripts/test_worker_two_way.py [--url WS_URL] [--session-id ID]

The script connects to the gateway WebSocket, lets you type questions, and
handles ask_user events by showing a numbered menu and accepting your input.

Press Ctrl+C to exit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

try:
    import websockets  # type: ignore
except ImportError:
    print("Install websockets: uv add websockets")
    sys.exit(1)


DEFAULT_URL = "ws://localhost:8000/ws"


async def send_message(ws, payload: dict) -> None:
    await ws.send(json.dumps(payload))


async def handle_ask_user(ws, event: dict) -> None:
    """Print numbered options and send back the user's choice."""
    question = event.get("question", "")
    options = event.get("options", [])
    prompt_id = event.get("prompt_id", "")
    session_id = event.get("session_id", "")

    print(f"\n[CLARIFIKASI] {question}")
    for i, opt in enumerate(options, 1):
        label = opt.get("label", f"Option {i}")
        desc = opt.get("description", "")
        rec = " ← recommended" if str(opt.get("recommended", "")).lower() == "true" else ""
        print(f"  {i}. {label} — {desc}{rec}")

    # Accept free text too
    print("  (enter number to select, or type your own answer)")
    try:
        raw = await asyncio.get_event_loop().run_in_executor(None, lambda: input("> ").strip())
    except (EOFError, KeyboardInterrupt):
        raw = "1"

    # Resolve numbered choice
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            answer = options[idx]["label"]
            answer_type = "select"
        else:
            answer = raw
            answer_type = "free_text"
    except ValueError:
        answer = raw
        answer_type = "free_text"

    response = {
        "type": "ask_user_response",
        "prompt_id": prompt_id,
        "session_id": session_id,
        "answer": answer,
        "answer_type": answer_type,
    }
    await send_message(ws, response)
    print(f"[TERKIRIM] {answer!r}")


async def input_loop(ws, session_id: str) -> None:
    """Read questions from stdin and send to gateway."""
    print(f"Sesi: {session_id}  |  Ketik pertanyaan (Ctrl+C untuk keluar)\n")
    loop = asyncio.get_event_loop()
    while True:
        try:
            question = await loop.run_in_executor(None, lambda: input("Kamu: ").strip())
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        await send_message(ws, {
            "type": "ask",
            "session_id": session_id,
            "message": question,
        })


async def receive_loop(ws, session_id: str) -> None:
    """Handle incoming events from gateway."""
    async for raw in ws:
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[RAW] {raw}")
            continue

        etype = event.get("type", "")

        if etype == "ask_user":
            await handle_ask_user(ws, event)

        elif etype in ("stream", "text_delta"):
            chunk = event.get("content") or event.get("delta") or ""
            print(chunk, end="", flush=True)

        elif etype == "stream_end":
            print()  # newline after stream completes

        elif etype == "answer":
            content = event.get("content", "")
            print(f"\n[JAWABAN]\n{content}\n")

        elif etype == "error":
            print(f"\n[ERROR] {event.get('message', event)}\n")

        elif etype == "report_ready":
            print(f"\n[LAPORAN] {event.get('url', '(siap)')}\n")

        else:
            # Show unknown event types for debugging
            print(f"\n[EVENT:{etype}] {json.dumps(event, ensure_ascii=False)[:200]}\n")


async def main(url: str, session_id: str) -> None:
    print(f"Menghubungkan ke {url} ...")
    async with websockets.connect(url) as ws:
        print("Terhubung.\n")
        # Run send and receive concurrently
        await asyncio.gather(
            receive_loop(ws, session_id),
            input_loop(ws, session_id),
            return_exceptions=True,
        )


def _parse_args() -> argparse.Namespace:
    import uuid
    p = argparse.ArgumentParser(description="SEEK4 two-way ask_user demo client")
    p.add_argument("--url", default=DEFAULT_URL, help="Gateway WebSocket URL")
    p.add_argument("--session-id", default=uuid.uuid4().hex[:8], help="Session ID")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        asyncio.run(main(args.url, args.session_id))
    except KeyboardInterrupt:
        print("\nKeluar.")
