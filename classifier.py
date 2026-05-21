#!/usr/bin/env python3
"""
Document Classifier — LLM-powered keyword presence scoring.

Uses the GitHub Models API (Azure AI Inference) via the openai SDK.
Requires:  GITHUB_TOKEN environment variable with access to GitHub Models.

Usage:
    python classifier.py /path/to/documents/folder [--config config.yaml] [--no-llm]
"""

import os
import shutil
import sys
import argparse
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from openai import OpenAI

from extractor import extract_text
from classifiers import classify_doc, classify_doc_keyword
from scoring import calculate_score
from config import load_config, validate_config
from report import write_csv, print_leaderboard

# When compiled with PyInstaller --onefile, __file__ lives inside a temp dir.
# Use the directory of the binary itself instead.
_BASE_DIR = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).parent
)


def _parse_keyword_groups(entries: list[str]) -> list[list[str]]:
    """Split each config entry on commas to build a list of OR-alternative groups.

    E.g. "network, networking" → ["network", "networking"].
    Duplicate entries are silently dropped.
    """
    seen: set[str] = set()
    groups: list[list[str]] = []
    for entry in entries:
        if not isinstance(entry, str) or entry in seen:
            continue
        seen.add(entry)
        alts = [a.strip() for a in entry.split(",") if a.strip()]
        if alts:
            groups.append(alts)
    return groups


def _process_one(
    doc_path: Path,
    client,
    model: str | None,
    no_llm: bool,
    must_keywords_flat: list[str],
    nice_keywords_flat: list[str],
    must_groups: list[list[str]],
    nice_groups: list[list[str]],
    must_weight: float,
    nice_weight: float,
    pass_threshold: float,
    must_known: set[str],
    nice_known: set[str],
) -> tuple[dict, str]:
    """Process a single document. Thread-safe. Returns (row_dict, display_line)."""
    prefix = f"  ► {doc_path.name}"
    try:
        text = extract_text(doc_path)
        if not text.strip():
            return (
                {
                    "filename": doc_path.name,
                    "result": "SKIP",
                    "score": "0.000",
                    "matched_must": "",
                    "missing_must": "",
                    "matched_nice": "",
                    "summary": "No text could be extracted from this file.",
                },
                f"{prefix} … SKIPPED (no text extracted)",
            )

        result = (
            classify_doc_keyword(text, must_keywords_flat, nice_keywords_flat)
            if no_llm
            else classify_doc(client, model, text, must_keywords_flat, nice_keywords_flat)
        )

        matched_must_raw = result.get("matched_must", [])
        matched_must: list[str] = (
            [k for k in matched_must_raw if isinstance(k, str)]
            if isinstance(matched_must_raw, list)
            else []
        )
        matched_nice_raw = result.get("matched_nice", [])
        matched_nice: list[str] = (
            [k for k in matched_nice_raw if isinstance(k, str)]
            if isinstance(matched_nice_raw, list)
            else []
        )
        matched_must = [k for k in matched_must if k in must_known]
        matched_nice = [k for k in matched_nice if k in nice_known]
        result["matched_must"] = matched_must
        result["matched_nice"] = matched_nice

        score, must_score, nice_score = calculate_score(result, must_groups, nice_groups, must_weight, nice_weight)
        passed = score >= pass_threshold
        matched_must_set = set(matched_must)
        missing_must_labels = [
            "/".join(group) for group in must_groups
            if not any(alt in matched_must_set for alt in group)
        ]

        return (
            {
                "filename": doc_path.name,
                "result": "PASS" if passed else "FAIL",
                "score": f"{score:.3f}",
                "must_score": f"{must_score:.3f}",
                "nice_score": f"{nice_score:.3f}",
                "matched_must": "; ".join(matched_must),
                "missing_must": "; ".join(missing_must_labels),
                "matched_nice": "; ".join(matched_nice),
                "summary": result.get("summary", ""),
            },
            f"{prefix} … {'PASS' if passed else 'FAIL'}  score={score:.3f}  (must={must_score:.3f}  nice={nice_score:.3f})",
        )

    except Exception as exc:  # noqa: BLE001
        return (
            {
                "filename": doc_path.name,
                "result": "ERROR",
                "score": "0.000",
                "must_score": "0.000",
                "nice_score": "0.000",
                "matched_must": "",
                "missing_must": "",
                "matched_nice": "",
                "summary": str(exc),
            },
            f"{prefix} … ERROR — {exc}",
        )


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify documents (PDF/.docx) using an LLM keyword scorer."
    )
    parser.add_argument("doc_folder", help="Folder containing document files")
    parser.add_argument(
        "--config",
        default=str(_BASE_DIR / "config.yaml"),
        help="Path to config.yaml (default: config.yaml next to this script)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use fast regex keyword matching instead of the LLM (no GITHUB_TOKEN required)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Number of parallel workers (overrides output.workers in config, default: 4)",
    )
    args = parser.parse_args()

    if args.workers is not None and args.workers < 1:
        print("Error: --workers must be >= 1", file=sys.stderr)
        sys.exit(1)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        print("Create one or pass --config /path/to/config.yaml", file=sys.stderr)
        sys.exit(1)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error: cannot read {args.config}: {exc}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f"Error: invalid YAML in {args.config}: {exc}", file=sys.stderr)
        sys.exit(1)

    config_errors = validate_config(cfg)
    if config_errors:
        print(f"Config error(s) in {args.config}:", file=sys.stderr)
        for err in config_errors:
            print(f"  • {err}", file=sys.stderr)
        sys.exit(1)

    must_groups: list[list[str]] = _parse_keyword_groups(cfg.get("must_keywords", []))
    nice_groups: list[list[str]] = _parse_keyword_groups(cfg.get("nice_keywords", []))
    # Flat lists used by classifiers — deduplicated to avoid sending duplicate keywords
    # to the LLM when two groups share an alternative (e.g. "network, networking" and
    # "networking, wifi" both contribute "networking").
    must_keywords_flat: list[str] = list(dict.fromkeys(alt for g in must_groups for alt in g))
    nice_keywords_flat: list[str] = list(dict.fromkeys(alt for g in nice_groups for alt in g))
    must_weight: float = float(cfg.get("must_weight", 0.7))
    nice_weight: float = float(cfg.get("nice_weight", 0.3))
    pass_threshold: float = float(cfg.get("pass_threshold", 0.6))

    # ── LLM client ────────────────────────────────────────────────────────────
    client: OpenAI | None = None
    model: str | None = None

    if not args.no_llm:
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
            print(
                "Generate a token at https://github.com/settings/tokens "
                "with GitHub Models access enabled.",
                file=sys.stderr,
            )
            print("Tip: run with --no-llm for offline keyword matching.", file=sys.stderr)
            sys.exit(1)

        llm_cfg = cfg.get("llm") or {}
        client = OpenAI(
            base_url=llm_cfg.get("endpoint", "https://models.inference.ai.azure.com"),
            api_key=github_token,
        )
        model = llm_cfg.get("model", "gpt-4o-mini")

    # ── Paths ─────────────────────────────────────────────────────────────────
    doc_folder = Path(args.doc_folder).resolve()
    if not doc_folder.is_dir():
        print(f"Error: Document folder not found or not a directory: {doc_folder}", file=sys.stderr)
        sys.exit(1)
    out_cfg = cfg.get("output") or {}
    pass_dir = doc_folder / out_cfg.get("pass_folder", "classified/pass")
    fail_dir = doc_folder / out_cfg.get("fail_folder", "classified/fail")
    csv_path = pass_dir.parent / out_cfg.get("csv_file", "results.csv")
    copy_mode: bool = bool(out_cfg.get("copy_files", True))

    try:
        top_n: int = int(out_cfg.get("top_n", 3))
        bottom_n: int = int(out_cfg.get("bottom_n", 3))
    except (TypeError, ValueError) as exc:
        print(f"Error: invalid output.top_n/bottom_n in {args.config}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Clear output dirs so stale results from previous runs don't accumulate.
    for _d in (pass_dir, fail_dir):
        if _d.exists():
            shutil.rmtree(_d)
        _d.mkdir(parents=True, exist_ok=True)

    # ── Collect document files (skip output sub-folders) ────────────────────────
    doc_files = [
        f
        for f in doc_folder.iterdir()
        if f.is_file() and f.suffix.lower() in (".pdf", ".docx", ".doc")
    ]

    if not doc_files:
        print("No PDF or .docx files found in", doc_folder)
        sys.exit(0)

    mode_label = "keyword matching (no LLM)" if args.no_llm else f"LLM ({model})"
    print(f"Found {len(doc_files)} document(s) — mode: {mode_label}")
    must_display = ["/".join(g) for g in must_groups]
    nice_display = ["/".join(g) for g in nice_groups]
    print(f"Must-have keywords : {', '.join(must_display)}")
    print(f"Nice-to-have       : {', '.join(nice_display)}")
    print(f"Pass threshold     : {pass_threshold}\n")

    must_known: set[str] = set(must_keywords_flat)
    nice_known: set[str] = set(nice_keywords_flat)

    workers_cfg = int(out_cfg.get("workers", 4))
    workers: int = args.workers if args.workers is not None else workers_cfg

    doc_files_sorted = sorted(doc_files)
    rows_map: dict[str, dict] = {}
    _print_lock = threading.Lock()

    # --no-llm is CPU-bound (PDF parsing): use processes to bypass the GIL.
    # LLM mode is I/O-bound and the OpenAI client is not picklable: use threads.
    Executor = ProcessPoolExecutor if args.no_llm else ThreadPoolExecutor
    with Executor(max_workers=workers) as executor:
        future_to_path = {
            executor.submit(
                _process_one,
                doc_path, client, model, args.no_llm,
                must_keywords_flat, nice_keywords_flat,
                must_groups, nice_groups,
                must_weight, nice_weight, pass_threshold,
                must_known, nice_known,
            ): doc_path
            for doc_path in doc_files_sorted
        }
        for future in as_completed(future_to_path):
            row, line = future.result()
            rows_map[future_to_path[future].name] = row
            with _print_lock:
                print(line)

    rows: list[dict] = [rows_map[p.name] for p in doc_files_sorted]

    # ── Copy/move files with rank prefix (sorted by score, highest first) ─────
    def _rank_key(r: dict) -> tuple:
        return (
            -float(r["score"]),
            -float(r.get("must_score", 0)),
            -float(r.get("nice_score", 0)),
            r["filename"],
        )

    for dest_dir, result_tag in ((pass_dir, "PASS"), (fail_dir, "FAIL")):
        group = sorted([r for r in rows if r["result"] == result_tag], key=_rank_key)
        width = len(str(len(group))) if group else 1
        for rank, row in enumerate(group, 1):
            src = doc_folder / row["filename"]
            dest_name = f"{str(rank).zfill(width)}_{row['filename']}"
            if copy_mode:
                shutil.copy2(src, dest_dir / dest_name)
            else:
                shutil.move(str(src), str(dest_dir / dest_name))

    # ── Write CSV ─────────────────────────────────────────────────────────────
    if rows:
        write_csv(rows, csv_path)

    passed_count = sum(1 for r in rows if r["result"] == "PASS")
    failed_count = sum(1 for r in rows if r["result"] == "FAIL")
    skip_count   = sum(1 for r in rows if r["result"] == "SKIP")
    error_count  = sum(1 for r in rows if r["result"] == "ERROR")
    summary_parts = [f"{passed_count} passed", f"{failed_count} failed"]
    if skip_count:
        summary_parts.append(f"{skip_count} skipped")
    if error_count:
        summary_parts.append(f"{error_count} error(s)")
    print(f"\nSummary: {', '.join(summary_parts)} — threshold={pass_threshold}")

    # ── Leaderboard ───────────────────────────────────────────────────────────
    print_leaderboard(rows, top_n, bottom_n)


if __name__ == "__main__":
    main()
