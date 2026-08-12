"""One-off script: fetch Dominic Ford's (dcf21) constellation stick-figure
data and derive data/constellation_lines.json, mapping the IAU 3-letter
constellation abbreviation to its full name and the Hipparcos-ID polylines
used to draw its stick figure.

Source: https://github.com/dcf21/constellation-stick-figures (GPLv3+, see
data/THIRD_PARTY_LICENSES.md). Not run at app startup -- run manually when
refreshing the curated dataset, then commit the resulting JSON.
"""

import json
import re
import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/dcf21/constellation-stick-figures/master"
LINES_URL = f"{BASE_URL}/constellation_lines_iau.dat"
NAMES_URL = f"{BASE_URL}/constellation_names.dat"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "constellation_lines.json"

# The stick-figure file splits Serpens into two stick figures (head/tail)
# that don't textually match constellation_names.dat's "SerpensCaput" /
# "SerpensCauda" -- merge them back into a single "Ser" / "Serpens" entry.
HEADER_OVERRIDES = {"SerpensA": "Ser", "SerpensB": "Ser"}

# IAU abbreviations that use internal capitals; str.title() would otherwise
# flatten these to e.g. "Cma" instead of the conventional "CMa".
ABBR_CASING = {
    "Cma": "CMa",
    "Cmi": "CMi",
    "Cvn": "CVn",
    "Cra": "CrA",
    "Crb": "CrB",
    "Lmi": "LMi",
    "Psa": "PsA",
    "Tra": "TrA",
    "Uma": "UMa",
    "Umi": "UMi",
}


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_abbreviations(names_text: str) -> dict[str, str]:
    """Return {full_name_no_spaces: 3-letter abbreviation}."""
    mapping = {}
    for line in names_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        abbr, full_name = parts[0], parts[1]
        # Skip the split Serpens rows (SER1/SER2); handled via HEADER_OVERRIDES.
        if abbr in ("SER1", "SER2"):
            continue
        titled = abbr[:3].title()
        mapping[full_name] = ABBR_CASING.get(titled, titled)
    return mapping


def pretty_name(compact_name: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", compact_name)


def parse_lines(lines_text: str) -> dict[str, list[str]]:
    """Return {compact_constellation_name: [raw polyline text, ...]}."""
    sections: dict[str, list[str]] = {}
    current = None
    for raw_line in lines_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("*"):
            current = line.lstrip("*").strip()
            sections.setdefault(current, [])
            continue
        if line.startswith("[") and current is not None:
            sections[current].append(line)
    return sections


def parse_polyline(raw: str) -> list[str]:
    hip_ids = json.loads(raw)
    # Some entries mark a borrowed star with a trailing "*"; strip it.
    return [hip.rstrip("*") for hip in hip_ids]


def build_constellations(lines_text: str, names_text: str) -> dict:
    abbr_by_name = parse_abbreviations(names_text)
    sections = parse_lines(lines_text)

    result: dict[str, dict] = {}
    for compact_name, raw_polylines in sections.items():
        if compact_name in HEADER_OVERRIDES:
            abbr = HEADER_OVERRIDES[compact_name]
            full_name = "Serpens"
        else:
            abbr = abbr_by_name.get(compact_name)
            if abbr is None:
                raise ValueError(f"no abbreviation found for constellation {compact_name!r}")
            full_name = pretty_name(compact_name)

        entry = result.setdefault(abbr, {"name": full_name, "lines": []})
        for raw in raw_polylines:
            entry["lines"].append(parse_polyline(raw))

    return result


def main() -> None:
    lines_text = fetch_text(LINES_URL)
    names_text = fetch_text(NAMES_URL)
    constellations = build_constellations(lines_text, names_text)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(constellations, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(constellations)} constellations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
