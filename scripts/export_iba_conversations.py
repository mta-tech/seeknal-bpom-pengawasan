"""Export conversation history from iba_service PostgreSQL to JSON or Parquet.

Connects to iba-prod-postgres (port 6543) via DuckDB PostgreSQL extension.
Requires VPN connection (Pritunl, server bpom) — 10.200.0.3 must be reachable.

Usage:
    # Last 1 day → JSON (default)
    python scripts/export_iba_conversations.py --period 1d

    # Last 30 days → Parquet
    python scripts/export_iba_conversations.py --period 30d --format parquet

    # Yesterday → both formats, pretty-printed JSON
    python scripts/export_iba_conversations.py --yesterday --format both --pretty

    # Explicit date range, select only vote + time + message content
    python scripts/export_iba_conversations.py --from 2026-06-01 --to 2026-06-15 \\
        --columns messages,vote,time

    # All columns, filter by domain and platform
    python scripts/export_iba_conversations.py --period 7d \\
        --domain <domain_id> --platform web

Column groups (--columns, comma-separated, default: all):
    messages      question, answer, is_error, error_message, event_type,
                  is_free, dify_id, caching_message_id, metadata, file_download
    conversations conv_question, conv_summary, is_active, group_id
    users         account_id, domain_id, domain_name
    platform      conv_platform, msg_platform
    vote          vote (up / down / NULL=none)
    time          started_at, ended_at, response_time_ms, msg_created_at, conv_created_at
    core          question, answer, error_message, account_id, conv_question,
                  vote, response_time_ms (quick-analysis shortcut)
    all           every group above (default)

Environment variables (or set via CLI flags):
    IBA_DB_HOST      default: 10.200.0.3
    IBA_DB_PORT      default: 6543
    IBA_DB_NAME      default: iba_service
    IBA_DB_USER      default: postgres
    IBA_DB_PASSWORD  required if not passed via --password
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_HOST = os.getenv("IBA_DB_HOST", "10.200.0.3")
DEFAULT_PORT = int(os.getenv("IBA_DB_PORT", "6543"))
DEFAULT_DB = os.getenv("IBA_DB_NAME", "iba_service")
DEFAULT_USER = os.getenv("IBA_DB_USER", "postgres")
DEFAULT_PASSWORD = os.getenv("IBA_DB_PASSWORD", "")

ALWAYS_INCLUDED: list[str] = [
    "m.id AS message_id",
    "c.id AS conversation_id",
]

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
        "c.summary AS conv_summary",
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
}

VALID_GROUPS = set(COLUMN_GROUPS.keys()) | {"all"}

# Conversation-level fields — used to separate message fields during grouping
CONV_FIELD_PREFIXES = ("conv_", "account_id", "domain_id", "domain_name", "is_active", "group_id")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExportError(Exception):
    """Base exception for all export failures."""


class DBConnectionError(ExportError):
    """Raised when the PostgreSQL database cannot be reached."""


class DateRangeError(ExportError):
    """Raised when date range arguments are missing or logically invalid."""


class ColumnGroupError(ExportError):
    """Raised when an unknown column group name is provided."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DateRange:
    """Immutable date window for the export query."""

    date_from: datetime
    date_to: datetime

    def label(self) -> str:
        """Return a short human-readable label for file naming."""
        delta = self.date_to - self.date_from
        days = delta.days
        if days == 1:
            return "1d"
        return f"{days}d"


@dataclass(frozen=True)
class ExportConfig:
    """Validated, resolved configuration for a single export run."""

    db_url: str
    date_range: DateRange
    columns: list[str]
    output_format: str
    output_path: str
    pretty: bool
    domain_id: str | None
    platform: str | None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments.

    Returns:
        Parsed argparse.Namespace with all flags resolved.
    """
    parser = argparse.ArgumentParser(
        description="Export iba_service conversation history to JSON or Parquet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # -- Date range (mutually exclusive group) --
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--period",
        metavar="Nd",
        help="Last N days from now. Examples: --period 1d  --period 30d",
    )
    date_group.add_argument(
        "--yesterday",
        action="store_true",
        help="Export only yesterday's data (00:00–23:59 UTC).",
    )

    parser.add_argument(
        "--from",
        dest="date_from",
        metavar="YYYY-MM-DD",
        help="Start date (inclusive). Combine with --to for explicit range.",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        metavar="YYYY-MM-DD",
        help="End date (exclusive). Defaults to today if --from is given alone.",
    )

    # -- Column selection --
    parser.add_argument(
        "--columns",
        default="all",
        metavar="GROUP[,GROUP...]",
        help=(
            "Comma-separated column groups to include. "
            f"Valid groups: {', '.join(sorted(COLUMN_GROUPS))}. "
            "Use 'core' for a quick-analysis shortcut (question, answer, error_message, "
            "account_id, conv_question, vote, response_time_ms). "
            "Default: all"
        ),
    )

    # -- Output --
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "parquet", "both"],
        default="json",
        help="Output file format. Default: json",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help=(
            "Output file path (without extension). "
            "Default: iba_conversations_<period>_<YYYYMMDD_HHMM>"
        ),
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (indent=2).",
    )

    # -- Filters --
    parser.add_argument("--domain", metavar="DOMAIN_ID", help="Filter by domain_id.")
    parser.add_argument("--platform", metavar="PLATFORM", help="Filter by platform (e.g. web).")

    # -- DB connection --
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"DB host. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"DB port. Default: {DEFAULT_PORT}")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Database name. Default: {DEFAULT_DB}")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"DB user. Default: {DEFAULT_USER}")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="DB password.")

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Validation & resolution
# ---------------------------------------------------------------------------

def resolve_date_range(args: argparse.Namespace) -> DateRange:
    """Compute the date_from / date_to window from CLI arguments.

    Args:
        args: Parsed argparse namespace with period, yesterday,
              date_from, and date_to fields.

    Returns:
        A frozen DateRange with UTC-aware datetime bounds.

    Raises:
        DateRangeError: If no date range flag is supplied, if --period
                        format is invalid, or if date_from >= date_to.
    """
    now = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    if args.period:
        match = re.fullmatch(r"(\d+)d", args.period)
        if not match:
            raise DateRangeError(
                f"Invalid --period format '{args.period}'. Expected format: Nd (e.g. 1d, 30d)."
            )
        days = int(match.group(1))
        if days <= 0:
            raise DateRangeError("--period must be a positive number of days.")
        date_from = now - timedelta(days=days)
        date_to = now + timedelta(days=1)
        return DateRange(date_from=date_from, date_to=date_to)

    if args.yesterday:
        yesterday = now - timedelta(days=1)
        return DateRange(date_from=yesterday, date_to=now)

    if args.date_from:
        try:
            date_from = datetime.fromisoformat(args.date_from).replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise DateRangeError(f"Invalid --from date '{args.date_from}': {exc}") from exc

        if args.date_to:
            try:
                date_to = datetime.fromisoformat(args.date_to).replace(tzinfo=timezone.utc)
            except ValueError as exc:
                raise DateRangeError(f"Invalid --to date '{args.date_to}': {exc}") from exc
        else:
            date_to = now + timedelta(days=1)

        if date_from >= date_to:
            raise DateRangeError(
                f"--from ({args.date_from}) must be earlier than --to ({args.date_to})."
            )
        return DateRange(date_from=date_from, date_to=date_to)

    raise DateRangeError(
        "No date range specified. Use --period Nd, --yesterday, or --from YYYY-MM-DD."
    )


def resolve_columns(columns_arg: str) -> list[str]:
    """Expand the --columns argument into a flat list of SQL column expressions.

    Args:
        columns_arg: Comma-separated group names (e.g. "messages,vote,time")
                     or "all" for every group.

    Returns:
        Flat list of SQL column strings, deduplicated, preserving order.

    Raises:
        ColumnGroupError: If any group name is not in VALID_GROUPS.
    """
    requested = [g.strip().lower() for g in columns_arg.split(",")]
    unknown = [g for g in requested if g not in VALID_GROUPS]
    if unknown:
        raise ColumnGroupError(
            f"Unknown column group(s): {', '.join(unknown)}. "
            f"Valid groups: {', '.join(sorted(VALID_GROUPS))}."
        )

    if "all" in requested:
        groups = list(COLUMN_GROUPS.keys())
    else:
        groups = requested

    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for col in COLUMN_GROUPS[group]:
            if col not in seen:
                seen.add(col)
                result.append(col)

    return result


def build_output_path(args: argparse.Namespace, date_range: DateRange) -> str:
    """Construct the output file path stem (without extension).

    Args:
        args: Parsed CLI arguments (may contain --output override).
        date_range: Resolved date range used to build the default name.

    Returns:
        File path stem string (no extension).
    """
    if args.output:
        return args.output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"iba_conversations_{date_range.label()}_{timestamp}"


def build_db_url(args: argparse.Namespace) -> str:
    """Compose the PostgreSQL connection URL from CLI/env arguments.

    Args:
        args: Parsed CLI arguments with host, port, db, user, password.

    Returns:
        A psycopg-compatible connection URL string.

    Raises:
        DBConnectionError: If password is empty.
    """
    if not args.password:
        raise DBConnectionError(
            "DB password is required. Set IBA_DB_PASSWORD env var or use --password."
        )
    return (
        f"postgresql://{args.user}:{args.password}"
        f"@{args.host}:{args.port}/{args.db}"
    )


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def connect_db(db_url: str) -> duckdb.DuckDBPyConnection:
    """Attach the iba_service PostgreSQL database via DuckDB.

    Args:
        db_url: Full PostgreSQL connection URL.

    Returns:
        Open DuckDB connection with `iba` schema attached.

    Raises:
        DBConnectionError: If the connection or extension load fails.
    """
    try:
        con = duckdb.connect()
        con.execute("INSTALL postgres; LOAD postgres;")
        con.execute(f"ATTACH '{db_url}' AS iba (TYPE POSTGRES, READ_ONLY)")
        return con
    except Exception as exc:
        raise DBConnectionError(f"Cannot connect to database: {exc}") from exc


def build_sql(
    columns: list[str],
    date_range: DateRange,
    domain_id: str | None,
    platform: str | None,
) -> tuple[str, dict[str, Any]]:
    """Build the export SELECT statement and its parameter dict.

    Args:
        columns: SQL column expressions to SELECT (from resolve_columns).
        date_range: UTC-aware date window for the WHERE clause.
        domain_id: Optional domain_id filter value.
        platform: Optional platform filter value (applied to messages.platform).

    Returns:
        Tuple of (sql_string, params_dict) ready for duckdb execute().
    """
    select_cols = ",\n    ".join(ALWAYS_INCLUDED + columns)

    where_clauses = [
        "m.created_at >= $date_from",
        "m.created_at <  $date_to",
    ]
    params: dict[str, Any] = {
        "date_from": date_range.date_from.isoformat(),
        "date_to": date_range.date_to.isoformat(),
    }

    if domain_id:
        where_clauses.append("c.domain_id = $domain_id")
        params["domain_id"] = domain_id

    if platform:
        where_clauses.append("m.platform = $platform")
        params["platform"] = platform

    where = "\n  AND ".join(where_clauses)

    sql = f"""
SELECT
    {select_cols}
FROM iba.public.messages m
JOIN iba.public.conversations c ON c.id = m.conversation_id
LEFT JOIN iba.public.domains d ON d.id = c.domain_id
WHERE {where}
ORDER BY c.created_at ASC, m.created_at ASC
"""
    return sql.strip(), params


def fetch_rows(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute the query and return all rows as a list of dicts.

    Args:
        con: Open DuckDB connection with iba schema attached.
        sql: SELECT statement with $param placeholders.
        params: Parameter dict matching placeholders in sql.

    Returns:
        List of row dicts. Empty list if no rows found.

    Raises:
        DBConnectionError: If the query execution fails.
    """
    try:
        result = con.execute(sql, params)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as exc:
        raise DBConnectionError(f"Query failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Data shaping
# ---------------------------------------------------------------------------

def _is_conv_field(key: str) -> bool:
    """Return True if a field belongs to the conversation (not message) level."""
    return key == "conversation_id" or key.startswith(CONV_FIELD_PREFIXES)


def group_by_conversation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reshape flat rows (one per message) into a nested conversation structure.

    Each conversation object contains a `messages` list. Conversation-level
    fields (conversation_id, conv_*, account_id, domain_id, etc.) are lifted
    to the top level; message-level fields are kept inside each message dict.

    Args:
        rows: Flat list of dicts, one per message, from fetch_rows().

    Returns:
        List of conversation dicts, each with a `messages` key containing
        the ordered list of message dicts for that conversation.
    """
    conv_map: dict[str, dict[str, Any]] = {}
    conv_order: list[str] = []

    for row in rows:
        conv_id = row["conversation_id"]

        if conv_id not in conv_map:
            conv_fields = {k: v for k, v in row.items() if _is_conv_field(k)}
            conv_map[conv_id] = {**conv_fields, "messages": []}
            conv_order.append(conv_id)

        msg_fields = {k: v for k, v in row.items() if not _is_conv_field(k)}
        conv_map[conv_id]["messages"].append(msg_fields)

    return [conv_map[cid] for cid in conv_order]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """JSON serializer for types not handled by the default encoder.

    Args:
        obj: Object to serialize.

    Returns:
        JSON-compatible representation.

    Raises:
        TypeError: If the type is not handled.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable.")


def write_json(
    conversations: list[dict[str, Any]],
    path: str,
    pretty: bool = False,
) -> None:
    """Write nested conversation data to a JSON file.

    Args:
        conversations: Grouped conversation list from group_by_conversation().
        path: Output file path (with .json extension).
        pretty: If True, indent output with 2 spaces.
    """
    indent = 2 if pretty else None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(conversations, fh, default=_serialize, indent=indent, ensure_ascii=False)


def write_parquet(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: dict[str, Any],
    path: str,
) -> None:
    """Write flat query results directly to a Parquet file via DuckDB COPY.

    Avoids loading all rows into Python — DuckDB streams directly to disk.

    Args:
        con: Open DuckDB connection.
        sql: SELECT statement used for the export.
        params: Parameter dict for the SELECT statement.
        path: Output file path (with .parquet extension).
    """
    copy_sql = f"COPY ({sql}) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    con.execute(copy_sql, params)


# ---------------------------------------------------------------------------
# Output summary
# ---------------------------------------------------------------------------

def print_summary(
    conversations: list[dict[str, Any]],
    total_messages: int,
    date_range: DateRange,
    output_format: str,
    output_stem: str,
) -> None:
    """Print a summary of the export to stdout.

    Args:
        conversations: Grouped conversation list (for conversation count).
        total_messages: Total message row count.
        date_range: The resolved date range used for the query.
        output_format: One of 'json', 'parquet', 'both'.
        output_stem: Base output path without extension.
    """
    print("\n── Export Summary ──────────────────────────────────")
    print(f"  Date range    : {date_range.date_from.date()} → {date_range.date_to.date()}")
    print(f"  Conversations : {len(conversations):,}")
    print(f"  Messages      : {total_messages:,}")
    if output_format in ("json", "both"):
        print(f"  JSON output   : {output_stem}.json")
    if output_format in ("parquet", "both"):
        print(f"  Parquet output: {output_stem}.parquet")
    print("────────────────────────────────────────────────────\n")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Orchestrate the export: parse args → query → shape → write → summarize.

    Raises:
        SystemExit: On any ExportError, prints the error and exits with code 1.
    """
    args = parse_args()

    try:
        date_range = resolve_date_range(args)
        columns = resolve_columns(args.columns)
        db_url = build_db_url(args)
        output_stem = build_output_path(args, date_range)

        print(f"Connecting to {args.host}:{args.port}/{args.db} …")
        con = connect_db(db_url)

        print(
            f"Querying messages from {date_range.date_from.date()} "
            f"to {date_range.date_to.date()} …"
        )
        sql, params = build_sql(
            columns=columns,
            date_range=date_range,
            domain_id=args.domain,
            platform=args.platform,
        )

        rows = fetch_rows(con, sql, params)

        if not rows:
            print("⚠  Warning: query returned 0 rows. No output files written.")
            return

        conversations = group_by_conversation(rows)

        if args.output_format in ("json", "both"):
            json_path = f"{output_stem}.json"
            print(f"Writing JSON → {json_path} …")
            write_json(conversations, json_path, pretty=args.pretty)

        if args.output_format in ("parquet", "both"):
            parquet_path = f"{output_stem}.parquet"
            print(f"Writing Parquet → {parquet_path} …")
            write_parquet(con, sql, params, parquet_path)

        con.close()

        print_summary(
            conversations=conversations,
            total_messages=len(rows),
            date_range=date_range,
            output_format=args.output_format,
            output_stem=output_stem,
        )

    except ExportError as exc:
        print(f"\n✗ Export failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
