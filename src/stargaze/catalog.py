"""Loads the bundled curated data (star names, constellation lines)."""

import json

from stargaze import config


def load_star_names() -> dict[str, dict]:
    with config.STAR_NAMES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_constellation_lines() -> dict[str, dict]:
    with config.CONSTELLATION_LINES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def all_constellation_hips(constellation_lines: dict[str, dict]) -> frozenset[int]:
    """Every HIP ID referenced by any constellation stick figure -- some of
    these are fainter than the app's default display magnitude cutoff, but
    they're still needed to draw the lines, so the star catalog must always
    include them regardless of the requested magnitude filter."""
    hips: set[int] = set()
    for entry in constellation_lines.values():
        for line in entry["lines"]:
            hips.update(int(hip) for hip in line)
    return frozenset(hips)
