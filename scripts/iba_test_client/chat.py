"""IBA v6 chat client — two-phase POST /v6/chat + GET /v6/sse SSE streaming.

The IBA chat flow is split into two phases:

Phase 1 — Initiate (POST /v6/chat):
    Sends the user query. Returns immediately with ``message_id`` and
    ``sse_token``; the backend queues the request to a Seeknal worker via
    Temporal without blocking the HTTP response.

Phase 2 — Stream (GET /v6/sse):
    Opens a Server-Sent Events stream. The Seeknal worker publishes events
    (``token``, ``tool_call``, ``message``, ``done``, ``error``) to a Redis
    pub/sub channel; the SSE server forwards them to this connection.
    The ``sse_token`` is single-use (consumed atomically in Redis by Lua
    script), so reconnecting after a disconnect is not possible.

Key design decisions:
    - The inactivity timeout resets on every event including heartbeats,
      so the stream survives long worker processing times.
    - ``error`` events are NOT terminal — the Seeknal worker may retry a
      failed Gemini call internally and still publish a ``message`` event
      afterwards. Only ``done`` signals the true end of a stream.
    - If a ``message`` event arrives after an earlier ``error`` event,
      the error is cleared (retry succeeded).

Usage:
    client = IBAChatClient(token, "https://alpha.keycenter.ai/api")
    answer = client.ask("Berapa total NIE ERBA 2024?", domain_id="<uuid>")
    print(answer.answer)
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from iba_test_client.metrics import LatencyTracker, RequestMetrics

log = logging.getLogger("iba-test-chat")


@dataclass
class ChatResponse:
    """Response from POST /v6/chat initiation."""

    message_id: str
    sse_url: str
    sse_token: str
    conversation_id: str = ""
    status_code: int = 200
    error: Optional[str] = None


@dataclass
class StreamResult:
    """Collected result from SSE stream."""

    answer: str = ""
    reasoning: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    tool_call_count: int = 0
    sqls: list[str] = field(default_factory=list)
    conversation_id: str = ""
    done: bool = False
    error: Optional[str] = None
    timed_out: bool = False


@dataclass
class Answer:
    """Combined result of a full chat request (init + stream)."""

    answer: str = ""
    conversation_id: str = ""
    message_id: str = ""
    metrics: Optional[RequestMetrics] = None
    tool_calls: int = 0
    sqls: list[str] = field(default_factory=list)
    error: Optional[str] = None
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.error is None and not self.timed_out


SQL_PATTERN = re.compile(
    r"(?:SELECT|INSERT|UPDATE|DELETE|WITH)\s.+?(?:;|$)",
    re.IGNORECASE | re.DOTALL,
)


def _extract_sqls(tool_args: dict | str) -> list[str]:
    """Extract SQL queries from tool call arguments."""
    sqls = []
    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except (json.JSONDecodeError, TypeError):
            return sqls
    if isinstance(tool_args, dict):
        sql = tool_args.get("sql", "").strip()
        if sql:
            sqls.append(sql)
    return sqls


class IBAChatClient:
    """HTTP client for IBA v6 chat API (POST /v6/chat + GET /v6/sse).

    Args:
        token: Keycloak JWT access_token.
        base_url: IBA service base URL (e.g., http://localhost:6800).
        service_path: API service path prefix (default: /services/iba).
    """

    def __init__(self, token: str, base_url: str, service_path: str = "/services/iba"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.service_path = service_path.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}{self.service_path}{path}"

    def send_message(
        self,
        query: str,
        domain_id: str,
        conversation_id: str = "",
    ) -> ChatResponse:
        """Initiate a chat message (Phase 1).

        Args:
            query: The user's question.
            domain_id: Target domain UUID.
            conversation_id: Existing conversation ID, or empty for new conversation.

        Returns:
            ChatResponse with message_id, sse_url, sse_token.
        """
        body = {
            "query": query,
            "domain_id": domain_id,
        }
        if conversation_id:
            body["conversation_id"] = conversation_id

        r = requests.post(
            self._api_url("/v6/chat"),
            headers=self._headers,
            json=body,
            timeout=30,
        )

        if r.status_code != 200:
            return ChatResponse(
                message_id="",
                sse_url="",
                sse_token="",
                status_code=r.status_code,
                error=r.text[:500],
            )

        data = r.json()
        return ChatResponse(
            message_id=data.get("message_id", ""),
            sse_url=data.get("sse_url", ""),
            sse_token=data.get("sse_token", ""),
            conversation_id=data.get("conversation_id", conversation_id),
            status_code=200,
        )

    def stream_response(
        self,
        message_id: str,
        sse_token: str,
        timeout: int = 300,
    ) -> StreamResult:
        """Stream SSE response (Phase 2).

        The timeout is an *inactivity* timeout — the deadline resets every time
        an event (including heartbeat) is received. This keeps the stream alive
        while the worker is processing queued requests (heartbeats every 15s).

        Args:
            message_id: From ChatResponse.
            sse_token: From ChatResponse (single-use).
            timeout: Max seconds of *inactivity* (no events) before giving up.

        Returns:
            StreamResult with collected answer, tool_calls, sqls.
        """
        url = self._api_url(f"/v6/sse?message_id={message_id}&sse_token={sse_token}")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "text/event-stream",
        }

        result = StreamResult()
        deadline = time.monotonic() + timeout
        event_count = 0

        try:
            r = requests.get(url, headers=headers, stream=True, timeout=timeout + 60)
            r.raise_for_status()

            for line in r.iter_lines(decode_unicode=True):
                if time.monotonic() > deadline:
                    result.timed_out = True
                    log.debug("SSE stream timeout after %ds (no events for %ds)", int(time.monotonic() - (deadline - timeout)), timeout)
                    break

                if not line or not line.startswith("data: "):
                    continue

                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                event_type = event.get("event", "")
                payload = event.get("payload", {})
                event_count += 1

                # Reset deadline on ANY event (including heartbeat).
                # This makes timeout an *inactivity* timeout — the stream stays
                # alive as long as events keep arriving (heartbeats every 15s).
                deadline = time.monotonic() + timeout
                if event_type == "heartbeat":
                    log.debug("SSE heartbeat received (event #%d)", event_count)

                # Reset deadline on ANY event (including heartbeat).
                # This makes timeout an *inactivity* timeout — the stream stays
                # alive as long as events keep arriving (heartbeats every 15s).
                deadline = time.monotonic() + timeout

                if event_type == "token":
                    result.answer += payload.get("answer", "")
                elif event_type == "reasoning":
                    result.reasoning.append(payload.get("answer", ""))
                elif event_type == "tool_call":
                    result.tool_call_count += 1
                    tool_name = payload.get("tool_name", "")
                    tool_args = payload.get("tool_args", {})
                    result.tool_calls.append(
                        {"name": tool_name, "args": tool_args}
                    )
                    extracted = _extract_sqls(tool_args)
                    result.sqls.extend(extracted)
                elif event_type == "tool_result":
                    pass  # tracked via tool_call
                elif event_type == "message":
                    result.answer = payload.get("answer", result.answer)
                    result.error = None  # retry succeeded after earlier error event
                    result.conversation_id = event.get(
                        "conversation_id", result.conversation_id
                    )
                elif event_type == "done":
                    result.done = True
                    result.conversation_id = event.get(
                        "conversation_id", result.conversation_id
                    )
                    break
                elif event_type == "error":
                    result.error = payload.get("error_message", "unknown error")
                    # Don't break — Temporal may retry the failed activity and
                    # publish a successful message+done event after this error.
                    # Only "done" is the true terminal event.

        except requests.exceptions.Timeout:
            result.timed_out = True
            result.error = f"SSE stream timeout after {timeout}s"
        except requests.exceptions.ConnectionError as exc:
            result.error = f"SSE connection error: {exc}"
        except Exception as exc:
            result.error = f"SSE error: {type(exc).__name__}: {exc}"

        return result

    def ask(
        self,
        query: str,
        domain_id: str,
        conversation_id: str = "",
        stream_timeout: int = 300,
        auth_latency_ms: float = 0.0,
    ) -> Answer:
        """Full chat request — initiate + stream (convenience method).

        Args:
            query: The user's question.
            domain_id: Target domain UUID.
            conversation_id: Existing conversation ID, or empty for new.
            stream_timeout: Max seconds to wait for SSE stream.
            auth_latency_ms: Pre-measured auth latency to include in metrics.

        Returns:
            Answer with response text, metrics, and conversation context.
        """
        tracker = LatencyTracker()
        tracker.start("total")

        # Phase 1: Initiate
        tracker.start("init")
        chat_resp = self.send_message(query, domain_id, conversation_id)
        tracker.stop("init")
        tracker.set_status_code(chat_resp.status_code)

        if chat_resp.error:
            tracker.stop("total")
            metrics = tracker.build()
            metrics.auth_latency_ms = auth_latency_ms
            return Answer(
                error=chat_resp.error,
                metrics=metrics,
            )

        # Phase 2: Stream
        tracker.start("stream")
        tracker.start("ttft")  # will be stopped on first token
        stream_result = self.stream_response(
            chat_resp.message_id, chat_resp.sse_token, timeout=stream_timeout
        )
        tracker.stop("stream")
        tracker.stop("total")

        tracker.set_tool_calls(stream_result.tool_call_count)
        tracker.set_sqls(stream_result.sqls)
        if stream_result.error:
            tracker.set_error(stream_result.error)

        metrics = tracker.build()
        metrics.auth_latency_ms = auth_latency_ms

        return Answer(
            answer=stream_result.answer,
            conversation_id=stream_result.conversation_id or chat_resp.conversation_id,
            message_id=chat_resp.message_id,
            metrics=metrics,
            tool_calls=stream_result.tool_call_count,
            sqls=stream_result.sqls,
            error=stream_result.error,
            timed_out=stream_result.timed_out,
        )
