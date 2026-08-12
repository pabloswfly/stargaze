from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
SKYFIELD_DATA_DIR = ROOT_DIR / "var" / "skyfield-data"
STATIC_DIR = ROOT_DIR / "static"

STAR_NAMES_PATH = DATA_DIR / "star_names.json"
CONSTELLATION_LINES_PATH = DATA_DIR / "constellation_lines.json"

EPHEMERIS_FILE = "de421.bsp"

DEFAULT_MAG_LIMIT = 6.0
MAX_MAG_LIMIT = 8.0
