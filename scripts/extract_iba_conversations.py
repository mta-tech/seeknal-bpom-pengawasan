#!/usr/bin/env python3
"""
Extract conversation history from iba_service PostgreSQL to JSON or Parquet.

Connects to iba-prod-postgres via DuckDB PostgreSQL extension.
Requires VPN (Pritunl server: bpom) — 10.200.0.3:6543 must be reachable.

Output structure:
  JSON   — nested: one conversation object per entry, with a `messages` list inside.
  Parquet — flat: one row per message, conversation fields repeated on every row.

── Date Range ────────────────────────────────────────────────────────────────

  --period 1d          Last 1 day from now
  --period 7d          Last 7 days from now
  --period 30d         Last 30 days from now
  --yesterday          Only yesterday (00:00–23:59 UTC)
  --from 2026-06-01    From this date to now
  --from 2026-06-01 --to 2026-06-15   Explicit date window

── Column Groups (--columns) ─────────────────────────────────────────────────

  core          Quick-analysis shortcut:
                  question, answer, error_message, account_id,
                  conv_question, vote, response_time_ms

  messages      Full message content:
                  question, answer, is_error, error_message, event_type,
                  is_free, dify_id, caching_message_id, metadata, file_download

  conversations Conversation metadata:
                  conv_question, conv_summary, is_active, group_id

  users         User and domain identity:
                  account_id, domain_id, domain_name, domain_type

  platform      Channel information:
                  conv_platform, msg_platform

  vote          Feedback signal:
                  vote  → "up" | "down" | null (none)

  time          Timing fields:
                  started_at, ended_at, response_time_ms,
                  msg_created_at, conv_created_at

  sql           SQL execution trace:
                  sqls  → list of SQL queries executed by the agent to answer
                          the user's question (parsed from metadata JSONB)

  all           Every group above (default)

Groups can be combined: --columns core,platform

── Output ────────────────────────────────────────────────────────────────────

  --format json        Write .json  (default)
  --format parquet     Write .parquet
  --format both        Write both files
  --pretty             Indent JSON output (readable, larger file)
  --output PATH        Custom output stem (no extension)

── Filters ───────────────────────────────────────────────────────────────────

  --domain DOMAIN_ID   Restrict to one knowledge domain
  --platform PLATFORM  Restrict to one platform (e.g. web)

── Usage Examples ────────────────────────────────────────────────────────────

  # Minimal — last day, all columns, JSON
  python scripts/extract_iba_conversations.py --period 1d

  # Quick read — core fields only, pretty-printed JSON
  python scripts/extract_iba_conversations.py --yesterday --columns core --pretty

  # Analysis export — 30 days to Parquet
  python scripts/extract_iba_conversations.py --period 30d --format parquet

  # Targeted — specific date window, vote + time only, both formats
  python scripts/extract_iba_conversations.py \\
      --from 2026-06-01 --to 2026-06-15 \\
      --columns vote,time,messages --format both

  # Filtered — single domain, last 7 days
  python scripts/extract_iba_conversations.py \\
      --period 7d --domain <domain_id> --platform web

── Environment Variables ─────────────────────────────────────────────────────

  IBA_DB_HOST      DB host      (default: 10.200.0.3)
  IBA_DB_PORT      DB port      (default: 6543)
  IBA_DB_NAME      DB name      (default: iba_service)
  IBA_DB_USER      DB user      (default: postgres)
  IBA_DB_PASSWORD  DB password  (required — or use --password)

  Set in scripts/.env.extract or export in shell before running.
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

try:
    from dotenv import load_dotenv
    for _env in [
        Path(__file__).parent / ".env.extract",
        Path(__file__).parent.parent / ".env",
    ]:
        if _env.exists():
            load_dotenv(_env)
            break
except ImportError:
    pass


# ── Constants ─────────────────────────────────────────────────────────────────

_DEFAULT_HOST = os.getenv("IBA_DB_HOST", "10.200.0.3")
_DEFAULT_PORT = int(os.getenv("IBA_DB_PORT", "6543"))
_DEFAULT_DB   = os.getenv("IBA_DB_NAME",   "iba_service")
_DEFAULT_USER = os.getenv("IBA_DB_USER",   "postgres")
_DEFAULT_PASS = os.getenv("IBA_DB_PASSWORD", "")

_OUTPUT_DIR = (
    Path(__file__).parent.parent
    / "seeknal" / "tests" / "outputs" / "messagearchive"
)

# Always-included columns — minimum identity for every row.
_ALWAYS: list[str] = [
    "m.id AS message_id",
    "c.id AS conversation_id",
]

# Named column groups. Resolved at runtime via --columns.
# Keys also serve as valid argument values.
COLUMN_GROUPS: dict[str, list[str]] = {
    "core": [
        "m.question",
        "m.answer",
        "m.error_system_message AS error_message",
        "c.account_id",
        "c.question AS conv_question",
        "m.vote",
        "(EPOCH(m.ended_at) - EPOCH(m.started_at)) * 1000 AS response_time_ms",
    ],
    "messages": [
        "m.question",
        "m.answer",
        "m.is_error",
        "m.error_system_message AS error_message",
        "m.event_type",
        "m.is_free",
        "m.dify_id",
        "m.caching_message_id",
        "m.metadata::TEXT AS metadata",
        "m.file_download",
    ],
    "conversations": [
        "c.question AS conv_question",
        "c.summary  AS conv_summary",
        "c.is_active",
        "c.group_id",
    ],
    "users": [
        "c.account_id",
        "c.domain_id",
        "d.domain_name",
        "d.domain_type",
    ],
    "platform": [
        "c.platform AS conv_platform",
        "m.platform AS msg_platform",
    ],
    "vote": [
        "m.vote",
    ],
    "time": [
        "m.started_at",
        "m.ended_at",
        "(EPOCH(m.ended_at) - EPOCH(m.started_at)) * 1000 AS response_time_ms",
        "m.created_at AS msg_created_at",
        "c.created_at AS conv_created_at",
    ],
    "sql": [
        "m.metadata::TEXT AS metadata",
    ],
}

# Fields that belong at the conversation level when building nested JSON.
_CONV_PREFIXES = (
    "conversation_id",
    "conv_",
    "account_id",
    "domain_id",
    "domain_name",
    "domain_type",
    "is_active",
    "group_id",
)


# ── Exceptions ────────────────────────────────────────────────────────────────

class ExtractError(Exception):
    """Base class for all extraction failures."""


class ConnectionError(ExtractError):  # noqa: A001
    """Database connection or query execution failed."""


class DateRangeError(ExtractError):
    """Date range flags are missing, malformed, or logically invalid."""


class ColumnGroupError(ExtractError):
    """An unrecognised column group name was requested."""


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DateRange:
    """Immutable UTC date window used in the WHERE clause.

    Attributes:
        date_from: Start of the window (inclusive).
        date_to:   End of the window (exclusive).
    """

    date_from: datetime
    date_to:   datetime

    def label(self) -> str:
        """Return a compact label for use in auto-generated file names.

        Returns:
            str: E.g. ``"12h"``, ``"1d"``, ``"30d"``.

        Example:
            >>> dr = DateRange(datetime(2026, 6, 14, tzinfo=timezone.utc),
            ...                datetime(2026, 6, 15, tzinfo=timezone.utc))
            >>> dr.label()
            '1d'
        """
        delta = self.date_to - self.date_from
        total_hours = int(delta.total_seconds() // 3600)
        if total_hours < 24:
            return f"{total_hours}h"
        days = delta.days
        return "1d" if days == 1 else f"{days}d"


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser with all CLI flags.

    Returns:
        argparse.ArgumentParser: Fully configured parser.
    """
    valid = ", ".join(sorted(COLUMN_GROUPS)) + ", all"
    p = argparse.ArgumentParser(
        prog="extract_iba_conversations.py",
        description="Extract iba_service conversation history to JSON or Parquet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── date range (period / yesterday / from-to are mutually exclusive) ──
    period = p.add_mutually_exclusive_group()
    period.add_argument(
        "--period", metavar="N(d|h)",
        help="Last N days or hours from now. E.g. --period 12h, --period 1d, --period 30d",
    )
    period.add_argument(
        "--yesterday", action="store_true",
        help="Extract only yesterday's data (UTC 00:00–23:59).",
    )

    p.add_argument(
        "--from", dest="date_from", metavar="YYYY-MM-DD",
        help="Start date (inclusive). Pair with --to for an explicit window.",
    )
    p.add_argument(
        "--to", dest="date_to", metavar="YYYY-MM-DD",
        help="End date (exclusive). Defaults to today when --from is used alone.",
    )

    # ── column selection ──
    p.add_argument(
        "--columns", default="all", metavar="GROUP[,GROUP,...]",
        help=f"Column groups to include. Valid: {valid}. Default: all",
    )

    # ── output ──
    p.add_argument(
        "--format", dest="output_format",
        choices=["json", "parquet", "both"], default="json",
        help="Output format. Default: json",
    )
    p.add_argument(
        "--output", metavar="PATH",
        help="Output file stem (no extension). Default: iba_conversations_<period>_<timestamp>",
    )
    p.add_argument(
        "--pretty", action="store_true",
        help="Indent JSON with 2 spaces (human-readable).",
    )

    # ── filters ──
    p.add_argument("--domain",   metavar="DOMAIN_ID", help="Filter by domain_id.")
    p.add_argument("--platform", metavar="PLATFORM",  help="Filter by platform (e.g. web).")

    # ── database connection ──
    p.add_argument("--host",     default=_DEFAULT_HOST, help=f"DB host. Default: {_DEFAULT_HOST}")
    p.add_argument("--port",     default=_DEFAULT_PORT, type=int, help=f"DB port. Default: {_DEFAULT_PORT}")
    p.add_argument("--db",       default=_DEFAULT_DB,   help=f"Database name. Default: {_DEFAULT_DB}")
    p.add_argument("--user",     default=_DEFAULT_USER, help=f"DB user. Default: {_DEFAULT_USER}")
    p.add_argument("--password", default=_DEFAULT_PASS, help="DB password (or set IBA_DB_PASSWORD).")

    return p


# ── Validation & resolution ───────────────────────────────────────────────────

def resolve_date_range(args: argparse.Namespace) -> DateRange:
    """Derive a UTC-bounded DateRange from the parsed CLI arguments.

    Args:
        args (argparse.Namespace): Parsed namespace; examined fields are
            ``period``, ``yesterday``, ``date_from``, ``date_to``.

    Returns:
        DateRange: Frozen dataclass with UTC-aware ``date_from`` and ``date_to``.

    Raises:
        DateRangeError: When no date flag is supplied, ``--period`` has
            invalid format, or ``date_from >= date_to``.

    Example:
        >>> import types
        >>> ns = types.SimpleNamespace(period="7d", yesterday=False,
        ...                            date_from=None, date_to=None)
        >>> dr = resolve_date_range(ns)
        >>> (dr.date_to - dr.date_from).days
        8
    """
    today = datetime.now(tz=timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # ── --period Nd / Nh ──
    if args.period:
        m = re.fullmatch(r"(\d+)(d|h)", args.period)
        if not m:
            raise DateRangeError(
                f"Invalid --period '{args.period}'. Expected format: Nd or Nh (e.g. 12h, 1d, 30d)."
            )
        n, unit = int(m.group(1)), m.group(2)
        if n <= 0:
            raise DateRangeError("--period must be a positive integer.")
        now = datetime.now(tz=timezone.utc)
        if unit == "h":
            return DateRange(
                date_from=now - timedelta(hours=n),
                date_to=now,
            )
        return DateRange(
            date_from=today - timedelta(days=n),
            date_to=today + timedelta(days=1),
        )

    # ── --yesterday ──
    if args.yesterday:
        return DateRange(
            date_from=today - timedelta(days=1),
            date_to=today,
        )

    # ── --from [--to] ──
    if args.date_from:
        try:
            date_from = datetime.fromisoformat(args.date_from).replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise DateRangeError(f"Invalid --from value '{args.date_from}': {exc}") from exc

        if args.date_to:
            try:
                date_to = datetime.fromisoformat(args.date_to).replace(tzinfo=timezone.utc)
            except ValueError as exc:
                raise DateRangeError(f"Invalid --to value '{args.date_to}': {exc}") from exc
        else:
            date_to = today + timedelta(days=1)

        if date_from >= date_to:
            raise DateRangeError(
                f"--from ({args.date_from}) must be earlier than --to ({args.date_to or 'today'})."
            )
        return DateRange(date_from=date_from, date_to=date_to)

    raise DateRangeError(
        "No date range provided. Use --period Nd, --yesterday, or --from YYYY-MM-DD."
    )


def resolve_columns(raw: str) -> list[str]:
    """Expand a comma-separated group string into SQL column expressions.

    Columns are deduplicated while preserving declaration order within each
    group. When ``"all"`` appears (or is the sole value), every group is
    included in the order defined in ``COLUMN_GROUPS``.

    Args:
        raw (str): Comma-separated group names, e.g. ``"messages,vote,time"``
            or ``"all"``.

    Returns:
        list[str]: Flat, deduplicated list of SQL column expressions ready
            to embed in a ``SELECT`` statement.

    Raises:
        ColumnGroupError: When any requested group name is not a key in
            ``COLUMN_GROUPS`` and is not ``"all"``.

    Example:
        >>> cols = resolve_columns("vote,time")
        >>> "m.vote" in cols
        True
        >>> "m.started_at" in cols
        True
    """
    valid = set(COLUMN_GROUPS) | {"all"}
    requested = [g.strip().lower() for g in raw.split(",") if g.strip()]
    unknown = [g for g in requested if g not in valid]
    if unknown:
        raise ColumnGroupError(
            f"Unknown column group(s): {', '.join(unknown)}. "
            f"Valid groups: {', '.join(sorted(valid))}."
        )

    groups = list(COLUMN_GROUPS) if "all" in requested else requested

    seen: set[str] = set()
    result: list[str] = []
    for g in groups:
        for col in COLUMN_GROUPS[g]:
            if col not in seen:
                seen.add(col)
                result.append(col)
    return result


def build_output_stem(args: argparse.Namespace, date_range: DateRange) -> str:
    """Return the output file stem (path without extension).

    Uses ``args.output`` when provided; otherwise constructs a timestamped
    default name from the date range label.

    Args:
        args (argparse.Namespace): Parsed CLI arguments.
        date_range (DateRange): Resolved date range for labelling.

    Returns:
        str: File path stem, e.g. ``"iba_conversations_30d_20260615_0900"``.

    Example:
        >>> import types
        >>> ns = types.SimpleNamespace(output=None)
        >>> stem = build_output_stem(ns, DateRange(...))
        >>> stem.startswith("iba_conversations_")
        True
    """
    if args.output:
        return args.output
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return str(_OUTPUT_DIR / f"iba_conversations_{date_range.label()}_{ts}")


def build_db_url(args: argparse.Namespace) -> str:
    """Compose a PostgreSQL connection URL from CLI / environment values.

    Args:
        args (argparse.Namespace): Parsed CLI arguments supplying host,
            port, db, user, and password.

    Returns:
        str: Full ``postgresql://`` URL string.

    Raises:
        ConnectionError: When ``args.password`` is empty and
            ``IBA_DB_PASSWORD`` is not set.

    Example:
        >>> import types
        >>> ns = types.SimpleNamespace(
        ...     host="10.200.0.3", port=6543, db="iba_service",
        ...     user="postgres", password="secret")
        >>> build_db_url(ns)
        'postgresql://postgres:secret@10.200.0.3:6543/iba_service'
    """
    if not args.password:
        raise ConnectionError(
            "DB password is required. "
            "Set IBA_DB_PASSWORD in .env.extract or use --password."
        )
    return f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.db}"


# ── Database ──────────────────────────────────────────────────────────────────

def open_connection(db_url: str) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB in-memory connection and attach the iba_service database.

    Uses the DuckDB ``postgres`` extension to read directly from PostgreSQL
    without a separate psycopg dependency. The attached alias is ``iba``.

    Args:
        db_url (str): Full ``postgresql://`` connection URL.

    Returns:
        duckdb.DuckDBPyConnection: Open connection with ``iba`` attached.

    Raises:
        ConnectionError: When the extension cannot load or the attach fails
            (wrong credentials, host unreachable, VPN not connected).

    Example:
        >>> con = open_connection("postgresql://postgres:pass@10.200.0.3:6543/iba_service")
        >>> con.execute("SELECT 1").fetchone()
        (1,)
    """
    try:
        con = duckdb.connect()
        con.execute("INSTALL postgres; LOAD postgres;")
        con.execute(f"ATTACH '{db_url}' AS iba (TYPE POSTGRES, READ_ONLY)")
        return con
    except Exception as exc:
        raise ConnectionError(f"Cannot connect to database: {exc}") from exc


def build_query(
    columns: list[str],
    date_range: DateRange,
    domain_id: str | None,
    platform: str | None,
) -> tuple[str, dict[str, Any]]:
    """Build the extraction SELECT statement and its named parameter dict.

    Always joins ``messages → conversations → domains``. Applies date,
    domain, and platform filters as positional DuckDB ``$name`` parameters
    to prevent SQL injection.

    Args:
        columns (list[str]): SQL column expressions from ``resolve_columns``.
        date_range (DateRange): UTC-aware date window for the WHERE clause.
        domain_id (str | None): Optional domain_id equality filter.
        platform (str | None): Optional ``messages.platform`` equality filter.

    Returns:
        tuple[str, dict[str, Any]]: ``(sql, params)`` — the SQL string with
            ``$name`` placeholders and the matching parameter dict.

    Example:
        >>> sql, params = build_query(["m.question"], date_range, None, None)
        >>> "$date_from" in sql
        True
        >>> "date_from" in params
        True
    """
    select = ",\n    ".join(_ALWAYS + columns)

    where: list[str] = [
        "m.created_at >= $date_from",
        "m.created_at <  $date_to",
    ]
    params: dict[str, Any] = {
        "date_from": date_range.date_from.isoformat(),
        "date_to":   date_range.date_to.isoformat(),
    }

    if domain_id:
        where.append("c.domain_id = $domain_id")
        params["domain_id"] = domain_id

    if platform:
        where.append("m.platform = $platform")
        params["platform"] = platform

    sql = (
        f"SELECT\n    {select}\n"
        "FROM iba.public.messages      m\n"
        "JOIN iba.public.conversations c ON c.id = m.conversation_id\n"
        "LEFT JOIN iba.public.domains  d ON d.id = c.domain_id\n"
        "WHERE " + "\n  AND ".join(where) + "\n"
        "ORDER BY c.created_at ASC, m.created_at ASC"
    )
    return sql, params


def run_query(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute the extraction query and return rows as a list of dicts.

    Args:
        con (duckdb.DuckDBPyConnection): Open connection with ``iba`` attached.
        sql (str): SELECT statement with ``$name`` placeholders.
        params (dict[str, Any]): Parameter values matching the placeholders.

    Returns:
        list[dict[str, Any]]: One dict per message row. Empty list when the
            query matches no rows.

    Raises:
        ConnectionError: When DuckDB raises any exception during execution.

    Example:
        >>> rows = run_query(con, "SELECT 1 AS n", {})
        >>> rows[0]["n"]
        1
    """
    try:
        result  = con.execute(sql, params)
        headers = [d[0] for d in result.description]
        return [dict(zip(headers, row)) for row in result.fetchall()]
    except Exception as exc:
        raise ConnectionError(f"Query failed: {exc}") from exc


# ── Data shaping ──────────────────────────────────────────────────────────────

def _is_conv_field(key: str) -> bool:
    """Return True when a column belongs at the conversation level.

    Args:
        key (str): Column name from a result row dict.

    Returns:
        bool: ``True`` for conversation-level fields; ``False`` for
            message-level fields.
    """
    return key.startswith(_CONV_PREFIXES)


def nest_by_conversation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group flat per-message rows into a nested conversation structure.

    Conversation-level fields (anything matching ``_CONV_PREFIXES``) are
    hoisted to the parent object. Message-level fields are placed inside
    a ``messages`` list under that parent. Row order is preserved.

    When a ``metadata`` key is present in a row (from the ``sql`` or
    ``messages`` column group), it is parsed via
    ``extract_sqls_from_metadata`` and replaced by a ``sqls`` list field
    containing every SQL query executed by the agent for that message.
    The raw ``metadata`` text is not included in the output.

    Args:
        rows (list[dict[str, Any]]): Flat message rows from ``run_query``.

    Returns:
        list[dict[str, Any]]: Conversation objects, each containing a
            ``messages`` list with the ordered messages for that conversation.
            Each message may include a ``sqls`` field (list of SQL strings)
            when metadata was requested.

    Example:
        >>> rows = [
        ...     {"conversation_id": "c1", "account_id": "u1",
        ...      "message_id": "m1", "question": "hi", "answer": "hello"},
        ...     {"conversation_id": "c1", "account_id": "u1",
        ...      "message_id": "m2", "question": "bye", "answer": "goodbye"},
        ... ]
        >>> nested = nest_by_conversation(rows)
        >>> len(nested)
        1
        >>> len(nested[0]["messages"])
        2
        >>> nested[0]["messages"][0]["question"]
        'hi'
    """
    index: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for row in rows:
        cid = row["conversation_id"]
        if cid not in index:
            conv = {k: v for k, v in row.items() if _is_conv_field(k)}
            index[cid] = {**conv, "messages": []}
            order.append(cid)
        msg = {k: v for k, v in row.items() if not _is_conv_field(k)}
        if "metadata" in msg:
            msg["sqls"] = extract_sqls_from_metadata(msg.pop("metadata"))
        index[cid]["messages"].append(msg)

    return [index[cid] for cid in order]


def extract_sqls_from_metadata(metadata_text: str | None) -> list[str]:
    """Parse metadata JSONB text and return all SQL queries executed by the agent.

    The IBA service stores each agent session's tool calls inside the ``metadata``
    JSONB column of the ``messages`` table. This function extracts only the
    ``execute_sql`` tool call arguments to reconstruct the list of SQL queries
    that were run to answer the user's question.

    Args:
        metadata_text (str | None): Raw JSON string from ``m.metadata::TEXT``.

    Returns:
        list[str]: Ordered list of SQL query strings. Empty list when metadata
            is absent, unparseable, or contains no SQL tool calls.

    Example:
        >>> meta = json.dumps({"events": [{"event": "tool_call", "payload":
        ...     {"tool_name": "execute_sql", "tool_args": {"sql": "SELECT 1"}}}]})
        >>> extract_sqls_from_metadata(meta)
        ['SELECT 1']
    """
    if not metadata_text:
        return []
    try:
        meta = json.loads(metadata_text)
        sqls: list[str] = []
        for event in meta.get("events", []):
            if event.get("event") == "tool_call":
                payload = event.get("payload", {})
                if payload.get("tool_name") == "execute_sql":
                    sql = payload.get("tool_args", {}).get("sql", "").strip()
                    if sql:
                        sqls.append(sql)
        return sqls
    except (json.JSONDecodeError, AttributeError):
        return []


# ── Writers ───────────────────────────────────────────────────────────────────

def _json_default(obj: Any) -> Any:
    """Fallback JSON serialiser for non-standard types.

    Args:
        obj (Any): Object that the default JSON encoder cannot handle.

    Returns:
        Any: JSON-serialisable representation.

    Raises:
        TypeError: When the type is not handled by this function.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable.")


def write_json(
    conversations: list[dict[str, Any]],
    path: str,
    *,
    pretty: bool = False,
) -> None:
    """Serialise nested conversation data to a UTF-8 JSON file.

    Args:
        conversations (list[dict[str, Any]]): Grouped output from
            ``nest_by_conversation``.
        path (str): Destination file path (including ``.json`` extension).
        pretty (bool): When ``True``, indent with 2 spaces. Default ``False``.

    Example:
        >>> write_json(data, "output.json", pretty=True)
        # Writes indented JSON → output.json
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(
            conversations, fh,
            default=_json_default,
            indent=2 if pretty else None,
            ensure_ascii=False,
        )


def write_parquet(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any],
    path: str,
) -> None:
    """Stream query results directly to a ZSTD-compressed Parquet file.

    Bypasses Python-level row materialisation — DuckDB writes straight to
    disk. Output is flat (one row per message); use ``nest_by_conversation``
    only for JSON output.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        sql (str): The extraction SELECT statement.
        params (dict[str, Any]): Parameter values for the SELECT.
        path (str): Destination file path (including ``.parquet`` extension).

    Example:
        >>> write_parquet(con, sql, params, "output.parquet")
        # Writes flat Parquet → output.parquet
    """
    con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)", params)


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(
    n_conversations: int,
    n_messages: int,
    date_range: DateRange,
    output_format: str,
    stem: str,
    elapsed: float,
) -> None:
    """Print a concise extraction summary to stdout.

    Args:
        n_conversations (int): Number of distinct conversations extracted.
        n_messages (int): Total message rows extracted.
        date_range (DateRange): The resolved date window.
        output_format (str): One of ``"json"``, ``"parquet"``, ``"both"``.
        stem (str): Output file stem (no extension).
        elapsed (float): Wall-clock seconds taken by the full extraction.
    """
    print()
    print("── Extraction Summary ───────────────────────────────")
    print(f"  Date range    : {date_range.date_from.date()} → {date_range.date_to.date()}")
    print(f"  Conversations : {n_conversations:,}")
    print(f"  Messages      : {n_messages:,}")
    print(f"  Elapsed       : {elapsed:.1f}s")
    if output_format in ("json",    "both"):
        print(f"  JSON          : {stem}.json")
    if output_format in ("parquet", "both"):
        print(f"  Parquet       : {stem}.parquet")
    print("─────────────────────────────────────────────────────")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Run the full extraction pipeline.

    Steps:
        1. Parse CLI arguments.
        2. Resolve date range and column groups.
        3. Open DuckDB → PostgreSQL connection.
        4. Execute extraction query.
        5. Write output (JSON nested / Parquet flat).
        6. Print summary.

    Raises:
        SystemExit: On any ``ExtractError``; message printed to stderr, exit 1.
    """
    parser = _build_parser()
    args   = parser.parse_args()
    t0     = time.perf_counter()

    try:
        date_range = resolve_date_range(args)
        columns    = resolve_columns(args.columns)
        db_url     = build_db_url(args)
        stem       = build_output_stem(args, date_range)

        print(f"Connecting  → {args.host}:{args.port}/{args.db}")
        con = open_connection(db_url)

        print(
            f"Extracting  → {date_range.date_from.date()} "
            f"to {date_range.date_to.date()} …"
        )
        sql, params = build_query(columns, date_range, args.domain, args.platform)
        rows        = run_query(con, sql, params)

        if not rows:
            print("  ⚠  No rows matched — no files written.")
            con.close()
            return

        conversations = nest_by_conversation(rows)

        if args.output_format in ("json", "both"):
            dest = f"{stem}.json"
            print(f"Writing     → {dest}")
            write_json(conversations, dest, pretty=args.pretty)

        if args.output_format in ("parquet", "both"):
            dest = f"{stem}.parquet"
            print(f"Writing     → {dest}")
            write_parquet(con, sql, params, dest)

        con.close()

        print_summary(
            n_conversations=len(conversations),
            n_messages=len(rows),
            date_range=date_range,
            output_format=args.output_format,
            stem=stem,
            elapsed=time.perf_counter() - t0,
        )

    except ExtractError as exc:
        print(f"\n✗  {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
