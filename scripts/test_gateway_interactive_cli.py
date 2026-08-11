"""Interactive gateway CLI for realistic multi-turn + clarification testing.

This script behaves closer to the website chat than static YAML/UAT scripts:
it keeps one session alive, listens to SSE events continuously, sends each user
message through ``POST /ask``, and if the agent emits an ``ask_user`` /
clarification event it pauses and asks the operator for the follow-up answer in
the same terminal.

Current clarification model:
    - The gateway emits ``ask_user`` and ends the current turn.
    - The operator's clarification answer is sent back as the NEXT user turn in
      the same session.
    - This matches the current ``request_clarification`` flow used by the
      gateway/headless runtime.

Usage:
    python3 scripts/test_gateway_interactive_cli.py
    python3 scripts/test_gateway_interactive_cli.py --base-url http://127.0.0.1:8000
    python3 scripts/test_gateway_interactive_cli.py --session-id demo-clarify-1
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class PendingClarification:
    prompts: list[dict[str, Any]]


class InteractiveGatewayCLI:
    def __init__(
        self,
        base_url: str,
        session_id: str,
        tenant_id: str | None = None,
        connect_timeout: float = 10.0,
        read_timeout: float = 900.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.http = requests.Session()
        self.print_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.sse_ready = threading.Event()
        self.pending_clarifications: queue.Queue[PendingClarification] = queue.Queue()
        self._token_open = False
        self._turn_has_terminal_output = False

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id
        return headers

    def _sse_headers(self) -> dict[str, str]:
        headers = {"Accept": "text/event-stream"}
        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id
        return headers

    def _println(self, text: str = "") -> None:
        with self.print_lock:
            print(text, flush=True)

    def _print_token(self, text: str) -> None:
        with self.print_lock:
            print(text, end="", flush=True)

    def _reset_turn_state(self) -> None:
        self._token_open = False
        self._turn_has_terminal_output = False

    def _close_token_line_if_needed(self) -> None:
        if self._token_open:
            self._println()
            self._token_open = False

    def _handle_sse_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type", "")
        data = event.get("data")

        if event_type == "keepalive":
            return

        if event_type == "started":
            self._println("\n[started]")
            return

        if event_type == "queued":
            pos = "?"
            if isinstance(data, dict):
                pos = str(data.get("position", "?"))
            self._println(f"\n[queued] position={pos}")
            return

        if event_type == "token":
            if not self._token_open:
                self._println("\nAssistant:")
                self._token_open = True
            self._print_token(str(data or ""))
            return

        if event_type == "reasoning":
            self._close_token_line_if_needed()
            if data:
                self._println(f"[reasoning] {str(data).strip()}")
            return

        if event_type == "tool_start":
            self._close_token_line_if_needed()
            payload = data or {}
            if isinstance(payload, dict):
                name = payload.get("name", "tool")
                args = payload.get("args", {})
                self._println(f"[tool:start] {name} {json.dumps(args, ensure_ascii=False)[:240]}")
            return

        if event_type == "tool_end":
            self._close_token_line_if_needed()
            payload = data or {}
            if isinstance(payload, dict):
                name = payload.get("name", "tool")
                elapsed_ms = payload.get("elapsed_ms", "")
                suffix = f" ({elapsed_ms} ms)" if elapsed_ms != "" else ""
                self._println(f"[tool:end] {name}{suffix}")
            return

        if event_type == "ask_user":
            self._close_token_line_if_needed()
            prompts = []
            if isinstance(data, dict):
                prompts = data.get("prompts", []) or []
            self.pending_clarifications.put(PendingClarification(prompts=prompts))
            self._println("[clarification requested]")
            return

        if event_type == "answer":
            self._close_token_line_if_needed()
            answer = str(data or "").strip()
            if answer:
                self._println("\n[final answer]")
                self._println(answer)
                self._turn_has_terminal_output = True
            return

        if event_type == "error":
            self._close_token_line_if_needed()
            self._println(f"\n[error] {data}")
            self._turn_has_terminal_output = True
            return

        if event_type == "done":
            self._close_token_line_if_needed()
            self._println("\n[done]")
            self._turn_has_terminal_output = True
            return

        self._close_token_line_if_needed()
        self._println(f"[event:{event_type}] {json.dumps(event, ensure_ascii=False)[:500]}")

    def _sse_loop(self) -> None:
        url = f"{self.base_url}/events/{self.session_id}"
        while not self.stop_event.is_set():
            try:
                with self.http.get(
                    url,
                    headers=self._sse_headers(),
                    stream=True,
                    timeout=(self.connect_timeout, self.read_timeout),
                ) as resp:
                    resp.raise_for_status()
                    self.sse_ready.set()
                    for raw_line in resp.iter_lines(decode_unicode=True):
                        if self.stop_event.is_set():
                            return
                        if not raw_line or not raw_line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(raw_line[6:])
                        except json.JSONDecodeError:
                            continue
                        self._handle_sse_event(event)
            except requests.RequestException as exc:
                self._println(f"[sse] reconnecting after error: {exc}")
                time.sleep(1.0)

    def _start_sse(self) -> threading.Thread:
        thread = threading.Thread(target=self._sse_loop, name="seeknal-sse", daemon=True)
        thread.start()
        if not self.sse_ready.wait(timeout=5):
            self._println("[warn] SSE connection not confirmed yet; continuing anyway.")
        return thread

    def _post_question(self, question: str) -> dict[str, Any]:
        body = {
            "question": question,
            "session_id": self.session_id,
        }
        resp = self.http.post(
            f"{self.base_url}/ask",
            headers=self._headers(),
            json=body,
            timeout=(self.connect_timeout, self.read_timeout),
        )
        resp.raise_for_status()
        return resp.json()

    def _collect_pending_clarification(self) -> PendingClarification | None:
        latest: PendingClarification | None = None
        while True:
            try:
                latest = self.pending_clarifications.get_nowait()
            except queue.Empty:
                return latest

    def _prompt_single_slot(self, prompt: dict[str, Any], index: int) -> str:
        question = str(prompt.get("question", "")).strip() or f"Clarification #{index}"
        options = prompt.get("options", []) or []

        self._println()
        self._println(f"[clarification {index}] {question}")
        for i, option in enumerate(options, 1):
            label = str(option.get("label", f"Option {i}"))
            description = str(option.get("description", "")).strip()
            recommended = str(option.get("recommended", "")).lower() == "true"
            suffix = " [recommended]" if recommended else ""
            if description:
                self._println(f"  {i}. {label} - {description}{suffix}")
            else:
                self._println(f"  {i}. {label}{suffix}")
        self._println("  Type a number or write your own answer.")

        while True:
            raw = input("clarify> ").strip()
            if not raw:
                continue
            try:
                choice = int(raw)
            except ValueError:
                return raw
            idx = choice - 1
            if 0 <= idx < len(options):
                return str(options[idx].get("label", raw))
            self._println("Invalid option number.")

    def _prompt_clarification(self, pending: PendingClarification) -> str:
        if not pending.prompts:
            return input("clarify> ").strip()

        answers: list[str] = []
        for i, prompt in enumerate(pending.prompts, 1):
            answer = self._prompt_single_slot(prompt, i)
            if answer:
                answers.append(answer)

        if len(answers) == 1:
            return answers[0]
        return "My clarification answers: " + "; ".join(answers)

    def _run_single_turn(self, question: str) -> None:
        current_question = question
        while current_question:
            self._reset_turn_state()
            self._println()
            self._println(f"You: {current_question}")
            try:
                result = self._post_question(current_question)
            except requests.RequestException as exc:
                self._println(f"[request failed] {exc}")
                return

            pending = self._collect_pending_clarification()
            if pending is not None:
                current_question = self._prompt_clarification(pending)
                continue

            answer = str(result.get("answer", "")).strip()
            if answer and not self._turn_has_terminal_output:
                self._println("\n[final answer]")
                self._println(answer)
            break

    def run(self) -> None:
        sse_thread = self._start_sse()
        self._println("Interactive gateway CLI")
        self._println(f"base_url   : {self.base_url}")
        self._println(f"session_id : {self.session_id}")
        if self.tenant_id:
            self._println(f"tenant_id  : {self.tenant_id}")
        self._println("Type /exit to quit.\n")

        try:
            while True:
                raw = input("> ").strip()
                if not raw:
                    continue
                if raw in {"/exit", "/quit"}:
                    break
                self._run_single_turn(raw)
        except KeyboardInterrupt:
            self._println("\nStopped.")
        finally:
            self.stop_event.set()
            sse_thread.join(timeout=1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive CLI for Seeknal gateway clarify flow")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SEEKNAL_GATEWAY_URL", "http://127.0.0.1:8000"),
        help="Gateway base URL",
    )
    parser.add_argument(
        "--session-id",
        default=f"cli-{uuid.uuid4().hex[:10]}",
        help="Session ID to keep multi-turn context",
    )
    parser.add_argument(
        "--tenant-id",
        default=os.getenv("SEEKNAL_TENANT_ID"),
        help="Optional X-Tenant-ID header",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cli = InteractiveGatewayCLI(
        base_url=args.base_url,
        session_id=args.session_id,
        tenant_id=args.tenant_id,
    )
    cli.run()


if __name__ == "__main__":
    main()
