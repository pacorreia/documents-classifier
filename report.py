"""CSV writing and console leaderboard display."""

import csv
from pathlib import Path


def write_csv(rows: list[dict], csv_path: Path) -> None:
    fieldnames = [
        "filename",
        "result",
        "score",
        "must_score",
        "nice_score",
        "matched_must",
        "missing_must",
        "matched_nice",
        "summary",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV report → {csv_path}")


def print_leaderboard(rows: list[dict], top_n: int, bottom_n: int) -> None:
    """Print top-N and bottom-N leaderboard tables from scored rows."""
    scored = [r for r in rows if r["result"] in ("PASS", "FAIL")]
    if not scored:
        return

    def _sort_key(r: dict, ascending: bool) -> tuple:
        s = float(r["score"])
        must_count = len(r["matched_must"].split("; ")) if r["matched_must"] else 0
        nice_count = len(r["matched_nice"].split("; ")) if r["matched_nice"] else 0
        sign = 1 if ascending else -1
        return (sign * s, sign * must_count, sign * nice_count, r["filename"])

    sorted_desc = sorted(scored, key=lambda r: _sort_key(r, ascending=False))
    sorted_asc  = sorted(scored, key=lambda r: _sort_key(r, ascending=True))

    col_w = max(len(r["filename"]) for r in scored) + 2

    def _print_table(title: str, entries: list[dict]) -> None:
        print(f"\n{title}")
        print(f"  {'#':<4} {'Filename':<{col_w}} {'Score':>7}  {'Must':>6}  {'Nice':>6}  {'Result':<6}  {'Must matched':<30}  Nice matched")
        print(f"  {'-'*4} {'-'*col_w} {'-'*7}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*30}  ------------")
        for i, r in enumerate(entries, 1):
            must = r["matched_must"] or "—"
            nice = r["matched_nice"] or "—"
            print(
                f"  {i:<4} {r['filename']:<{col_w}} {float(r['score']):>7.3f}"
                f"  {float(r.get('must_score', 0)):>6.3f}  {float(r.get('nice_score', 0)):>6.3f}"
                f"  {r['result']:<6}  {must:<30}  {nice}"
            )

    top_entries    = sorted_desc[:top_n]
    bottom_entries = [r for r in sorted_asc[:bottom_n] if r not in top_entries]

    _print_table(f"Top {top_n} highest-scored document(s):", top_entries)
    if bottom_entries:
        _print_table(f"Bottom {bottom_n} lowest-scored document(s):", bottom_entries)
