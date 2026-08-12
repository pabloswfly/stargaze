"""One-off script: fetch the IAU Working Group on Star Names' Catalog of Star
Names (IAU-CSN) and derive data/star_names.json, mapping Hipparcos ID -> the
star's common name, Bayer/Flamsteed designation, and constellation.

Not run at app startup -- run manually when the curated dataset needs
refreshing, then commit the resulting data/star_names.json.
"""

import json
import urllib.request
from pathlib import Path

SOURCE_URL = "https://www.pas.rochester.edu/~emamajek/WGSN/IAU-CSN.txt"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "star_names.json"

FIELDS = [
    "name",
    "name_dia",
    "designation",
    "bayer_ascii",
    "bayer_diacritic",
    "con",
    "component",
    "wds",
    "mag",
    "band",
    "hip",
    "hd",
    "ra",
    "dec",
    "date",
    "notes",
]


def fetch_lines() -> list[str]:
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    return text.splitlines()


def find_header_index(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if line.startswith("#Name/ASCII"):
            return i
    raise ValueError("could not find IAU-CSN header row")


def infer_column_starts(data_rows: list[str]) -> list[int]:
    """Fixed-width columns: find character positions where every data row has
    a non-space char preceded by an all-space column (or the start of line).
    """
    max_len = max(len(row) for row in data_rows)
    padded = [row.ljust(max_len) for row in data_rows]
    all_space = [all(row[c] == " " for row in padded) for c in range(max_len)]
    starts = []
    in_field = False
    for c in range(max_len):
        if not all_space[c] and not in_field:
            starts.append(c)
            in_field = True
        elif all_space[c]:
            in_field = False
    return starts


def parse_rows(lines: list[str]) -> list[dict]:
    header_idx = find_header_index(lines)
    data_lines = [
        line for line in lines[header_idx + 1 :] if line.strip() and not line.startswith("#")
    ]
    starts = infer_column_starts(data_lines)
    if len(starts) != len(FIELDS):
        raise ValueError(f"expected {len(FIELDS)} columns, inferred {len(starts)}: {starts}")
    bounds = [*starts, None]
    records = []
    for line in data_lines:
        rec = {
            field: line[bounds[i] : bounds[i + 1]].strip() for i, field in enumerate(FIELDS)
        }
        records.append(rec)
    return records


def build_star_names(records: list[dict]) -> dict:
    result = {}
    for rec in records:
        hip = rec["hip"]
        if not hip or hip == "_" or not hip.isdigit():
            continue
        bayer = rec["bayer_ascii"] if rec["bayer_ascii"] and rec["bayer_ascii"] != "_" else None
        con = rec["con"] if rec["con"] and rec["con"] != "_" else None
        entry = {"name": rec["name"]}
        if bayer and con:
            entry["bayer"] = f"{bayer} {con}"
        if con:
            entry["con"] = con
        # Later rows shouldn't override an existing HIP, but keep the first
        # (file is ordered alphabetically by name; ties are rare/nonexistent).
        result.setdefault(hip, entry)
    return result


def main() -> None:
    lines = fetch_lines()
    records = parse_rows(lines)
    star_names = build_star_names(records)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(star_names, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(star_names)} star names to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
