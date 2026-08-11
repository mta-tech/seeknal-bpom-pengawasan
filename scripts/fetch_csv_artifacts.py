"""Fetch CSV artifacts uploaded during a test_variant_compare.py run and save
them physically next to that run's trace files, correctly attributed to the
exact scenario/turn that produced each one.

test_variant_compare.py's upload_to_s3 calls land in the remote SeaweedFS
bucket only (via iba-storage's presigned-PUT flow) -- there is no local copy.
This companion script closes that gap for local Docker testing.

v1 of this script matched purely by TIME WINDOW (every bucket object created
in the N minutes before the run folder's own save timestamp was assumed to
belong to that run). That is unsound: two runs launched close together in
time have heavily overlapping windows, so an ENTIRE unrelated run's files
bleed into this run's csv/ folder (confirmed empirically -- see
docs/planning/2026-07-21-forecast-e2e-round2-deepdive.md, a run only ~100s
after an 18-scenario batch picked up all 18 of that batch's files too).

v2 instead reads the run's own _data.json (the machine-readable trace every
test_variant_compare.py run already writes), which records the exact prompt
text and full tool_trace for every turn. iba-storage renames each upload to
slugify(question)[:60] + '-' + upload timestamp, with no run/scenario id
embedded -- so this script recomputes that same slug from each turn's own
recorded prompt and matches it against bucket object names by a 50-char
prefix (safely below the 60-char truncation boundary, so exact
truncation/word-boundary differences don't matter). This attributes files by
CONTENT (which question produced them), not by wall-clock proximity, so it
is immune to adjacent/overlapping runs.

If a single turn made more than one upload_to_s3 call (the known duplicate-
upload bug -- see finding #2 in the deep-dive doc above), the matching bucket
objects for that slug are assigned in ascending Mtime order to that turn's
upload_to_s3 calls in trace order, and saved with an explicit
`_upload1of2`/`_upload2of2` suffix so the duplicate is visible in the
filename itself instead of silently colliding or overwriting.

A generous +/- window_hours bucket-scan window is still used, but only as a
coarse safety net against scanning the entire bucket history / matching a
coincidentally similar prompt from a much older run -- it is NOT the
attribution mechanism anymore, so its exact width no longer affects
correctness, only how far back the scan bothers to look.

Prerequisites -- what has to be running, and why (verified against this
machine's actual `docker ps` / `ps aux`, not assumed):

1. Docker stack in the sibling `iba` monorepo checkout
   (/home/mta/projects/seeknal_audit/iba/), providing local SeaweedFS +
   iba-storage + iba-engine:

       cd /home/mta/projects/seeknal_audit/iba
       make up          # `docker compose up -d`, full stack incl. profile "all"
                          # (iba-storage / iba-engine only start under that profile)

   This script itself only needs ONE of those containers reachable --
   `iba-seaweedfs-filer`, published on host port 6702 (FILER_URL below).
   Sanity check: `docker ps --filter name=iba-seaweedfs-filer` should show
   it Up (the SeaweedFS containers report "(unhealthy)" in `docker ps` on
   this stack even when serving requests fine -- that's a healthcheck
   config quirk, not a real outage; judge by whether requests succeed, not
   by the health column). `iba-storage` (port 6002) and `iba-engine` (port
   6705) are what test_variant_compare.py itself talks to during the run
   that produces the CSVs -- not needed for THIS script, only for the run
   that came before it.

2. A separate SSH tunnel to the real BPOM warehouse database, unrelated to
   the Docker stack above and NOT required by this script -- only by the
   test_variant_compare.py run that generated the run_dir you're fetching
   for (execute_sql / run_forecast tool calls need it live at the time the
   scenarios actually run):

       ssh -L 5533:localhost:5433 cbnpom@10.59.2.29

   Kept open in its own terminal/session for the duration of the test run;
   `IBA_DATABASE_DSN` in the harness's env then points at
   postgresql://...@localhost:5533/rpo_v2. If this tunnel drops mid-batch,
   affected scenarios fail fast with elapsed_s~=10s / llm_requests=0 /
   ConnectError in their trace -- that data is unusable and should be
   re-run, not fetched (see docs/planning/2026-07-21-forecast-e2e-round2-deepdive.md
   §0 for a real instance of this).

Typical order of operations: (1) `make up` in the iba repo, (2) open the DB
SSH tunnel, (3) run test_variant_compare.py to completion (writes _data.json
and uploads CSVs via iba-storage's presigned-PUT flow), (4) run this script
against that run's output folder -- step 4 only needs the Docker stack from
step 1 still up; the SSH tunnel from step 2 can be closed by then, since this
script never touches the database, only the SeaweedFS filer.

Usage:
    uv run python scripts/fetch_csv_artifacts.py <run_dir> [window_hours]
    uv run python scripts/fetch_csv_artifacts.py seeknal/tests/outputs/2026-07-20/v6-after-finding-compact/20260720_214322
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

FILER_URL = "http://localhost:6702"
BUCKET = "iba-storage"
PREFIX = "csv-exports"
SLUG_PREFIX_LEN = 50  # below the storage service's 60-char slug truncation boundary

_OBJ_RE = re.compile(r"^(?P<slug>.+)-\d{8}-\d{6}\.csv$")


def _slugify(text: str, maxlen: int = 60) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:maxlen]


def _forecast_table(arg: str) -> str:
    """Table slug embedded in ``forecast-combined-{table}-{ts}.csv`` names.

    Mirrors ``forecast.py::_derive_forecast_filename`` so a run_forecast tool
    call in the trace can be matched to the combined CSV it self-uploaded.
    """
    table = "forecast"
    m = re.search(r"\bFROM\s+([\w.]+)", arg, re.IGNORECASE)
    if m:
        table = m.group(1).strip("`\"'").split(".")[-1].lower()
        table = re.sub(r"^(t_|tbl_|table_|ft_)", "", table) or "forecast"
    return table


def _run_anchor_utc(run_dir: Path) -> datetime:
    # Folder name: YYYYMMDD_HHMMSS, UTC (test_variant_compare.py convention).
    # Captured at output-SAVE time, i.e. AFTER all of this run's own uploads.
    return datetime.strptime(run_dir.name, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)


def _run_span_seconds(data_json: Path) -> float:
    """Total agent execution time of the run (sum of every turn's elapsed_s).

    Used to bound the table-named forecast-combined-* files to THIS run's own
    execution span — a refused/failed forecast produces no file in its span, and
    a neighbouring sequential run's file falls outside it, so neither is
    mis-attributed here.
    """
    try:
        d = json.loads(data_json.read_text(encoding="utf-8"))
    except Exception:
        return 0.0
    total = 0.0
    for sc in d.get("scenarios", {}).values():
        for turn in sc.get("turns", []):
            total += float(turn.get("elapsed_s") or 0.0)
    return total


def _list_bucket_entries() -> list[dict]:
    resp = httpx.get(
        f"{FILER_URL}/buckets/{BUCKET}/{PREFIX}/",
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("Entries", [])


def _list_folder(uuid_path: str) -> list[dict]:
    resp = httpx.get(
        f"{FILER_URL}{uuid_path}/",
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("Entries", [])


def _bucket_objects(anchor: datetime, window_hours: float) -> list[tuple[str, str, str]]:
    """Return (full_path, mtime_iso, slug) for every bucket object in the coarse window."""
    start = anchor - timedelta(hours=window_hours)
    # The run folder is saved AFTER this run's own uploads, so they all fall
    # BEFORE the anchor. Keep only a tiny same-host clock-skew slack — a larger
    # forward window would catch the NEXT sequential run's uploads (they share
    # the table-named forecast-combined-* slug), mis-attributing them here.
    end = anchor + timedelta(seconds=15)
    out: list[tuple[str, str, str]] = []
    for e in _list_bucket_entries():
        for f in _list_folder(e["FullPath"]):
            mtime = datetime.fromisoformat(f["Mtime"].replace("Z", "+00:00"))
            if not (start <= mtime <= end):
                continue
            fname = f["FullPath"].rsplit("/", 1)[-1]
            m = _OBJ_RE.match(fname)
            slug = m.group("slug") if m else fname
            out.append((f["FullPath"], f["Mtime"], slug))
    return out


def _expected_uploads(data_json: Path) -> list[dict]:
    """Walk one variant's _data.json in execution order; one entry per
    upload_to_s3 tool call, carrying scenario/turn attribution."""
    d = json.loads(data_json.read_text(encoding="utf-8"))
    expected: list[dict] = []
    for scenario_id, sc in d.get("scenarios", {}).items():
        for turn in sc.get("turns", []):
            prompt = turn.get("prompt", "")
            slug = _slugify(prompt)
            trace = turn.get("tool_trace", [])
            # (a) Agent's explicit upload_to_s3 calls — matched by question slug.
            uploads_this_turn = [t for t in trace if t.get("tool") == "upload_to_s3"]
            for i, t in enumerate(uploads_this_turn, start=1):
                expected.append(
                    {
                        "scenario_id": scenario_id,
                        "turn_num": turn.get("turn_num"),
                        "prompt": prompt,
                        "slug": slug,
                        "upload_index": i,
                        "upload_count": len(uploads_this_turn),
                        "tool_arg": t.get("arg", ""),
                        "at_s": t.get("at_s"),
                    }
                )
            # (b) run_forecast self-uploads ONE combined CSV per SUCCESSFUL call,
            # named forecast-combined-{table}-{ts}.csv (see forecast.py). The agent
            # commonly calls it twice (unqualified-table DRAFT that FAILS → schema-
            # qualified CORRECTED that succeeds); only the successful one uploads,
            # and both share the same table. So expect ONE combined CSV per DISTINCT
            # table per turn (avoids over-counting the failed draft). Matched by the
            # table-derived name. (Rare multi-series-same-table questions may under-
            # count; documented limitation.)
            tables: list[str] = []
            for t in trace:
                if t.get("tool") == "run_forecast":
                    tbl = _forecast_table(t.get("arg", ""))
                    if tbl not in tables:
                        tables.append(tbl)
            for tbl in tables:
                expected.append(
                    {
                        "scenario_id": scenario_id,
                        "turn_num": turn.get("turn_num"),
                        "prompt": prompt,
                        "slug": f"forecast-combined-{tbl}",
                        "upload_index": 1,
                        "upload_count": 1,
                        "tool_arg": "",
                        "at_s": None,
                    }
                )
    return expected


def _process_variant(vdir: Path, objects: list[tuple[str, str, str]], anchor: datetime) -> None:
    expected = _expected_uploads(vdir / "_data.json")
    if not expected:
        print(f"[{vdir.name}] tidak ada upload_to_s3 / run_forecast di trace -- tidak ada yang diambil.")
        return

    # forecast-combined-* files are TABLE-named (shared slug across runs). Bound
    # them to THIS run's own execution span so a refused forecast (no file in
    # span) or a neighbouring sequential run's file isn't grabbed. run_start ≈
    # anchor(save) − agent_elapsed − 5s. Question-slug uploads are unique enough
    # to skip this bound.
    run_start = anchor - timedelta(seconds=_run_span_seconds(vdir / "_data.json") + 5)

    out_dir = vdir / "csv"
    if out_dir.exists():
        for f in out_dir.glob("*.csv"):
            f.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group expected uploads by slug prefix so same-slug duplicates (either a
    # genuine double-upload bug within one turn, or two different turns that
    # happen to ask the exact same question) pair against candidates in the
    # same relative order on both sides.
    groups: dict[str, list[dict]] = {}
    for item in expected:
        groups.setdefault(item["slug"][:SLUG_PREFIX_LEN], []).append(item)

    saved = 0
    unmatched: list[dict] = []
    for prefix, items in groups.items():
        cands = [o for o in objects if o[2][:SLUG_PREFIX_LEN] == prefix]
        if prefix.startswith("forecast-combined-"):
            cands = [o for o in cands
                     if datetime.fromisoformat(o[1].replace("Z", "+00:00")) >= run_start]
        candidates = sorted(cands, key=lambda o: o[1])
        # A run's OWN uploads are the MOST RECENT for a given slug; older
        # same-slug files from earlier runs also land in the coarse ±window
        # (esp. table-named forecast-combined-* files), so keep the last
        # len(items) candidates (closest to this run's save time), assigned in
        # chronological order to the trace's calls.
        if len(candidates) > len(items):
            candidates = candidates[-len(items):]
        for i, item in enumerate(items):
            if i >= len(candidates):
                unmatched.append(item)
                continue
            obj_path, mtime, _ = candidates[i]
            fname = obj_path.rsplit("/", 1)[-1]
            suffix = (
                f"_upload{item['upload_index']}of{item['upload_count']}"
                if item["upload_count"] > 1
                else ""
            )
            dest = out_dir / f"{item['scenario_id']}__T{item['turn_num']}{suffix}__{fname}"
            r = httpx.get(f"{FILER_URL}{obj_path}", timeout=30)
            r.raise_for_status()
            dest.write_bytes(r.content)
            print(f"  [OK] {item['scenario_id']} T{item['turn_num']} ({mtime}) -> {dest.name}")
            saved += 1

    print(f"[{vdir.name}] {saved}/{len(expected)} CSV tersimpan -> {out_dir}")
    if unmatched:
        print(f"  PERINGATAN: {len(unmatched)} upload_to_s3 di trace TIDAK ketemu file cocok di bucket "
              f"(coba perbesar window_hours jika run ini lebih lama dari window default):")
        for u in unmatched:
            print(f"    - {u['scenario_id']} T{u['turn_num']}: prompt={u['prompt']!r}")


def main(run_dir_str: str, window_hours: float = 6.0) -> None:
    run_dir = Path(run_dir_str)
    if not run_dir.is_dir():
        print(f"Run dir not found: {run_dir}")
        sys.exit(1)

    anchor = _run_anchor_utc(run_dir)
    objects = _bucket_objects(anchor, window_hours)
    print(f"Coarse bucket scan: {len(objects)} objek dalam +/-{window_hours}j sekitar {anchor.isoformat()} "
          f"(hanya penyaring kasar -- atribusi sebenarnya pakai slug pertanyaan dari _data.json)")

    variant_dirs = [p for p in run_dir.iterdir() if p.is_dir() and (p / "_data.json").exists()]
    if not variant_dirs:
        print(f"Tidak ada _data.json ditemukan langsung di bawah {run_dir}")
        return

    for vdir in sorted(variant_dirs):
        _process_variant(vdir, objects, anchor)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    win = float(sys.argv[2]) if len(sys.argv) == 3 else 6.0
    main(sys.argv[1], win)
