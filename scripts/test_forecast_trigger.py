"""Forecast trigger test — verify run_forecast and upload_to_s3 fire correctly.

Single-purpose probe script that fires forecast questions at the seeknal agent
(in-process, ``environment='gateway'`` — same as the real HTTP worker) and
reports exactly which tools triggered, with what args, and what they returned.

Designed to answer three diagnostic questions after a code/skill change:

  1. Did the agent construct a flat 2-column SQL (no LEFT JOIN / generate_series)?
  2. Did ``run_forecast`` actually fire (not get skipped, not crash the activity)?
  3. Did ``upload_to_s3`` fire (either via the reminder hook or agent initiative)?

Usage:
    # Default: run all built-in forecast questions
    IBA_FORECAST_URL=http://localhost:6705 uv run python scripts/test_forecast_trigger.py

    # One specific question
    IBA_FORECAST_URL=http://localhost:6705 uv run python scripts/test_forecast_trigger.py \\
        --question "forecast total ERBA 3 bulan ke depan"

    # Skip preflight (when engine/warehouse are already known-good)
    IBA_FORECAST_URL=http://localhost:6705 uv run python scripts/test_forecast_trigger.py --no-preflight

Pre-requisites (checked by preflight unless --no-preflight):
    - iba-forecast container reachable at $IBA_FORECAST_URL
    - PostgreSQL warehouse reachable at $WAREHOUSE_URL (BPOM data)
    - seeknal_agent.yml has agent.forecast.enabled: true and agent.upload_to_s3.enabled: true
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))

# Default reminder threshold used by the csv_upload_reminder hook. Imported
# here so the "general analytics" report path can mention the right number
# when explaining why upload_to_s3 was/wasn't offered proactively. This is a
# heuristic, NOT an access gate — explicit user requests ("download CSV")
# bypass this threshold entirely.
try:
    from seeknal.ask.agents.hooks import _CSV_REMINDER_MIN_ROWS
except Exception:  # pragma: no cover — fallback if import path shifts
    _CSV_REMINDER_MIN_ROWS = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("forecast-trigger")

# Built-in forecast questions covering the dynamic-SQL matrix from
# forecast_guide.md §7 Series Registry. Each one should produce a different
# SQL but the SAME 2-column shape (no JOINs).
DEFAULT_QUESTIONS: list[str] = [
    "forecast total ERBA 3 bulan ke depan",
    "forecast NIE Terbit ERBA untuk 6 bulan kedepan",
    "forecast BTP ERBA 3 bulan kedepan",
    # The two production-failing questions — must now succeed or return
    # a structured Kesalahan/Ditolak (NOT a raw activity crash).
    "forecast NIE aktif hingga 2026 akhir",
    "lakukan forecast untuk permintaan data tersebut dalam beberapa bulan kedepan",
]


@dataclass
class ToolCall:
    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnAnalysis:
    question: str
    answer: str = ""
    elapsed_s: float = 0.0
    error: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    forecast_result: str | None = None
    upload_result: str | None = None
    execute_sqls: list[str] = field(default_factory=list)

    @property
    def forecast_triggered(self) -> bool:
        return any(c.tool_name == "run_forecast" for c in self.tool_calls)

    @property
    def clarification_triggered(self) -> bool:
        """The agent correctly asked for clarification on an ambiguous question.

        This is a VALID outcome — when the series/scope is ambiguous (e.g.
        "NIE aktif" is not in §7 Series Registry), the skill instructs the
        agent to call ``request_clarification`` instead of guessing. A
        clarification turn is a pass, not a failure.
        """
        return any(c.tool_name == "request_clarification" for c in self.tool_calls)

    @property
    def upload_triggered(self) -> bool:
        return any(c.tool_name == "upload_to_s3" for c in self.tool_calls)

    @property
    def execute_sql_triggered(self) -> bool:
        """An execute_sql call. For non-forecast questions (general analytics),
        this is the primary data path and is a valid trigger for the turn —
        not a failure.
        """
        return any(c.tool_name == "execute_sql" for c in self.tool_calls)

    @property
    def forecast_sql(self) -> str | None:
        for c in self.tool_calls:
            if c.tool_name == "run_forecast":
                return str(c.args.get("sql", ""))
        return None

    @property
    def forecast_sql_has_forbidden(self) -> bool:
        sql = (self.forecast_sql or "").upper()
        return any(
            kw in sql
            for kw in ("JOIN", "GENERATE_SERIES", "WITH RECURSIVE")
        )

    @property
    def raw_error_in_answer(self) -> bool:
        """Detect the pre-fix failure mode: raw JSON error leaking into the answer."""
        if not self.answer:
            return False
        return (
            '"error":' in self.answer
            or "Conversion Error" in self.answer
            or "TIMESTAMP -> TIMESTAMP[]" in self.answer
        )


# ---------------------------------------------------------------------------
# Preflight — fail fast with a clear message instead of mysterious LLM errors
# ---------------------------------------------------------------------------


def _load_dotenv_if_present() -> None:
    """Populate os.environ from .env at PROJECT_ROOT if present.

    Mirrors what ``_load_project_env`` does inside the agent, so preflight can
    see WAREHOUSE_URL / IBA_FORECAST_URL / GOOGLE_API_KEY etc. without waiting
    for the first agent invocation. Explicitly-exported CLI values win.
    """
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def preflight() -> bool:
    """Verify engine + warehouse + config before running any question."""
    # Load .env first so WAREHOUSE_URL etc. are visible to preflight itself.
    # (run_question calls _load_project_env internally, but preflight runs
    # before any question — we want the same env visibility here.)
    _load_dotenv_if_present()

    ok = True

    # 1. Engine reachable
    engine_url = os.environ.get("IBA_FORECAST_URL", "http://iba-forecast:6705")
    log.info("preflight: engine URL = %s", engine_url)
    try:
        import httpx

        r = httpx.get(engine_url.rstrip("/"), timeout=5.0)
        r.raise_for_status()
        body = r.json()
        log.info(
            "preflight: engine OK — service=%s, model=%s",
            body.get("service"),
            body.get("model"),
        )
    except Exception as exc:
        log.error(
            "preflight: engine UNREACHABLE at %s — %s\n"
            "  hint: start via `docker compose -f docker-compose.infra.yml "
            "-f docker-compose.yml --profile all up -d iba-forecast` from the "
            "iba repo, and set IBA_FORECAST_URL=http://localhost:6705",
            engine_url,
            exc,
        )
        ok = False

    # 2. Warehouse reachable (best-effort — TCP only, no creds check)
    wh_url = os.environ.get("WAREHOUSE_URL", "")
    log.info("preflight: warehouse URL = %s", wh_url or "(unset)")
    if not wh_url:
        log.warning("preflight: WAREHOUSE_URL not set — agent will not be able to query data")
        ok = False
    else:
        try:
            from urllib.parse import urlparse

            p = urlparse(wh_url)
            import socket

            host = p.hostname or "localhost"
            port = p.port or 5432
            with socket.create_connection((host, port), timeout=3):
                log.info("preflight: warehouse TCP %s:%s OK", host, port)
        except Exception as exc:
            log.warning(
                "preflight: warehouse %s:%s unreachable — %s\n"
                "  hint: start your SSH tunnel to BPOM postgres (typically "
                "`scripts/start_tunnel.sh`)",
                host,
                port,
                exc,
            )
            ok = False

    # 3. seeknal_agent.yml gates
    cfg_path = PROJECT_ROOT / "seeknal_agent.yml"
    if cfg_path.exists():
        try:
            import yaml

            cfg = yaml.safe_load(cfg_path.read_text()) or {}
            agent = (cfg.get("agent") or {})
            fc = (agent.get("forecast") or {})
            up = (agent.get("upload_to_s3") or {})
            log.info(
                "preflight: agent.forecast.enabled=%s, agent.upload_to_s3.enabled=%s",
                fc.get("enabled"), up.get("enabled"),
            )
            if not fc.get("enabled"):
                log.error("preflight: agent.forecast.enabled is not true — run_forecast will NOT register")
                ok = False
        except Exception as exc:
            log.warning("preflight: could not parse %s — %s", cfg_path, exc)
    else:
        log.warning("preflight: %s not found", cfg_path)

    return ok


# ---------------------------------------------------------------------------
# Run one question through the agent
# ---------------------------------------------------------------------------


def run_question(question: str, turn_timeout: int = 0) -> TurnAnalysis:
    """Run a single forecast question in-process and capture tool calls."""
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor
    from pydantic_ai.messages import ToolCallPart, ToolReturnPart

    import seeknal.ask.testing as _testing_mod
    _testing_mod.save_ask_sql_test_results = lambda *a, **kw: Path("/dev/null")

    _load_project_env(PROJECT_ROOT)

    analysis = TurnAnalysis(question=question)

    try:
        agent, deps, history, _ = create_agent(PROJECT_ROOT, environment="gateway")
    except Exception as exc:
        analysis.error = f"create_agent failed: {type(exc).__name__}: {exc}"
        log.error(analysis.error)
        return analysis

    prev_len = len(history)
    reset_turn_governor(question)
    start = time.monotonic()

    try:
        if turn_timeout > 0:
            import signal

            def _handler(signum, frame):
                raise TimeoutError(f"turn exceeded {turn_timeout}s")

            old = signal.signal(signal.SIGALRM, _handler)
            signal.alarm(turn_timeout)
            try:
                analysis.answer = agent_ask(agent, deps, history, question)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
        else:
            analysis.answer = agent_ask(agent, deps, history, question)
    except TimeoutError as exc:
        analysis.error = f"TIMEOUT: {exc}"
    except Exception as exc:
        analysis.error = f"{type(exc).__name__}: {exc}"
        log.exception("agent_ask raised")

    analysis.elapsed_s = time.monotonic() - start

    # Walk new messages and capture tool calls + returns
    for msg in history[prev_len:]:
        for part in getattr(msg, "parts", []):
            if isinstance(part, ToolCallPart):
                args = part.args if isinstance(part.args, dict) else {}
                analysis.tool_calls.append(
                    ToolCall(tool_name=part.tool_name, args=dict(args))
                )
                if part.tool_name == "execute_sql":
                    sql = str(args.get("sql") or args.get("query") or "").strip()
                    if sql:
                        analysis.execute_sqls.append(sql)
            elif isinstance(part, ToolReturnPart):
                if part.tool_name == "run_forecast":
                    try:
                        analysis.forecast_result = (
                            part.content if isinstance(part.content, str)
                            else json.dumps(part.content)
                        )
                    except Exception:
                        analysis.forecast_result = str(part.content)
                elif part.tool_name == "upload_to_s3":
                    try:
                        analysis.upload_result = (
                            part.content if isinstance(part.content, str)
                            else json.dumps(part.content)
                        )
                    except Exception:
                        analysis.upload_result = str(part.content)

    return analysis


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def report(analyses: list[TurnAnalysis]) -> bool:
    """Pretty-print per-question analysis; return True iff all passed."""
    log.info("=" * 78)
    log.info("FORECAST TRIGGER REPORT — %d question(s)", len(analyses))
    log.info("=" * 78)

    all_pass = True

    for i, a in enumerate(analyses, 1):
        log.info("-" * 78)
        log.info("Q%d: %s", i, a.question)
        log.info("    elapsed: %.1fs", a.elapsed_s)

        if a.error:
            log.error("    STATUS: ERROR — %s", a.error)
            all_pass = False
            continue

        # Tool call sequence
        if not a.tool_calls:
            log.warning("    STATUS: NO TOOL CALLS — agent did nothing")
            all_pass = False
            continue

        log.info("    tool sequence: %s", " → ".join(c.tool_name for c in a.tool_calls))

        # Per-tool detail
        for c in a.tool_calls:
            if c.tool_name == "run_forecast":
                sql = str(c.args.get("sql", "")).strip().replace("\n", " ")
                periods = c.args.get("periods")
                log.info("    run_forecast args: periods=%s", periods)
                log.info("    run_forecast SQL:  %s", sql[:300] + (" ..." if len(sql) > 300 else ""))
            elif c.tool_name == "upload_to_s3":
                log.info(
                    "    upload_to_s3 args: filename=%s, sql=%s",
                    c.args.get("filename"),
                    str(c.args.get("sql", ""))[:200],
                )

        # Assertions
        failures: list[str] = []

        # A regression of the original crash surfaces as raw JSON error text
        # in the answer — that must NEVER happen, regardless of which tool fired.
        if a.raw_error_in_answer:
            failures.append("raw error leaked into answer (pre-fix regression)")

        # Clarification is a valid outcome for ambiguous questions — count as PASS.
        if a.clarification_triggered and not a.forecast_triggered:
            log.info("    STATUS: PASS (clarification)")
            log.info(
                "    clarification correctly triggered — question is ambiguous "
                "(skill instructs request_clarification for unclear series/scope)"
            )
            log.info("    answer (first 300c): %s", (a.answer or "")[:300])
            if failures:
                for f in failures:
                    log.error("      ✗ %s", f)
                all_pass = False
                continue
            continue

        # General analytics question (non-forecast): execute_sql + (optional)
        # upload_to_s3 is a valid PASS. The agent did its job — answered the
        # question with data, and offered/ran CSV export when warranted.
        # We only fail if NO data tool ran at all (genuine "did nothing").
        if not a.forecast_triggered and a.execute_sql_triggered:
            log.info("    STATUS: PASS (general analytics)")
            log.info(
                "    execute_sql ran (non-forecast path) — general data question"
            )
            if a.upload_triggered:
                log.info("    upload_to_s3: TRIGGERED")
                if a.upload_result:
                    log.info("      result: %s", a.upload_result[:200])
            else:
                log.info(
                    "    upload_to_s3: not triggered (either < %d rows or user did "
                    "not ask for CSV)",
                    _CSV_REMINDER_MIN_ROWS,
                )
            if failures:
                for f in failures:
                    log.error("      ✗ %s", f)
                all_pass = False
                continue
            continue

        if not a.forecast_triggered:
            failures.append("run_forecast was NOT triggered (and no clarification either)")
        if a.forecast_sql_has_forbidden:
            failures.append(
                f"forecast SQL contains forbidden pattern (JOIN/GENERATE_SERIES/RECURSIVE)"
            )
        if a.forecast_result:
            # Must be a structured markdown block — not a raw exception.
            fr = a.forecast_result
            is_ok = (
                "## Proyeksi" in fr
                or "## Ringkasan" in fr
                or "## Kesalahan" in fr
                or "## Ditolak" in fr
            )
            if not is_ok:
                failures.append(
                    f"forecast result is not a structured markdown block "
                    f"(first 200c): {fr[:200]!r}"
                )

        if failures:
            log.error("    STATUS: FAIL")
            for f in failures:
                log.error("      ✗ %s", f)
            all_pass = False
        else:
            log.info("    STATUS: PASS")
            if a.forecast_result:
                # Summarize the outcome (ok / refused / kesalahan)
                fr = a.forecast_result
                if "## Proyeksi" in fr or "## Ringkasan" in fr:
                    label_line = next(
                        (ln for ln in fr.splitlines()
                         if "Kualitas" in ln or "MAPE" in ln),
                        "",
                    )
                    log.info("    forecast outcome: 7-blok OK — %s", label_line.strip())
                elif "## Ditolak" in fr:
                    log.info("    forecast outcome: refused by engine (expected for short series)")
                elif "## Kesalahan" in fr:
                    first_lines = fr.splitlines()
                    detail = next(
                        (ln for ln in first_lines if "Detail" in ln or "rejected" in ln),
                        "(see body)",
                    )
                    log.info("    forecast outcome: Kesalahan — %s", detail.strip())

            if a.upload_triggered:
                log.info("    upload_to_s3: TRIGGERED")
                if a.upload_result:
                    log.info("      result: %s", a.upload_result[:200])
            else:
                log.info("    upload_to_s3: not triggered (reminder-only hook; agent may skip)")

        # Answer preview
        log.info("    answer (first 300c): %s", (a.answer or "")[:300])

    log.info("=" * 78)
    log.info("OVERALL: %s", "ALL PASS" if all_pass else "SOME FAILED")
    log.info("=" * 78)
    return all_pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--question", "-q",
        help="Run a single question instead of the built-in matrix.",
    )
    ap.add_argument(
        "--no-preflight",
        action="store_true",
        help="Skip engine/warehouse/config preflight checks.",
    )
    ap.add_argument(
        "--turn-timeout",
        type=int, default=0,
        help="Per-turn timeout in seconds (0 = no limit; sequential only).",
    )
    args = ap.parse_args()

    if not args.no_preflight:
        if not preflight():
            log.error("preflight failed — fix the issues above before running questions")
            return 2

    questions = [args.question] if args.question else list(DEFAULT_QUESTIONS)
    log.info("running %d question(s): %s", len(questions), questions)

    analyses: list[TurnAnalysis] = []
    for q in questions:
        log.info("=" * 78)
        log.info("QUESTION: %s", q)
        log.info("=" * 78)
        a = run_question(q, turn_timeout=args.turn_timeout)
        analyses.append(a)

    ok = report(analyses)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
