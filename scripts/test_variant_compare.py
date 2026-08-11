"""
test_variant_compare.py — Jalankan skenario yang sama terhadap beberapa context variant dan bandingkan hasilnya.

Variant adalah snapshot direktori yang berisi kombinasi berbeda dari:
  seeknal_agent.yml / seeknal/skills/ / context/ / SEEKNAL_ASK.md

Disimpan di: docs/context_recap/testing_refactor/<variant-name>/

Setiap variant wajib memiliki (sudah dibuat via symlink sekali saja):
  .env             → symlink ke ../../../../.env
  .seeknal/        → symlink ke ../../../../.seeknal/
  seeknal/skills/  → symlink ke ../skills/

=== MODEL PARALELISME ===

Untuk setiap pertanyaan (scenario), SEMUA variant selalu dijalankan secara paralel.
--workers mengontrol berapa pertanyaan yang jalan bersamaan.

  --workers 1 (default):
    Pertanyaan diproses satu per satu.
    Tapi 4 variant untuk setiap pertanyaan jalan BERSAMAAN.
    Concurrency: 1 × 4 = 4 sesi LLM paralel

  --workers 4:
    4 pertanyaan sekaligus, masing-masing 4 variant.
    Concurrency: 4 × 4 = 16 sesi LLM paralel

=== QUICK START ===

Jalankan satu skenario di semua 4 variant (default: semua test di seeknal/tests/v1):
    uv run python scripts/test_variant_compare.py --scenario UAT-TOTAL-1

Hanya skenario CLARIF di semua variant:
    uv run python scripts/test_variant_compare.py --scenario CLARIF

Jalankan 4 pertanyaan sekaligus × 4 variant = 16 paralel:
    uv run python scripts/test_variant_compare.py --scenario CLARIF --workers 4

Pilih variant tertentu saja:
    uv run python scripts/test_variant_compare.py --scenario CLARIF-BAYI-1 \\
        --variants after-refactor-f8d34b0,after-refactor-f8d34b0-notsystemprompt

Singleturn UAT test (auto-clarif aktif by default):
    uv run python scripts/test_variant_compare.py \\
        --test-path seeknal/tests/v1/singleturn/UAT --scenario UAT-TOTAL-1

Matikan auto-clarif (agent berhenti di pertanyaan klarifikasi):
    uv run python scripts/test_variant_compare.py --scenario CLARIF --no-auto-clarif

    uv run python  scripts/test_variant_compare.py --variants-path docs/context_recap/after-anomaly --test-path seeknal/tests/v1/singleturn/UAT-v2/UAT-v2-compact-II --workers 1 --timeout 330
    uv run python  scripts/test_variant_compare.py --variants-path docs/context_recap/after-chart-030826 --variants after-forecast-chart --test-path seeknal/tests/v1/singleturn/UAT-v2-compact-V --scenario UAT-KOMITMEN-PROSES-1 --workers 1 --timeout 400
    uv run python  scripts/test_variant_compare.py --variants-path docs/context_recap/after-chart-route --variants route-context-070826-v2 --test-path seeknal/tests/v1/singleturn/UAT-v2-compact-V --scenario UAT-KOMITMEN-PROSES-1 --workers 1 --timeout 400

=== VARIANT MATRIX ===

Variant di docs/context_recap/testing_refactor/:

  pre-refactor-1dd55d9                  skills/context LAMA + config LAMA (tanpa workflow:false)
  pre-refactor-1dd55d9-notsystemprompt  skills/context LAMA + config BARU (workflow:false + custom)
  after-refactor-f8d34b0               skills/context BARU + config LAMA
  after-refactor-f8d34b0-notsystemprompt  skills/context BARU + config BARU  ← expected PASS

Matrix:
                        config LAMA       config BARU
  skills LAMA           pre               pre-newsys
  skills BARU           after             after-newsys  ← target

=== OUTPUT ===

  1. Log per-skenario per-variant (turn detail, SQL, clarif count)
     → tampil setelah semua variant selesai per pertanyaan
  2. Tabel perbandingan side-by-side di akhir (SCENARIO × VARIANT)
  3. JSON: seeknal/tests/outputs/<YYYY-MM-DD>/v2/variant_compare_results_<ts>.json
     Format sama dengan multiturn_results_*.json (v1) + dimensi variant per scenario.

=== AUTO-CLARIF (aktif by default) ===

Ketika agent memanggil request_clarification, script otomatis:
  1. Membaca opsi dari pending_clarification
  2. Memilih opsi dengan recommended:true (fallback: options[0] + WARNING log)
  3. Mencatat turn klarifikasi (feedback agen, clarif=1 terlihat di log)
  4. Inject label opsi terpilih sebagai turn [AUTO]
  5. Menjalankan agent lagi → jawaban akhir tertangkap di turn [AUTO]

Hasilnya di JSON:
  turn {prompt: "pertanyaan asal", ask_user_calls: 1, answer: "<teks klarifikasi>"}
  turn {prompt: "[AUTO] opsi terpilih",  is_auto_clarif: true,  answer: "<jawaban akhir>"}

Gunakan --no-auto-clarif untuk mematikan dan melihat agen berhenti di klarifikasi.

=== PREREQUISITES ===

1. SSH tunnel ke database warehouse HARUS aktif (WAREHOUSE_URL di .env). Ini
   TERPISAH dari stack Docker di poin 2 -- database aslinya remote, contoh
   tunnel yang dipakai di mesin ini:
       ssh -L 5533:localhost:5433 cbnpom@10.59.2.29
   Kalau tunnel putus di tengah batch, skenario yang kena tampil di trace
   dengan elapsed_s~=10s / llm_requests=0 / ConnectError -- data itu TIDAK
   valid untuk dianalisis, harus dijalankan ulang, bukan dipakai apa adanya.

2. Stack Docker (iba-engine + iba-storage + SeaweedFS) HARUS aktif -- setiap
   skenario yang forecast/upload (hampir semua di seeknal/tests/v1) memanggil
   run_forecast (butuh IBA_ENGINE_URL -> iba-engine, port 6705) dan
   upload_to_s3 (butuh IBA_STORAGE_URL -> iba-storage, port 6002; keduanya
   lewat SeaweedFS filer di port 6702). Nyalakan dari repo `iba` (sibling
   checkout, BUKAN seeknal-bpom-neo):
       cd ../iba && make up      # docker compose up -d, full stack profile "all"
   Cek: `docker ps --filter name=iba-engine --filter name=iba-storage
   --filter name=iba-seaweedfs-filer` harus ketiganya Up (SeaweedFS sering
   tampil "(unhealthy)" di kolom health walau tetap melayani request dengan
   benar -- itu quirk healthcheck config, bukan indikasi stack mati).

3. Jalankan dari root project seeknal-bpom-neo/:
   cd seeknal-bpom-neo && uv run python scripts/test_variant_compare.py [args]
4. Symlink .env, .seeknal, seeknal/skills sudah ada di setiap variant dir (setup sekali)

=== CONTOH NYATA: MENJALANKAN SATU BATCH TESTCASE ===

Variant yang dipakai untuk audit round1/round2 BPOM (2026-07-20) BUKAN salah
satu dari docs/context_recap/testing_refactor/ (default), melainkan config
deployment nyata yang git-tracked & bind-mounted ke container seeknal-worker:
    ../iba-deploy-runbook/configs/seeknal-project/
(direktori ini punya seeknal_agent.yml langsung di dalamnya, jadi
--variants-path harus menunjuk ke PARENT-nya, yaitu ../iba-deploy-runbook/configs
-- variant yang ditemukan lalu bernama "seeknal-project", persis seperti yang
muncul di seeknal/tests/outputs/.../seeknal-project/).

Batch QA singleturn (18 skenario, termasuk QA-C4/QA-C7/HORIZON-*):
    uv run python scripts/test_variant_compare.py \\
        --variants-path ../iba-deploy-runbook/configs \\
        --test-path seeknal/tests/v1/singleturn/UAT-forecast-qa \\
        --workers 1

Satu skenario multiturn saja (QA-C8, disambiguasi query vs forecast):
    uv run python scripts/test_variant_compare.py \\
        --variants-path ../iba-deploy-runbook/configs \\
        --test-path seeknal/tests/v1/multiturn \\
        --scenario QA-C8

Batch forecast/ (FC-BTP-*, FC-ERBA-*, FC-RISIKO-*):
    uv run python scripts/test_variant_compare.py \\
        --variants-path ../iba-deploy-runbook/configs \\
        --test-path seeknal/tests/v1/singleturn/forecast \\
        --workers 1

Setelah run selesai, output-nya ada di
seeknal/tests/outputs/<YYYY-MM-DD>/<SEEKNAL_TEST_OUTPUT_VERSION dari .env>/<run_ts>/
(mis. v6-after-finding-compact/20260720_214143/seeknal-project/). Untuk
mengambil CSV yang di-upload_to_s3 selama run itu (bukan cuma trace-nya),
lanjutkan dengan scripts/fetch_csv_artifacts.py <run_dir> -- lihat docstring
skrip itu untuk detail (skrip itu HANYA butuh stack Docker poin 2 di atas
masih aktif, tunnel database di poin 1 boleh sudah ditutup).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml
from urllib.parse import quote as _urlquote

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_VARIANTS_ROOT = PROJECT_ROOT / "docs" / "context_recap" / "testing_refactor"
DEFAULT_TEST_PATH = PROJECT_ROOT / "seeknal" / "tests" / "v1"

sys.path.insert(0, str(PROJECT_ROOT.parent / "seeknal" / "src"))


def _resolve_output_base() -> Path:
    """Output base dir, configurable via `.env` (SEEKNAL_TEST_OUTPUT_DIR).

    Default keeps the historical location. A relative value is resolved against
    PROJECT_ROOT so `.env` can stay path-portable. Read lazily (at save time)
    so it picks up `.env` loaded during the run.
    """
    raw = os.environ.get("SEEKNAL_TEST_OUTPUT_DIR", "").strip()
    if not raw:
        return PROJECT_ROOT / "seeknal" / "tests" / "outputs"
    p = Path(raw)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


def _output_version() -> str:
    """Version subfolder, configurable via `.env` (SEEKNAL_TEST_OUTPUT_VERSION)."""
    return os.environ.get("SEEKNAL_TEST_OUTPUT_VERSION", "v3").strip() or "v3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("variant-compare")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    prompt: str
    assert_contains: list[str] = field(default_factory=list)
    assert_asked: bool | None = None
    clarif_response: bool = False
    note: str = ""
    assert_any_of: list = field(default_factory=list)  # OR of AND-groups; pass if >=1 group fully matches
    tolerance_pct: float = 0.0  # numeric-token tolerance within assert_any_of groups (%)


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
    llm_requests: int
    tool_calls: int
    sqls: list[str]
    passed: bool
    failures: list[str]
    note: str = ""
    timed_out: bool = False
    ask_user_calls: int = 0
    is_auto_clarif: bool = False
    clarif_slots: list = field(default_factory=list)
    tools: dict = field(default_factory=dict)  # per-tool-name call counts (matches terminal "tool breakdown")
    # Flat chronological ledger of EVERY tool call (root-cause tracing):
    # {step, at_s, tool, arg, origin, result_chars, status} — fixed keys, no nesting.
    tool_trace: list = field(default_factory=list)
    files_read: list = field(default_factory=list)    # paths passed to read_project_file, in order
    skills_loaded: list = field(default_factory=list) # skill names passed to load_skill, in order
    trace_partial: bool = False  # True when the turn aborted before messages returned (trace incomplete)


@dataclass
class ScenarioResult:
    name: str
    scenario_id: str
    turns: list[TurnResult]
    variant_name: str = ""
    # [G7] Status run — membedakan row 0-turn buatan infra dari hasil eksekusi asli:
    #   "completed" = run selesai normal (turns bisa saja gagal assert, itu FAIL biasa)
    #   "timeout"   = subprocess dibunuh parent karena melewati --timeout
    #   "fatal"     = exception sebelum/di luar turn loop (create_agent gagal, dsb.)
    # Pass-rate yang jujur dihitung dari denominator status == "completed".
    status: str = "completed"

    @property
    def passed(self) -> bool:
        # Empty turns = timeout/error producing no results → NOT a pass.
        # Without this guard, all([]) returns True (vacuous truth), making
        # timeouts look like passes.
        if not self.turns:
            return False
        return all(t.passed for t in self.turns)


# ---------------------------------------------------------------------------
# [G7] Serialisasi Scenario/TurnResult/ScenarioResult ↔ dict
#
# Dipakai mode worker-subprocess: parent menulis Scenario ke file JSON, worker
# menjalankannya dan menulis ScenarioResult kembali sebagai JSON. Round-trip
# memakai skema yang sama dengan _turn_to_dict (output besar) supaya tidak ada
# dua format berbeda.
# ---------------------------------------------------------------------------

def _scenario_to_dict(s: "Scenario") -> dict:
    return {
        "name": s.name,
        "scenario_id": s.scenario_id,
        "description": s.description,
        "turns": [
            {
                "prompt": t.prompt,
                "assert_contains": t.assert_contains,
                "assert_asked": t.assert_asked,
                "clarif_response": t.clarif_response,
                "note": t.note,
                "assert_any_of": t.assert_any_of,
                "tolerance_pct": t.tolerance_pct,
            }
            for t in s.turns
        ],
    }


def _scenario_from_dict(d: dict) -> "Scenario":
    return Scenario(
        name=d.get("name", ""),
        scenario_id=d.get("scenario_id", ""),
        description=d.get("description", ""),
        turns=[
            Turn(
                prompt=t["prompt"],
                assert_contains=t.get("assert_contains", []),
                assert_asked=t.get("assert_asked", None),
                clarif_response=t.get("clarif_response", False),
                note=t.get("note", ""),
                assert_any_of=t.get("assert_any_of", []),
                tolerance_pct=float(t.get("tolerance_pct", 0.0) or 0.0),
            )
            for t in d.get("turns", [])
        ],
    )


def _turn_result_from_dict(d: dict) -> "TurnResult":
    """Kebalikan dari _turn_to_dict — rekonstruksi TurnResult dari JSON worker."""
    return TurnResult(
        turn_num=int(d.get("turn_num", 0)),
        prompt=d.get("prompt", ""),
        answer=d.get("answer", ""),
        elapsed_s=float(d.get("elapsed_s", 0.0)),
        llm_requests=int(d.get("llm_requests", 0)),
        tool_calls=int(d.get("tool_calls", 0)),
        sqls=list(d.get("sqls", [])),
        passed=bool(d.get("passed", False)),
        failures=list(d.get("failures", [])),
        note=d.get("note", ""),
        timed_out=bool(d.get("timed_out", False)),
        ask_user_calls=int(d.get("ask_user_calls", 0)),
        is_auto_clarif=bool(d.get("is_auto_clarif", False)),
        clarif_slots=list(d.get("clarif_slots", [])),
        tools=dict(d.get("tools", {})),
        tool_trace=list(d.get("tool_trace", [])),
        files_read=list(d.get("files_read", [])),
        skills_loaded=list(d.get("skills_loaded", [])),
        trace_partial=bool(d.get("trace_partial", False)),
    )


def _scenario_result_to_dict(r: "ScenarioResult") -> dict:
    return {
        "name": r.name,
        "scenario_id": r.scenario_id,
        "variant_name": r.variant_name,
        "status": r.status,
        "turns": [_turn_to_dict(t) for t in r.turns],
    }


def _scenario_result_from_dict(d: dict) -> "ScenarioResult":
    return ScenarioResult(
        name=d.get("name", ""),
        scenario_id=d.get("scenario_id", ""),
        turns=[_turn_result_from_dict(t) for t in d.get("turns", [])],
        variant_name=d.get("variant_name", ""),
        status=d.get("status", "completed"),
    )


# ---------------------------------------------------------------------------
# Assertion matching helpers (assert_any_of + numeric tolerance)
# ---------------------------------------------------------------------------

def _extract_num(s) -> int | None:
    """Parse first integer from a token using Indonesian '.' thousand separator."""
    m = re.search(r"\d[\d\.]*", str(s))
    if not m:
        return None
    try:
        return int(m.group(0).replace(".", ""))
    except ValueError:
        return None


def _token_in_answer(token, answer_lower: str, tolerance_pct: float) -> bool:
    """Match a token against the answer.

    Numeric tokens (>=2 significant digits) use proximity within tolerance_pct.
    Non-numeric tokens use plain case-insensitive substring match.
    tolerance_pct == 0 -> exact substring for everything.
    """
    raw = str(token).replace(".", "")
    is_numeric = bool(re.search(r"\d{2,}", raw))
    tnum = _extract_num(token) if is_numeric else None
    if is_numeric and tolerance_pct and tnum is not None:
        tol = max(1, tnum * tolerance_pct / 100.0)
        for m in re.finditer(r"\d[\d\.]*", answer_lower):
            anum = _extract_num(m.group(0))
            if anum is not None and abs(anum - tnum) <= tol:
                return True
        return False
    return str(token).lower() in answer_lower


def _group_matches(group, answer_lower: str, tolerance_pct: float) -> bool:
    """A group matches when ALL its tokens match (AND within group)."""
    return all(_token_in_answer(tok, answer_lower, tolerance_pct) for tok in group)


def _any_of_matches(any_of, answer_lower: str, tolerance_pct: float) -> bool:
    """assert_any_of passes when at least one group fully matches (OR across groups)."""
    return any(_group_matches(g, answer_lower, tolerance_pct) for g in any_of)


def _normalize_clarification_slots(pending) -> list[dict]:
    """Coerce whatever the model passed to request_clarification into canonical
    slots: [{'question': str, 'options': [{'label', 'description', 'recommended'}]}].

    The tool contract is a LIST OF SLOTS, each slot carrying its own `options`.
    But the model is not deterministic and sometimes flattens it into a LIST OF
    OPTIONS — dicts with `label`/`description`/`recommended` at the root and no
    `options` key at all (observed: SERBUK-DICABUT-1, and KOPI-INSTAN-PENDAFTAR-1
    which sent the correct shape on one run and the flat shape on another). When
    that happens `slot.get('options')` is empty, clarif_slots come out blank, the
    AUTO turn never fires, and the clarification turn slips through as a vacuous
    PASS. Normalize both shapes here so auto-pick works regardless of which one
    the model emitted this run.

    Returns [] when there is genuinely nothing structured to pick from.
    """
    if not pending or not isinstance(pending, (list, tuple)):
        return []

    def _opt(d: dict) -> dict:
        return {
            "label": str(d.get("label", "") or ""),
            "description": str(d.get("description", "") or ""),
            "recommended": str(d.get("recommended", "")).lower() == "true",
        }

    proper_slots = [
        s for s in pending
        if isinstance(s, dict) and isinstance(s.get("options"), (list, tuple)) and s.get("options")
    ]
    if proper_slots:
        # At least one well-formed slot — keep only the well-formed ones.
        return [
            {
                "question": str(s.get("question", "") or ""),
                "options": [_opt(o) for o in s["options"] if isinstance(o, dict)],
            }
            for s in proper_slots
        ]

    # No slot carried options. If the elements themselves look like options
    # (have a label), treat the whole list as ONE slot's option set.
    flat_opts = [_opt(s) for s in pending if isinstance(s, dict) and s.get("label")]
    if flat_opts:
        return [{"question": "", "options": flat_opts}]

    return []


# ---------------------------------------------------------------------------
# YAML Loader
# ---------------------------------------------------------------------------

def _load_yaml_tests(path: Path) -> list[Scenario]:
    if not path.is_dir():
        log.error("Path not found: %s", path)
        sys.exit(1)

    yml_files = sorted(path.rglob("*.yml"))
    if not yml_files:
        log.error("No .yml files in %s", path)
        sys.exit(1)

    scenarios: list[Scenario] = []
    for yml_file in yml_files:
        with open(yml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "turns" not in data:
            continue
        turns = [
            Turn(
                prompt=t["prompt"],
                assert_contains=t.get("assert_contains", []),
                assert_asked=t.get("assert_asked", None),
                clarif_response=t.get("clarif_response", False),
                note=t.get("note", ""),
                assert_any_of=t.get("assert_any_of", []),
                tolerance_pct=float(t.get("tolerance_pct", 0.0) or 0.0),
            )
            for t in data["turns"]
            if "prompt" in t
        ]
        if not turns:
            continue
        scenarios.append(Scenario(
            name=data.get("name", yml_file.stem),
            scenario_id=data.get("scenario_id", yml_file.stem),
            description=data.get("description", ""),
            turns=turns,
        ))

    log.info("Loaded %d scenario(s) from %s", len(scenarios), path)
    return scenarios


def _filter_scenarios(scenarios: list[Scenario], select: str | None) -> list[Scenario]:
    if not select:
        return scenarios
    select_lower = select.lower()
    filtered = [
        s for s in scenarios
        if select_lower in s.name.lower() or select_lower in s.scenario_id.lower()
    ]
    if not filtered:
        log.warning("No scenarios matched filter: '%s'", select)
    return filtered


# ---------------------------------------------------------------------------
# Variant Discovery
# ---------------------------------------------------------------------------

def _discover_variants(variants_root: Path) -> list[Path]:
    if not variants_root.is_dir():
        log.error("Variants root not found: %s", variants_root)
        sys.exit(1)
    return sorted(
        d for d in variants_root.iterdir()
        if d.is_dir() and (d / "seeknal_agent.yml").exists()
    )


def _select_variants(all_variants: list[Path], names: list[str] | None) -> list[Path]:
    if not names:
        return all_variants
    result = []
    for name in names:
        matches = [v for v in all_variants if name.lower() in v.name.lower()]
        if not matches:
            log.warning("Variant '%s' not found — skip", name)
        result.extend(matches)
    return result


# ---------------------------------------------------------------------------
# Core runner: satu scenario × satu variant
# ---------------------------------------------------------------------------

def _extract_sqls(messages) -> list[str]:
    """Extract SQL statements executed by the agent across all SQL-capable tools.

    Captures: execute_sql (args: sql or query), preview_query (args: sql or
    query), execute_sql_pair (args: slug or authorative). This ensures SQL
    executed via any tool variant is recorded, not just execute_sql.
    """
    from pydantic_ai.messages import ToolCallPart
    _SQL_TOOLS = {"execute_sql", "preview_query"}
    sqls = []
    for m in messages:
        for p in getattr(m, "parts", []):
            if not isinstance(p, ToolCallPart):
                continue
            # [FIX provider-args] Versi lama membuang args string → SQL hilang
            # saat provider OpenAI-compatible (OpenRouter) dipakai:
            # args = p.args if isinstance(p.args, dict) else {}
            args = _tool_call_args_dict(p.args)
            if p.tool_name in _SQL_TOOLS:
                sql = (args.get("sql") or args.get("query") or "").strip()
                if sql:
                    sqls.append(sql)
            elif p.tool_name == "execute_sql_pair":
                slug = args.get("slug", "")
                if slug:
                    sqls.append(f"[execute_sql_pair: {slug}]")
    return sqls


def _tool_call_args_dict(args) -> dict:
    """[FIX provider-args] Normalisasi `ToolCallPart.args` menjadi dict.

    Bentuk args TERGANTUNG PROVIDER: Gemini (google-gla) mengirim dict,
    provider OpenAI-compatible (OpenRouter, dsb.) mengirim STRING JSON.
    Semua konsumen args di script ini wajib lewat helper ini supaya metrik
    (sqls, origin) tidak diam-diam kosong saat ganti provider.
    """
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _flatten_args(args) -> str:
    """One flat 'key=value key=value' string per call — same shape for EVERY tool.

    Values are whitespace-collapsed and truncated (sql/query/code 200 chars,
    everything else 160) so the ledger stays greppable and never nests.
    """
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return " ".join(args.split())[:200]
    if not isinstance(args, dict):
        return ""
    parts = []
    for k in sorted(args):
        text = " ".join(str(args[k]).split())
        limit = 200 if k in ("sql", "query", "code") else 160
        if len(text) > limit:
            text = text[: limit - 1] + "…"
        parts.append(f"{k}={text}")
    return " ".join(parts)


def _build_tool_origin_map(agent) -> dict[str, str]:
    """Map every REGISTERED tool name → its toolset id, read from the live agent.

    Data-driven: whatever tools seeknal registers (now or in the future) get their
    real toolset id here — no hardcoded tool-name list to fall out of date.
    Handles nested/wrapped toolsets recursively.
    """
    mapping: dict[str, str] = {}

    def collect(ts) -> None:
        ts_id = str(getattr(ts, "id", None) or type(ts).__name__)
        tools = getattr(ts, "tools", None)
        if isinstance(tools, dict):
            for name in tools:
                mapping.setdefault(str(name), ts_id)
        elif isinstance(tools, (list, tuple)):
            for t in tools:
                name = getattr(t, "name", None) or getattr(getattr(t, "function", None), "__name__", None)
                if name:
                    mapping.setdefault(str(name), ts_id)
        inner = getattr(ts, "wrapped", None)
        if inner is not None:
            collect(inner)
        for sub in getattr(ts, "toolsets", None) or []:
            collect(sub)

    try:
        for ts in getattr(agent, "toolsets", None) or []:
            collect(ts)
    except Exception:
        pass
    return mapping


# High-signal semantic labels for a handful of names whose MEANING matters more
# than their toolset id. Everything else falls through to the live toolset map,
# and names absent from BOTH are labeled 'unmapped-tool' — visible, never
# silently absorbed into a wrong bucket.
_SEMANTIC_ORIGIN = {
    "execute_sql": "database", "preview_query": "database",
    "execute_sql_pair": "database", "describe_table": "database",
    "list_tables": "database",
    "request_clarification": "user-interaction", "ask_user": "user-interaction",
    "upload_to_s3": "compute-export", "run_forecast": "compute-export",
    "detect_anomaly": "compute-export", "execute_python": "compute-export",
    "list_context_files": "source-context", "list_source_context": "source-context",
    "read_source_context": "source-context",
}


def _trace_origin(tool_name: str, args, variant_path: Path,
                  origin_map: dict[str, str] | None = None) -> str:
    """Classify WHERE a call points.

    Order: data-derived (skill dir / file path) → semantic label → live toolset
    id from the agent (`toolset:<id>`) → 'unmapped-tool' (explicitly visible).
    """
    a = args if isinstance(args, dict) else {}
    if tool_name == "load_skill":
        # Real tool arg is `skill_name`; keep name/skill as fallbacks.
        name = str(a.get("skill_name") or a.get("name") or a.get("skill") or "")
        if name and (variant_path / "skills" / name).is_dir():
            return "project-skill"
        return "engine-builtin-skill"
    if tool_name == "read_project_file":
        path = str(a.get("path") or a.get("file_path") or "")
        if "context/" in path:
            return "project-context"
        if "skills/" in path:
            return "project-skill-file"
        return "project-file"
    if tool_name in _SEMANTIC_ORIGIN:
        return _SEMANTIC_ORIGIN[tool_name]
    if origin_map and tool_name in origin_map:
        return f"toolset:{origin_map[tool_name]}"
    return "unmapped-tool"


def _extract_tool_trace(messages, variant_path: Path,
                        origin_map: dict[str, str] | None = None) -> list[dict]:
    """Flat chronological ledger of every tool call in this turn's messages.

    Pairs each ToolCallPart with its ToolReturnPart via tool_call_id to attach
    result size + ok/error status. Fixed keys, no nesting — auditable by grep.
    """
    from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart

    returns: dict = {}
    t0 = None
    for m in messages:
        ts = getattr(m, "timestamp", None)
        if ts is not None and t0 is None:
            t0 = ts
        for p in getattr(m, "parts", []):
            if isinstance(p, ToolReturnPart):
                returns[p.tool_call_id] = p

    trace: list[dict] = []
    step = 0
    for m in messages:
        if not isinstance(m, ModelResponse):
            continue
        m_ts = getattr(m, "timestamp", None)
        at_s = round((m_ts - t0).total_seconds(), 1) if (m_ts is not None and t0 is not None) else None
        for p in getattr(m, "parts", []):
            if not isinstance(p, ToolCallPart):
                continue
            step += 1
            # [FIX provider-args] Versi lama meneruskan string mentah sehingga
            # _trace_origin menerima {} → load_skill salah dilabeli
            # "engine-builtin-skill" dan read_project_file context/ salah
            # dilabeli "project-file" saat provider OpenRouter dipakai:
            # args = p.args if isinstance(p.args, dict) else p.args
            args = _tool_call_args_dict(p.args)
            ret = returns.get(p.tool_call_id)
            if ret is None:
                result_chars, status = 0, "no-return"
            else:
                content = str(getattr(ret, "content", "") or "")
                result_chars = len(content)
                head = content.lstrip()[:200].lower()
                status = "error" if (head.startswith("error")
                                     or head.startswith("[error")
                                     or '"error"' in head
                                     or "tool_error" in head) else "ok"
            trace.append({
                "step": step,
                "at_s": at_s,
                "tool": p.tool_name,
                # arg pakai p.args ASLI: _flatten_args sudah menangani str/dict
                # sendiri, dan fallback string-mentahnya (utk JSON malformed)
                # tetap terjaga. origin pakai dict hasil normalisasi.
                "arg": _flatten_args(p.args),
                "origin": _trace_origin(p.tool_name, args, variant_path, origin_map),
                "result_chars": result_chars,
                "status": status,
            })
    return trace


def _trace_derivatives(trace: list[dict]) -> tuple[list[str], list[str]]:
    """(files_read, skills_loaded) — flat ordered string lists for quick audit."""
    files, skills = [], []
    for e in trace:
        if e["tool"] == "read_project_file":
            m = re.search(r"(?:path|file_path)=(\S+)", e["arg"])
            if m:
                files.append(m.group(1))
        elif e["tool"] == "load_skill":
            m = re.search(r"(?:name|skill)=(\S+)", e["arg"])
            if m:
                skills.append(m.group(1))
    return files, skills


def _out_trace(out, label: str, trace: list[dict], cap: int = 40) -> None:
    """Print the ledger one aligned line per step — same flat shape as the JSON."""
    for e in trace[:cap]:
        at = f"{e['at_s']:6.1f}s" if e["at_s"] is not None else "     ?s"
        kb = f"{e['result_chars']/1024:.1f}KB" if e["result_chars"] else "-"
        out(f"  {label} {e['step']:02d} {at} {e['tool']:<22} [{e['origin']}] {e['arg'][:110]} → {kb} {e['status']}")
    if len(trace) > cap:
        out(f"  {label} … +{len(trace)-cap} step lagi (lihat JSON tool_trace)")


def _run_scenario_for_variant(
    scenario: Scenario,
    variant_path: Path,
    auto_clarif: bool = False,
) -> tuple[ScenarioResult, str]:
    from seeknal.cli.ask import _load_project_env
    from seeknal.ask.agents.agent import create_agent, ask as agent_ask
    from seeknal.ask.agents.tools._context import reset_turn_governor, get_tool_context
    from pydantic_ai.messages import ModelResponse, ToolCallPart

    import seeknal.ask.testing as _testing_mod
    _testing_mod.save_ask_sql_test_results = lambda *a, **kw: Path("/dev/null")

    _load_project_env(variant_path)

    buf = io.StringIO()

    def out(msg: str = "") -> None:
        buf.write(msg + "\n")

    variant_name = variant_path.name
    out(f">>> [{scenario.scenario_id}] variant={variant_name}  ({len(scenario.turns)} turns)")

    try:
        agent, deps, history, _ = create_agent(variant_path, environment="gateway")
        tool_origin_map = _build_tool_origin_map(agent)
        turn_results: list[TurnResult] = []

        for i, turn in enumerate(scenario.turns, start=1):
            if auto_clarif and turn.clarif_response:
                out(f"  T{i} [SKIP] clarif_response skipped (auto-clarif active)")
                continue

            prev_len = len(history)
            reset_turn_governor(turn.prompt)
            start = time.monotonic()
            timed_out = False
            answer = ""

            try:
                answer = agent_ask(agent, deps, history, turn.prompt)
            except TimeoutError as exc:
                timed_out = True
                answer = f"[TIMEOUT] {exc}"
            except Exception as exc:
                answer = f"[ERROR] {type(exc).__name__}: {exc}"

            elapsed = time.monotonic() - start
            new_msgs = history[prev_len:]

            turn_llm_req = sum(1 for m in new_msgs if isinstance(m, ModelResponse))
            turn_tool_calls = sum(
                1 for m in new_msgs
                for p in getattr(m, "parts", [])
                if isinstance(p, ToolCallPart)
            )
            turn_sqls = _extract_sqls(new_msgs)
            turn_clarif = sum(
                1 for m in new_msgs
                for p in getattr(m, "parts", [])
                if isinstance(p, ToolCallPart) and p.tool_name == "request_clarification"
            )

            # Capture full clarification details (questions + all options) for
            # the JSON output. Previously only the count was recorded.
            turn_clarif_slots: list = []
            if turn_clarif > 0:
                try:
                    ctx = get_tool_context()
                    pending = getattr(ctx, "pending_clarification", None)
                    for slot in _normalize_clarification_slots(pending):
                        turn_clarif_slots.append({
                            "question": slot.get("question", ""),
                            "options": [
                                {
                                    "label": opt.get("label", ""),
                                    "recommended": bool(opt.get("recommended")),
                                }
                                for opt in slot.get("options", [])
                            ],
                        })
                except Exception:
                    pass

            failures = []
            if not timed_out:
                # When clarify fires, T1 is a clarification prompt, not the
                # real answer — skip content assertions (assert_contains) and
                # only check assert_asked. The real answer is checked on the
                # AUTO turn below.
                if turn_clarif > 0:
                    if turn.assert_asked is False:
                        failures.append(f"expected no clarification but agent called it {turn_clarif}x")
                    # A clarification turn is only allowed to skip the content
                    # asserts because the AUTO turn below re-runs them on the
                    # real answer. That contract only holds when there ARE
                    # structured options to auto-pick from. If the agent called
                    # request_clarification but left pending_clarification empty
                    # (options typed into the answer text instead of the tool
                    # args), the AUTO turn never fires — so this turn would slip
                    # through as a vacuous PASS with no answer at all. Fail it
                    # explicitly instead. (Governed by auto_clarif; when
                    # auto-clarif is off, stopping at the question is expected.)
                    elif auto_clarif:
                        try:
                            _clar_ctx = get_tool_context()
                            _pending = getattr(_clar_ctx, "pending_clarification", None)
                        except Exception:
                            _pending = None
                        if not _normalize_clarification_slots(_pending):
                            failures.append(
                                "clarification asked but carried no pickable options "
                                "(pending_clarification empty or malformed) — cannot produce an answer turn"
                            )
                else:
                    for expected in turn.assert_contains:
                        if expected.lower() not in answer.lower():
                            failures.append(f"missing: '{expected}'")
                    if turn.assert_any_of:
                        if not _any_of_matches(turn.assert_any_of, answer.lower(), turn.tolerance_pct):
                            failures.append(f"no assert_any_of group matched (tol={turn.tolerance_pct}%)")
                    if turn.assert_asked is True and turn_clarif == 0:
                        failures.append("expected clarification ask but agent did not call request_clarification")
                    elif turn.assert_asked is False and turn_clarif > 0:
                        failures.append(f"expected no clarification but agent called it {turn_clarif}x")
            if timed_out:
                failures.append("timed out")

            passed = not failures
            status = "✓" if passed else "✗"
            out(
                f"  T{i} [{status}] {elapsed:5.1f}s  llm={turn_llm_req:<3d}"
                f"  sql={len(turn_sqls):<2d}  clarif={turn_clarif}"
                f"  '{turn.prompt[:50]}'"
            )
            # Tool breakdown for T1 (same as AUTO turn) — diagnose what tools
            # the agent called, especially when tool_calls > 0 but sqls = [].
            from collections import Counter
            t1_tool_names = [
                p.tool_name
                for m in new_msgs
                for p in getattr(m, "parts", [])
                if isinstance(p, ToolCallPart)
            ]
            turn_tool_breakdown = dict(Counter(t1_tool_names))
            if turn_tool_calls > 0:
                out(f"  T{i} tool breakdown: {turn_tool_breakdown}")

            # Flat step-by-step ledger (root-cause tracing): which skill/context
            # file was loaded, in what order, before which SQL.
            turn_trace = _extract_tool_trace(new_msgs, variant_path, tool_origin_map)
            turn_files_read, turn_skills_loaded = _trace_derivatives(turn_trace)
            turn_trace_partial = False
            if not new_msgs and answer.startswith(("[ERROR]", "[TIMEOUT]")):
                # Run aborted before messages were returned to history — pull the
                # governor's weak per-turn evidence instead of pretending 0 calls.
                turn_trace_partial = True
                try:
                    gctx = get_tool_context()
                    g_calls = int(getattr(gctx, "tool_calls_this_turn", 0) or 0)
                    for ev in list(getattr(gctx, "timing_events_this_turn", []) or []):
                        turn_trace.append({
                            "step": len(turn_trace) + 1,
                            "at_s": None,
                            "tool": str(ev.get("name", "?")),
                            "arg": f"elapsed_ms={ev.get('elapsed_ms', '?')}",
                            "origin": "governor-partial",
                            "result_chars": 0,
                            "status": "partial",
                        })
                    if g_calls:
                        out(f"  T{i} TRACE PARTIAL: run aborted; governor counted {g_calls} tool call(s) this turn")
                        turn_tool_calls = max(turn_tool_calls, g_calls)
                except Exception:
                    out(f"  T{i} TRACE PARTIAL: run aborted; no governor evidence available")
            if turn_trace:
                _out_trace(out, f"T{i}", turn_trace)
            if turn_clarif_slots:
                for si, slot in enumerate(turn_clarif_slots, 1):
                    out(f"  T{i} clarify slot {si}: '{slot['question'][:80]}'")
                    for opt in slot["options"]:
                        rec = " ★" if opt["recommended"] else ""
                        out(f"    - {opt['label']}{rec}")
            for f in failures:
                out(f"         FAIL: {f}")

            turn_results.append(TurnResult(
                turn_num=i,
                prompt=turn.prompt,
                answer=answer,
                elapsed_s=elapsed,
                llm_requests=turn_llm_req,
                tool_calls=turn_tool_calls,
                sqls=turn_sqls,
                passed=passed,
                failures=failures,
                note=turn.note,
                timed_out=timed_out,
                ask_user_calls=turn_clarif,
                clarif_slots=turn_clarif_slots,
                tools=turn_tool_breakdown,
                tool_trace=turn_trace,
                files_read=turn_files_read,
                skills_loaded=turn_skills_loaded,
                trace_partial=turn_trace_partial,
            ))

            # Auto-clarif: inject recommended option as extra turn (all slots)
            if auto_clarif and turn_clarif > 0 and not timed_out:
                ctx = get_tool_context()
                raw_pending = getattr(ctx, "pending_clarification", None)
                # Coerce both shapes (list-of-slots and flattened list-of-options)
                # into canonical slots so auto-pick works regardless of what the
                # model emitted this run.
                pending = _normalize_clarification_slots(raw_pending)
                if not pending:
                    # request_clarification was called but carried nothing
                    # pickable (empty, or malformed with no options anywhere).
                    # The AUTO turn cannot run and the T1 assert-skip above has
                    # already been turned into a FAIL. Surface it loudly instead
                    # of skipping this whole block in silence.
                    out(
                        f"  [AUTO-CLARIF] SKIPPED: request_clarification called but "
                        f"carried no pickable options (empty/malformed pending); "
                        f"T{i} marked FAIL (no answer turn produced)"
                    )
                if pending:
                    chosen_labels: list[str] = []
                    for slot_idx, slot in enumerate(pending):
                        slot_opts = slot.get("options", [])
                        slot_q = slot.get("question", f"slot {slot_idx + 1}")
                        slot_rec = next(
                            (o for o in slot_opts if o.get("recommended")),
                            None,
                        )
                        if slot_rec is None and slot_opts:
                            out(f"  [AUTO-CLARIF] WARNING: slot {slot_idx+1} ('{slot_q[:50]}') — no recommended:true, fallback options[0]")
                        chosen_opt = slot_rec or (slot_opts[0] if slot_opts else None)
                        if chosen_opt:
                            label = chosen_opt.get("label", "")
                            chosen_labels.append(label)
                            out(f"  [AUTO-CLARIF] slot {slot_idx+1}/{len(pending)}: '{label}' (recommended={slot_rec is not None})")
                    if chosen_labels:
                        auto_prompt = "; ".join(chosen_labels)
                        out(f"  [AUTO-CLARIF] injecting ({len(chosen_labels)} slot(s)): '{auto_prompt}'")

                        auto_prev = len(history)
                        reset_turn_governor(auto_prompt)
                        auto_start = time.monotonic()
                        auto_answer = ""
                        try:
                            auto_answer = agent_ask(agent, deps, history, auto_prompt)
                        except Exception as exc2:
                            auto_answer = f"[ERROR] {type(exc2).__name__}: {exc2}"

                        auto_elapsed = time.monotonic() - auto_start
                        auto_msgs = history[auto_prev:]
                        auto_sqls = _extract_sqls(auto_msgs)
                        auto_tools = sum(
                            1 for m in auto_msgs
                            for p in getattr(m, "parts", [])
                            if isinstance(p, ToolCallPart)
                        )
                        auto_llm_req = sum(1 for m in auto_msgs if isinstance(m, ModelResponse))
                        auto_tool_names = [
                            p.tool_name
                            for m in auto_msgs
                            for p in getattr(m, "parts", [])
                            if isinstance(p, ToolCallPart)
                        ]
                        from collections import Counter
                        auto_tool_summary = dict(Counter(auto_tool_names))
                        # Run assert_contains against the AUTO answer (the real
                        # answer after clarification), not hardcoded pass.
                        auto_failures = []
                        for expected in turn.assert_contains:
                            if expected.lower() not in auto_answer.lower():
                                auto_failures.append(f"missing: '{expected}'")
                        if turn.assert_any_of:
                            if not _any_of_matches(turn.assert_any_of, auto_answer.lower(), turn.tolerance_pct):
                                auto_failures.append(f"no assert_any_of group matched (tol={turn.tolerance_pct}%)")
                        auto_passed = not auto_failures
                        auto_status = "✓" if auto_passed else "✗"
                        out(f"  [AUTO] [{auto_status}] assert check on real answer ({len(auto_failures)} fail)")
                        for af in auto_failures:
                            out(f"         AUTO FAIL: {af}")

                        auto_trace = _extract_tool_trace(auto_msgs, variant_path, tool_origin_map)
                        auto_files, auto_skills = _trace_derivatives(auto_trace)
                        if auto_trace:
                            _out_trace(out, "[AUTO]", auto_trace)

                        turn_results.append(TurnResult(
                            turn_num=i,
                            prompt=f"[AUTO] {auto_prompt}",
                            answer=auto_answer,
                            elapsed_s=auto_elapsed,
                            llm_requests=auto_llm_req,
                            tool_calls=auto_tools,
                            sqls=auto_sqls,
                            passed=auto_passed,
                            failures=auto_failures,
                            note=f"Auto-selected: {auto_prompt}",
                            timed_out=False,
                            ask_user_calls=0,
                            is_auto_clarif=True,
                            tools=auto_tool_summary,
                            tool_trace=auto_trace,
                            files_read=auto_files,
                            skills_loaded=auto_skills,
                        ))

            # [SAFETY NET] Second layer over the per-turn verdict above.
            # A clarification turn was allowed to skip the content asserts on the
            # promise that an AUTO turn re-runs them on the real answer. If, for
            # ANY reason (empty/malformed pending, no pickable option), that AUTO
            # turn was never produced, the clarification turn would otherwise slip
            # through as a vacuous PASS with no answer. Force it to FAIL here.
            #
            # Guarded by `auto_clarif`: with --no-auto-clarif, stopping at the
            # question is the expected behaviour, so we never touch it. Matches
            # parent↔AUTO by turn_num AND is_auto_clarif (they share turn_num).
            # Idempotent: only flips a still-True parent, so it never double-
            # counts with the per-turn FAIL already appended above.
            if auto_clarif and turn_clarif > 0 and not timed_out:
                _has_auto = any(
                    t.is_auto_clarif and t.turn_num == i for t in turn_results
                )
                if not _has_auto:
                    _parent = next(
                        (t for t in turn_results
                         if t.turn_num == i and not t.is_auto_clarif),
                        None,
                    )
                    if _parent is not None and _parent.passed:
                        _parent.passed = False
                        _parent.failures.append(
                            "clarification asked but no AUTO answer turn was "
                            "produced — cannot verify an answer (safety net)"
                        )
                        out(
                            f"  [SAFETY NET] T{i}: clarification without an AUTO "
                            f"answer turn — forced FAIL"
                        )

        result = ScenarioResult(
            name=scenario.name,
            scenario_id=scenario.scenario_id,
            turns=turn_results,
            variant_name=variant_name,
        )
        total_time = sum(t.elapsed_s for t in turn_results)
        passed_count = sum(1 for t in turn_results if t.passed)
        out(f"  → {passed_count}/{len(turn_results)} passed  {total_time:.1f}s  variant={variant_name}")
        return result, buf.getvalue()

    except Exception as exc:
        out(f"  FATAL ERROR: {exc}")
        return ScenarioResult(
            name=scenario.name,
            scenario_id=scenario.scenario_id,
            turns=[],
            variant_name=variant_name,
            status="fatal",  # [G7] bukan timeout: exception di luar turn loop
        ), buf.getvalue()


# ---------------------------------------------------------------------------
# Parallel orchestrator
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# [G7-LEGACY] Versi THREAD lama — DINONAKTIFKAN, disimpan sebagai referensi.
#
# Kenapa diganti (audit 2026-07-16, "G7 — instrumen ukur cacat"):
#   1. `future.cancel()` TIDAK BISA menghentikan thread yang sudah berjalan —
#      ThreadPoolExecutor tidak punya interupsi thread. Run yang kena timeout
#      jadi THREAD YATIM: terus memanggil LLM/DB di background, makan kuota
#      API dan lock DB, dan menabrak batch berikutnya (self-amplifying).
#   2. `pool_size = len(work_items)` → semua future langsung start, tidak ada
#      yang antre, sehingga `cancel_futures=True` tidak pernah membatalkan apa pun.
#   3. Satu deadline bersama `batch_start + scenario_timeout` — pasangan yang
#      lambat menggerus jatah waktu pasangan lain di batch yang sama.
#   4. Row timeout tidak dibedakan dari row 0-SQL asli → "0 turns/0.0s"
#      mengotori pass-rate (baseline "0/4" BAYI didominasi row jenis ini).
#
# Pengganti: versi SUBPROCESS di bawah — proses bisa benar-benar di-kill.
# ---------------------------------------------------------------------------
# def _run_scenario_batch(
#     scenario_batch: list[Scenario],
#     variants: list[Path],
#     scenario_timeout: float,
#     auto_clarif: bool,
# ) -> dict[str, dict[str, ScenarioResult]]:
#     """Run one batch of scenarios, all variants in parallel for each scenario.
#
#     Pool size = len(scenario_batch) × len(variants).
#     Returns {scenario_id: {variant_name: ScenarioResult}}.
#     """
#     work_items = [(s, v) for s in scenario_batch for v in variants]
#     batch_results: dict[str, dict[str, ScenarioResult]] = {s.scenario_id: {} for s in scenario_batch}
#
#     pool_size = len(work_items)
#     pool = concurrent.futures.ThreadPoolExecutor(max_workers=pool_size)
#     future_map = {
#         pool.submit(_run_scenario_for_variant, s, v, auto_clarif): (s.scenario_id, v.name)
#         for s, v in work_items
#     }
#
#     # Per-scenario timeout: each future gets scenario_timeout seconds from
#     # batch_start (all futures start together since pool_size = len(work_items)).
#     # This replaces the old batch-level as_completed(timeout=) which gave the
#     # WHOLE batch a single timeout deadline.
#     batch_start = time.monotonic()
#     pending = set(future_map.keys())
#
#     try:
#         while pending:
#             remaining = scenario_timeout - (time.monotonic() - batch_start)
#             if remaining <= 0:
#                 break
#
#             done, _ = concurrent.futures.wait(
#                 pending, timeout=remaining,
#                 return_when=concurrent.futures.FIRST_COMPLETED,
#             )
#
#             if not done:
#                 break  # Timeout expired
#
#             for future in done:
#                 pending.discard(future)
#                 sid, vname = future_map[future]
#                 try:
#                     result, captured = future.result()
#                     print(captured, end="", flush=True)
#                     batch_results[sid][vname] = result
#                 except Exception as exc:
#                     print(f"  ✗ [{sid}] [{vname}] ERROR: {exc}\n", flush=True)
#                     batch_results[sid][vname] = ScenarioResult(
#                         name=sid, scenario_id=sid, turns=[], variant_name=vname,
#                     )
#
#         # Mark all unfinished as TIMEOUT
#         for future in pending:
#             sid, vname = future_map[future]
#             if vname not in batch_results.get(sid, {}):
#                 elapsed = time.monotonic() - batch_start
#                 print(f"  ✗ [{sid}] [{vname}] TIMEOUT ({elapsed:.0f}s)\n", flush=True)
#                 batch_results[sid][vname] = ScenarioResult(
#                     name=sid, scenario_id=sid, turns=[], variant_name=vname,
#                 )
#             future.cancel()
#     finally:
#         pool.shutdown(wait=False, cancel_futures=True)
#     return batch_results


def _run_scenario_batch(
    scenario_batch: list[Scenario],
    variants: list[Path],
    scenario_timeout: float,
    auto_clarif: bool,
) -> dict[str, dict[str, ScenarioResult]]:
    """[G7] Versi SUBPROCESS-ISOLATION — satu proses per (scenario × variant).

    Perbaikan atas versi thread lama (lihat blok [G7-LEGACY] di atas):
      - Timeout PER-PASANGAN dihitung dari start proses masing-masing, bukan
        satu deadline bersama untuk seluruh batch.
      - Pada timeout, prosesnya DI-KILL sungguhan (`proc.kill()`) — tidak ada
        lagi thread yatim yang diam-diam terus makan kuota LLM/DB.
      - Row hasil diberi `status` ("completed"/"timeout"/"fatal") sehingga
        kegagalan infra tidak lagi menyamar sebagai kegagalan penalaran.
      - Bonus: tiap proses punya env sendiri → hazard `load_dotenv(override=False)`
        lintas-varian hilang total.

    Model paralelisme TIDAK berubah: semua pasangan dalam satu batch tetap
    berjalan serentak (concurrency = workers × jumlah varian), sama seperti
    yang didokumentasikan di docstring modul.

    Returns {scenario_id: {variant_name: ScenarioResult}}.
    """
    import shutil
    import subprocess
    import tempfile

    work_items = [(s, v) for s in scenario_batch for v in variants]
    batch_results: dict[str, dict[str, ScenarioResult]] = {s.scenario_id: {} for s in scenario_batch}

    tmp_dir = Path(tempfile.mkdtemp(prefix="variant_compare_g7_"))
    jobs: list[dict] = []
    try:
        # Spawn satu worker-subprocess per pasangan. Log worker diarahkan ke
        # FILE (bukan PIPE) supaya worker tidak pernah nge-block gara-gara
        # buffer pipe penuh; dibaca dan dicetak parent setelah proses selesai.
        for idx, (s, v) in enumerate(work_items):
            scen_path = tmp_dir / f"scenario_{idx}.json"
            out_path = tmp_dir / f"result_{idx}.json"
            log_path = tmp_dir / f"log_{idx}.txt"
            scen_path.write_text(
                json.dumps(_scenario_to_dict(s), ensure_ascii=False), encoding="utf-8"
            )
            cmd = [
                sys.executable, str(Path(__file__).resolve()),
                "--single-scenario-file", str(scen_path),
                "--single-variant", str(v.resolve()),
                "--single-out", str(out_path),
            ]
            if not auto_clarif:
                cmd.append("--no-auto-clarif")
            log_fh = open(log_path, "w", encoding="utf-8")
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=log_fh,
                stderr=subprocess.STDOUT,
            )
            jobs.append({
                "proc": proc,
                "log_fh": log_fh,
                "sid": s.scenario_id,
                "vname": v.name,
                "out": out_path,
                "log": log_path,
                "start": time.monotonic(),
            })

        # Poll sampai semua selesai; tiap job punya deadline sendiri.
        pending = list(jobs)
        while pending:
            still_pending: list[dict] = []
            for job in pending:
                rc = job["proc"].poll()
                elapsed = time.monotonic() - job["start"]
                if rc is None and elapsed < scenario_timeout:
                    still_pending.append(job)
                    continue

                try:
                    job["log_fh"].close()
                except Exception:
                    pass
                sid, vname = job["sid"], job["vname"]

                if rc is None:
                    # Deadline lewat → bunuh PROSES. Ini perbedaan kunci dari
                    # versi thread: prosesnya benar-benar mati, bukan yatim.
                    job["proc"].kill()
                    try:
                        job["proc"].wait(timeout=10)
                    except Exception:
                        pass
                    partial = ""
                    try:
                        partial = job["log"].read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        pass
                    if partial.strip():
                        # Log parsial worker (baris logging ter-flush per record;
                        # buffer ledger per-turn ikut hilang saat kill — sama
                        # seperti perilaku lama, tapi kini prosesnya berhenti).
                        print(partial, end="", flush=True)
                    print(
                        f"  ✗ [{sid}] [{vname}] TIMEOUT ({elapsed:.0f}s) — subprocess di-kill\n",
                        flush=True,
                    )
                    batch_results[sid][vname] = ScenarioResult(
                        name=sid, scenario_id=sid, turns=[],
                        variant_name=vname, status="timeout",
                    )
                else:
                    captured = ""
                    try:
                        captured = job["log"].read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        pass
                    if captured.strip():
                        print(captured, end="", flush=True)
                    result: ScenarioResult | None = None
                    if job["out"].exists():
                        try:
                            result = _scenario_result_from_dict(
                                json.loads(job["out"].read_text(encoding="utf-8"))
                            )
                        except Exception as exc:
                            print(f"  ✗ [{sid}] [{vname}] ERROR baca hasil worker: {exc}\n", flush=True)
                    if result is None:
                        print(f"  ✗ [{sid}] [{vname}] FATAL: worker exit rc={rc} tanpa file hasil\n", flush=True)
                        result = ScenarioResult(
                            name=sid, scenario_id=sid, turns=[],
                            variant_name=vname, status="fatal",
                        )
                    batch_results[sid][vname] = result

            pending = still_pending
            if pending:
                time.sleep(0.5)
    finally:
        # Jaring pengaman: apa pun yang terjadi, tidak boleh ada proses hidup
        # yang lolos dari batch ini.
        for job in jobs:
            try:
                if job["proc"].poll() is None:
                    job["proc"].kill()
            except Exception:
                pass
            try:
                job["log_fh"].close()
            except Exception:
                pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return batch_results


def run_all_variants(
    scenarios: list[Scenario],
    variants: list[Path],
    workers: int = 1,
    scenario_timeout: float = 300.0,
    auto_clarif: bool = False,
) -> dict[str, dict[str, ScenarioResult]]:
    """Run all scenarios against all variants with controlled parallelism.

    workers  — berapa pertanyaan (scenario) jalan bersamaan (default 1).
    Variants — selalu dijalankan paralel di dalam setiap pertanyaan.
    Total concurrent LLM sessions = workers × len(variants).

    Returns {scenario_id: {variant_name: ScenarioResult}}.
    """
    n_variants = len(variants)
    workers = max(1, workers)
    total_runs = len(scenarios) * n_variants
    concurrent_runs = workers * n_variants

    print(
        f"\n{len(scenarios)} scenario(s) × {n_variants} variant(s) = {total_runs} run(s)"
        f"  |  concurrency: {workers} scenario(s) × {n_variants} variants = {concurrent_runs} paralel"
        f"  |  timeout={scenario_timeout}s  auto-clarif={auto_clarif}\n"
    )

    all_results: dict[str, dict[str, ScenarioResult]] = {}

    # Process scenarios in batches of `workers`
    for batch_start in range(0, len(scenarios), workers):
        batch = scenarios[batch_start: batch_start + workers]
        batch_num = batch_start // workers + 1
        total_batches = (len(scenarios) + workers - 1) // workers
        sids = [s.scenario_id for s in batch]
        print(f"\n{'='*60}")
        print(f"Batch {batch_num}/{total_batches}  scenarios={sids}")
        print(f"{'='*60}\n")

        batch_results = _run_scenario_batch(batch, variants, scenario_timeout, auto_clarif)
        all_results.update(batch_results)

    return all_results


# ---------------------------------------------------------------------------
# Comparison table (console)
# ---------------------------------------------------------------------------

def print_comparison(
    results: dict[str, dict[str, ScenarioResult]],
    scenarios: list[Scenario],
    variants: list[Path],
) -> None:
    variant_names = [v.name for v in variants]

    def _short(name: str) -> str:
        return (
            name
            .replace("notsystemprompt", "newsys")
            .replace("after-refactor-", "after-")
            .replace("pre-refactor-", "pre-")
        )

    col_s = max((len(s.scenario_id) for s in scenarios), default=12) + 2
    col_v = 18

    print("\n" + "=" * 70)
    print("VARIANT COMPARISON")
    print("=" * 70)

    # Header row
    header = f"{'SCENARIO':<{col_s}}"
    for vname in variant_names:
        header += f"  {_short(vname)[:col_v]:<{col_v}}"
    print(header)
    print("-" * 70)

    for scenario in scenarios:
        sid = scenario.scenario_id
        row = f"{sid:<{col_s}}"
        for vname in variant_names:
            r = results.get(sid, {}).get(vname)
            # [G7] Bedakan kegagalan infra dari hasil eksekusi asli.
            # Versi lama (disimpan sebagai referensi):
            # if r is None or not r.turns:
            #     cell = "NO DATA"
            if r is None:
                cell = "NO DATA"
            elif not r.turns:
                cell = {"timeout": "TIMEOUT", "fatal": "FATAL"}.get(r.status, "NO DATA")
            else:
                t1 = next((t for t in r.turns if t.turn_num == 1 and not t.is_auto_clarif), None)
                clarif = t1.ask_user_calls if t1 else 0
                cell = f"{'PASS' if r.passed else 'FAIL'}  c={clarif}"
            row += f"  {cell:<{col_v}}"
        print(row)

    print("-" * 70)

    # Summary row: pass count per variant
    row = f"{'PASS/TOTAL':<{col_s}}"
    for vname in variant_names:
        passed = sum(
            1 for s in scenarios
            if results.get(s.scenario_id, {}).get(vname) and results[s.scenario_id][vname].passed
        )
        row += f"  {f'{passed}/{len(scenarios)}':<{col_v}}"
    print(row)

    # [G7] Baris pembersih: berapa run yang mati karena infra (timeout/fatal)
    # per varian. Pass-rate yang jujur = PASS / (TOTAL - infra-death); jangan
    # bandingkan varian tanpa melihat baris ini.
    row = f"{'INFRA t/f':<{col_s}}"
    for vname in variant_names:
        n_timeout = sum(
            1 for s in scenarios
            if (results.get(s.scenario_id, {}).get(vname) or ScenarioResult("", "", [])).status == "timeout"
        )
        n_fatal = sum(
            1 for s in scenarios
            if (results.get(s.scenario_id, {}).get(vname) or ScenarioResult("", "", [])).status == "fatal"
        )
        row += f"  {f'{n_timeout} timeout/{n_fatal} fatal':<{col_v}}"
    print(row)
    print("=" * 70)

    print("\nLegenda:")
    for v in variants:
        print(f"  {_short(v.name):<20s}  {v.name}")
    print()


# ---------------------------------------------------------------------------
# JSON output — format mengikuti multiturn_results_*.json (v1)
# ---------------------------------------------------------------------------

def _turn_to_dict(t: TurnResult) -> dict:
    return {
        "turn_num": t.turn_num,
        "prompt": t.prompt,
        "passed": t.passed,
        "timed_out": t.timed_out,
        "elapsed_s": round(t.elapsed_s, 2),
        "llm_requests": t.llm_requests,
        "tool_calls": t.tool_calls,
        "sqls": t.sqls,
        "failures": t.failures,
        "note": t.note,
        "answer": t.answer,
        "ask_user_calls": t.ask_user_calls,
        "is_auto_clarif": t.is_auto_clarif,
        "clarif_slots": t.clarif_slots,
        "tools": t.tools,
        "tool_trace": t.tool_trace,
        "files_read": t.files_read,
        "skills_loaded": t.skills_loaded,
        "trace_partial": t.trace_partial,
    }


def save_json(
    results: dict[str, dict[str, ScenarioResult]],
    scenarios: list[Scenario],
    variants: list[Path],
    scenario_filter: str | None,
) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = _resolve_output_base() / today / _output_version()
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = f"variant_compare_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / filename

    variant_names = [v.name for v in variants]

    # Per-variant aggregate stats
    variants_summary: dict[str, dict] = {}
    for vname in variant_names:
        passed = sum(
            1 for s in scenarios
            if results.get(s.scenario_id, {}).get(vname) and results[s.scenario_id][vname].passed
        )
        failed = len(scenarios) - passed
        total_turns = sum(
            len(results[s.scenario_id][vname].turns)
            for s in scenarios
            if vname in results.get(s.scenario_id, {})
        )
        passed_turns = sum(
            sum(1 for t in results[s.scenario_id][vname].turns if t.passed)
            for s in scenarios
            if vname in results.get(s.scenario_id, {})
        )
        variants_summary[vname] = {
            "passed_scenarios": passed,
            "failed_scenarios": failed,
            "total_turns": total_turns,
            "passed_turns": passed_turns,
            "failed_turns": total_turns - passed_turns,
        }

    payload = {
        "project_path": str(PROJECT_ROOT),
        "timestamp": timestamp.isoformat(),
        "mode": "variant-compare",
        "version": "v3",
        "filter": scenario_filter,
        "variants": variant_names,
        "summary": {
            "total_scenarios": len(scenarios),
            "total_variants": len(variants),
            "variants": variants_summary,
        },
        "scenarios": [
            {
                "scenario_id": s.scenario_id,
                "name": s.name,
                "description": s.description,
                "variants": {
                    vname: {
                        "passed": r.passed,
                        "status": r.status,  # [G7] completed | timeout | fatal
                        "summary": {
                            "total_turns": len(r.turns),
                            "passed_turns": sum(1 for t in r.turns if t.passed),
                            "failed_turns": sum(1 for t in r.turns if not t.passed),
                            "total_elapsed_s": round(sum(t.elapsed_s for t in r.turns), 2),
                        },
                        "turns": [_turn_to_dict(t) for t in r.turns],
                    }
                    for vname, r in results.get(s.scenario_id, {}).items()
                },
            }
            for s in scenarios
        ],
    }

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Human-readable trace files: one folder per scenario, one file per variant.
#
# The JSON above is the source of truth for cross-run/aggregate analysis.
# This is a pure renderer over the SAME already-collected results — no
# re-run, no new data. It exists because opening the nested JSON to answer
# "what did variant B actually do on this one question" required writing a
# throwaway script every time; these files are readable top-to-bottom.
# ---------------------------------------------------------------------------

def _trace_row_md(e: dict) -> str:
    """One markdown table row for a tool_trace step — same shape as the
    stdout ledger printed by `_out_trace`, just formatted for a table cell."""
    at = f"{e['at_s']:.1f}s" if e.get("at_s") is not None else "?"
    kb = f"{e['result_chars']/1024:.1f}KB" if e.get("result_chars") else "-"
    arg = str(e.get("arg", "")).replace("|", "\\|")
    if len(arg) > 140:
        arg = arg[:139] + "…"
    return f"| {e['step']} | {at} | `{e['tool']}` | {e.get('origin','')} | {arg} | {kb} | {e.get('status','')} |"


def _variant_trace_md(scenario: Scenario, variant_name: str, result: "ScenarioResult") -> str:
    """Full readable transcript for one scenario x variant: every turn, every
    step, the final answer, and pass/fail — the file a human reads top-to-bottom."""
    lines = [
        f"# {scenario.scenario_id} — {variant_name}",
        "",
        f"**Skenario:** {scenario.name}  ",
        f"**Deskripsi:** {scenario.description}  " if scenario.description else "",
        f"**Hasil keseluruhan:** {'✅ PASS' if result.passed else '❌ FAIL'}",
        "",
        "---",
        "",
    ]
    for t in result.turns:
        lines += [
            f"## Turn {t.turn_num}{'  [AUTO-CLARIF]' if t.is_auto_clarif else ''}",
            "",
            f"**Prompt:** {t.prompt}",
            "",
        ]
        if t.note:
            lines += [f"**Note / GT:** {t.note}", ""]
        lines += [
            f"**Status:** {'✅ PASS' if t.passed else '❌ FAIL'}"
            f"{' (TIMEOUT)' if t.timed_out else ''}"
            f"{' (TRACE PARSIAL — run terhenti sebelum selesai)' if t.trace_partial else ''}  ",
            f"**Waktu:** {t.elapsed_s:.1f}s · **LLM requests:** {t.llm_requests} "
            f"· **Tool calls:** {t.tool_calls} · **SQL:** {len(t.sqls)} · **Klarifikasi:** {t.ask_user_calls}",
            "",
        ]
        if t.files_read:
            lines += [f"**Context file dibaca:** {', '.join(f'`{f}`' for f in t.files_read)}", ""]
        if t.skills_loaded:
            lines += [f"**Skill dimuat:** {', '.join(f'`{s}`' for s in t.skills_loaded)}", ""]
        if t.tool_trace:
            lines += [
                "### Step-by-step",
                "",
                "| # | t | tool | origin | arg | hasil | status |",
                "|---|---|---|---|---|---|---|",
            ]
            lines += [_trace_row_md(e) for e in t.tool_trace]
            lines += [""]
        elif t.trace_partial:
            lines += ["*(tidak ada jejak tool — run terhenti sebelum satu langkah pun tercatat)*", ""]
        if t.clarif_slots:
            lines += ["### Klarifikasi yang diajukan", ""]
            for slot in t.clarif_slots:
                lines += [f"- **{slot.get('question','')}**"]
                for opt in slot.get("options", []):
                    rec = " ★ recommended" if opt.get("recommended") else ""
                    lines += [f"  - {opt.get('label','')}{rec}"]
            lines += [""]
        lines += ["### Jawaban akhir", "", (t.answer or "*(kosong)*"), ""]
        if t.failures:
            lines += ["### Kegagalan", ""] + [f"- {f}" for f in t.failures] + [""]
        lines += ["---", ""]
    return "\n".join(lines)


def _variant_rollup_md(variant_name: str,
                       scenario_rows: list[tuple[Scenario, "ScenarioResult"]]) -> str:
    """Per-variant roll-up: one row per question this variant ran — the single
    screen to judge one variant's overall health across all questions."""
    n_pass = sum(1 for _, r in scenario_rows if r.passed)
    # [G7] Kematian infra dilaporkan terpisah supaya pass-rate bisa dibaca jujur.
    n_infra = sum(1 for _, r in scenario_rows if r.status in ("timeout", "fatal"))
    n_real = len(scenario_rows) - n_infra
    infra_note = (
        f" ({n_infra} run mati infra — timeout/fatal — di luar {n_real} run valid.)"
        if n_infra else ""
    )
    lines = [
        f"# {variant_name}",
        "",
        f"**Ringkasan:** {n_pass}/{len(scenario_rows)} pertanyaan PASS.{infra_note}",
        "",
        "| Pertanyaan | Hasil | Turns | SQL | Klarifikasi | Context dibaca | Skill dimuat | Durasi |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def _uniq(seq):
        seen, out = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x); out.append(x)
        return out

    for s, r in scenario_rows:
        # Aggregate across ALL turns (turn 1 may be a clarification with 0 SQL;
        # the real work happens in the follow-up/AUTO turn).
        n_sql = sum(len(t.sqls) for t in r.turns)
        n_clarif = sum(t.ask_user_calls for t in r.turns)
        files = ", ".join(f"`{f.split('/')[-1]}`"
                          for f in _uniq(f for t in r.turns for f in t.files_read)) or "-"
        skills = ", ".join(f"`{sk}`"
                           for sk in _uniq(sk for t in r.turns for sk in t.skills_loaded)) or "-"
        total_s = sum(t.elapsed_s for t in r.turns)
        # [G7] Kematian infra ditampilkan berbeda dari FAIL penalaran.
        # status = "✅ PASS" if r.passed else "❌ FAIL"   # (versi lama)
        if r.status == "timeout":
            status = "⏱ TIMEOUT"
        elif r.status == "fatal":
            status = "💥 FATAL"
        else:
            status = "✅ PASS" if r.passed else "❌ FAIL"
        link = f"[{s.scenario_id}](./{_urlquote(s.scenario_id)}.md)"
        lines.append(
            f"| {link} | {status} | {len(r.turns)} | {n_sql} | {n_clarif} | {files} | {skills} | {total_s:.1f}s |"
        )
    lines.append("")
    return "\n".join(lines)


def _variant_data_json(variant_name: str, run_ts: str,
                       scenario_rows: list[tuple[Scenario, "ScenarioResult"]]) -> dict:
    """Complete machine-readable slice for one variant: every question it ran,
    every turn, every field (reuses `_turn_to_dict` — same schema as big JSON)."""
    return {
        "variant": variant_name,
        "run_ts": run_ts,
        "scenarios": {
            s.scenario_id: {
                "name": s.name,
                "description": s.description,
                "passed": r.passed,
                "status": r.status,  # [G7] completed | timeout | fatal
                "summary": {
                    "total_turns": len(r.turns),
                    "passed_turns": sum(1 for t in r.turns if t.passed),
                    "failed_turns": sum(1 for t in r.turns if not t.passed),
                    "total_elapsed_s": round(sum(t.elapsed_s for t in r.turns), 2),
                },
                "turns": [_turn_to_dict(t) for t in r.turns],
            }
            for s, r in scenario_rows
        },
    }


def _run_index_md(scenarios: list[Scenario], results: dict[str, dict[str, "ScenarioResult"]],
                  variant_names: list[str], run_ts: str) -> str:
    """Whole-run map: rows = variants, cols = questions (variant-centric)."""
    lines = [
        f"# Trace index — run {run_ts}",
        "",
        f"{len(variant_names)} varian x {len(scenarios)} pertanyaan.",
        "",
        "| Varian | " + " | ".join(s.scenario_id for s in scenarios) + " |",
        "|---|" + "---|" * len(scenarios),
    ]
    for vname in variant_names:
        vq = _urlquote(vname)
        cells = []
        for s in scenarios:
            r = results.get(s.scenario_id, {}).get(vname)
            if r is None:
                cells.append("-")
            else:
                # [G7] ⏱ = timeout (proses di-kill), 💥 = fatal (exception init);
                # keduanya BUKAN kegagalan penalaran — jangan dihitung sebagai ❌.
                # mark = "✅" if r.passed else "❌"   # (versi lama)
                if r.status == "timeout":
                    mark = "⏱"
                elif r.status == "fatal":
                    mark = "💥"
                else:
                    mark = "✅" if r.passed else "❌"
                cells.append(f"[{mark}](./{vq}/{_urlquote(s.scenario_id)}.md)")
        lines.append(f"| [{vname}](./{vq}/_summary.md) | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def save_trace_files(
    results: dict[str, dict[str, ScenarioResult]],
    scenarios: list[Scenario],
    variants: list[Path],
    run_dir: Path,
) -> Path:
    """Render the SAME already-collected results as a variant-centric tree:

        <run_ts>/_index.md
        <run_ts>/<variant_name>/_summary.md   ← roll-up: all questions this variant ran
        <run_ts>/<variant_name>/_data.json    ← complete machine slice for this variant
        <run_ts>/<variant_name>/<scenario_id>.md ← full detail per question

    Pure renderer — no agent calls, no new data. Works for any number of
    variants (even one). Safe to call after save_json.
    """
    variant_names = [v.name for v in variants]
    run_dir.mkdir(parents=True, exist_ok=True)

    for vname in variant_names:
        # Collect this variant's results, preserving scenario order.
        scenario_rows = [
            (s, results[s.scenario_id][vname])
            for s in scenarios
            if vname in results.get(s.scenario_id, {})
        ]
        if not scenario_rows:
            continue
        variant_dir = run_dir / vname
        variant_dir.mkdir(parents=True, exist_ok=True)
        (variant_dir / "_summary.md").write_text(
            _variant_rollup_md(vname, scenario_rows), encoding="utf-8"
        )
        (variant_dir / "_data.json").write_text(
            json.dumps(_variant_data_json(vname, run_dir.name, scenario_rows),
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        for s, r in scenario_rows:
            (variant_dir / f"{s.scenario_id}.md").write_text(
                _variant_trace_md(s, vname, r), encoding="utf-8"
            )

    (run_dir / "_index.md").write_text(
        _run_index_md(scenarios, results, variant_names, run_dir.name), encoding="utf-8"
    )
    return run_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Jalankan skenario yang sama terhadap beberapa context variant dan bandingkan."
    )
    parser.add_argument(
        "--variants-path",
        type=str,
        default=str(DEFAULT_VARIANTS_ROOT),
        help=f"Direktori yang berisi variant dirs (default: {DEFAULT_VARIANTS_ROOT})",
    )
    parser.add_argument(
        "--variants",
        type=str,
        default=None,
        help="Nama variant yang dijalankan, pisah koma (default: semua). "
             "Contoh: --variants after-refactor-f8d34b0,pre-refactor-1dd55d9",
    )
    parser.add_argument(
        "--test-path",
        type=str,
        nargs="+",
        default=[str(DEFAULT_TEST_PATH)],
        help=f"Satu atau lebih direktori YAML skenario (default: {DEFAULT_TEST_PATH}). "
             "Contoh: --test-path seeknal/tests/v1/singleturn/CB seeknal/tests/v1/singleturn/NIE",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maksimum jumlah skenario per --test-path directory (diambil dari awal). "
             "Contoh: --limit 3 berarti 3 skenario dari tiap direktori.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Filter skenario berdasarkan nama/scenario_id (substring). "
             "Contoh: --scenario CLARIF  atau  --scenario CLARIF-BAYI-1",
    )
    parser.add_argument(
        "--no-auto-clarif",
        action="store_true",
        default=False,
        help=(
            "Matikan auto-clarif. Default: auto-clarif AKTIF — ketika agent memanggil "
            "request_clarification, script otomatis inject opsi recommended dan lanjutkan "
            "sehingga jawaban akhir tertangkap. Gunakan flag ini hanya untuk debug gate."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Jumlah scenario (pertanyaan) yang jalan bersamaan (default: 1). "
            "Variant untuk setiap scenario SELALU paralel. "
            "Total sesi LLM = workers × jumlah_variant. "
            "Contoh: --workers 4 dengan 4 variant = 16 sesi paralel."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        metavar="SECONDS",
        help="Timeout per (scenario × variant) run (default: 300s).",
    )
    # [G7] Argumen mode worker-subprocess — dipakai INTERNAL oleh
    # _run_scenario_batch, bukan untuk dipanggil manusia. Disembunyikan dari
    # --help. Worker menjalankan SATU (scenario × variant) lalu keluar;
    # parent yang memegang deadline dan berhak kill.
    parser.add_argument("--single-scenario-file", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--single-variant", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--single-out", type=str, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    from seeknal.cli.ask import _load_project_env
    _load_project_env(PROJECT_ROOT)

    # [G7] Cabang mode worker: jalankan satu pasangan, tulis hasil JSON, keluar.
    if args.single_scenario_file:
        if not (args.single_variant and args.single_out):
            log.error("--single-scenario-file membutuhkan --single-variant dan --single-out")
            sys.exit(2)
        _w_scenario = _scenario_from_dict(
            json.loads(Path(args.single_scenario_file).read_text(encoding="utf-8"))
        )
        _w_result, _w_captured = _run_scenario_for_variant(
            _w_scenario, Path(args.single_variant), auto_clarif=not args.no_auto_clarif,
        )
        # Log buffer dicetak ke stdout (parent mengarahkannya ke file log per-job).
        print(_w_captured, end="", flush=True)
        Path(args.single_out).write_text(
            json.dumps(_scenario_result_to_dict(_w_result), ensure_ascii=False),
            encoding="utf-8",
        )
        sys.exit(0)

    # Discover & select variants
    variants_root = Path(args.variants_path)
    all_variants = _discover_variants(variants_root)
    if not all_variants:
        log.error("Tidak ada variant dir di %s", variants_root)
        sys.exit(1)

    selected_names = [v.strip() for v in args.variants.split(",")] if args.variants else None
    variants = _select_variants(all_variants, selected_names)
    if not variants:
        log.error("Tidak ada variant yang cocok.")
        sys.exit(1)

    # Load & filter scenarios (supports multiple --test-path values)
    scenarios: list[Scenario] = []
    for tp in args.test_path:
        batch = _load_yaml_tests(Path(tp))
        batch = _filter_scenarios(batch, args.scenario)
        if args.limit is not None:
            batch = batch[: args.limit]
        scenarios.extend(batch)
    if not scenarios:
        log.error("Tidak ada skenario yang cocok.")
        sys.exit(1)

    log.info("Project root : %s", PROJECT_ROOT)
    log.info("Test path(s) : %s", args.test_path)
    log.info("Variants     : %d  %s", len(variants), [v.name for v in variants])
    log.info("Scenarios    : %d", len(scenarios))
    log.info("Workers      : %d scenario(s) × %d variant(s) = %d concurrent", args.workers, len(variants), args.workers * len(variants))
    auto_clarif = not args.no_auto_clarif
    log.info("auto-clarif  : %s", auto_clarif)

    # Run
    results = run_all_variants(
        scenarios=scenarios,
        variants=variants,
        workers=args.workers,
        scenario_timeout=args.timeout,
        auto_clarif=auto_clarif,
    )

    # Output
    print_comparison(results, scenarios, variants)
    output_path = save_json(results, scenarios, variants, scenario_filter=args.scenario)
    log.info("Output saved : %s", output_path)

    trace_dir = output_path.parent / output_path.stem.replace("variant_compare_results_", "")
    save_trace_files(results, scenarios, variants, trace_dir)
    log.info("Trace files  : %s/_index.md", trace_dir)
