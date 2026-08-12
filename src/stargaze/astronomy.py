"""Skyfield-backed astronomy computations: given an observer's location and
a time, compute the topocentric alt/az of stars, planets, the Sun, and the
Moon. All the astronomy happens server-side; callers (the API layer) get
plain alt/az degrees back and don't need to know anything about Skyfield.
"""

from dataclasses import dataclass
from datetime import datetime

from skyfield import almanac
from skyfield.api import Loader, Star, wgs84
from skyfield.data import hipparcos
from skyfield.magnitudelib import planetary_magnitude
from skyfield.timelib import Time

from stargaze import config

# A handful of Hipparcos entries ("problem stars" with an unreliable 5-parameter
# astrometric solution) have their computed ICRS ra_degrees/dec_degrees blank in
# the standard catalog file, even though the original input-catalog sexagesimal
# position is present. HIP 55203 (11h18m11.24s +31d31'50.8", from the raw
# hip_main.dat record) is needed for the Ursa Major stick figure, so it's
# restored here rather than silently dropped.
HIP_POSITION_OVERRIDES: dict[int, tuple[float, float]] = {
    55203: (169.54683333333335, 31.530777777777775),
}

PLANET_TARGETS = {
    "Mercury": "MERCURY",
    "Venus": "VENUS",
    "Mars": "MARS",
    "Jupiter": "JUPITER_BARYCENTER",
    "Saturn": "SATURN_BARYCENTER",
    "Uranus": "URANUS_BARYCENTER",
    "Neptune": "NEPTUNE_BARYCENTER",
}


@dataclass
class StarPosition:
    hip: int
    alt_degrees: float
    az_degrees: float
    magnitude: float


@dataclass
class BodyPosition:
    alt_degrees: float
    az_degrees: float


@dataclass
class PlanetPosition(BodyPosition):
    magnitude: float


@dataclass
class MoonPosition(BodyPosition):
    phase_angle_degrees: float
    illuminated_fraction: float


class SkyContext:
    """Everything loaded once at startup: ephemeris, timescale, and the
    filtered star catalog (as both a dataframe and a vectorized Star
    object, indexed identically by position)."""

    def __init__(self, data_dir=config.SKYFIELD_DATA_DIR, extra_hips: frozenset[int] = frozenset()):
        loader = Loader(str(data_dir))
        self.ts = loader.timescale()
        self.eph = loader(config.EPHEMERIS_FILE)
        self.earth = self.eph["earth"]
        self.sun = self.eph["sun"]
        self.moon = self.eph["moon"]
        self.planets = {name: self.eph[target] for name, target in PLANET_TARGETS.items()}

        with loader.open(hipparcos.URL) as f:
            df = hipparcos.load_dataframe(f)
        for hip, (ra_degrees, dec_degrees) in HIP_POSITION_OVERRIDES.items():
            if hip in df.index:
                df.loc[hip, "ra_degrees"] = ra_degrees
                df.loc[hip, "dec_degrees"] = dec_degrees
                df.loc[hip, "ra_hours"] = ra_degrees / 15.0
        mask = (df["magnitude"] <= config.MAX_MAG_LIMIT) | df.index.isin(extra_hips)
        self.star_df = df[mask].dropna(subset=["ra_degrees", "dec_degrees"]).copy()
        # Many faint/distant stars have no measured parallax; Skyfield's own
        # docs recommend treating that as "effectively at infinity" (0 mas)
        # rather than leaving it NaN, which otherwise corrupts the vectorized
        # light-time/deflection calculation for the whole star array.
        self.star_df["parallax_mas"] = self.star_df["parallax_mas"].fillna(0)
        self.star_df["ra_mas_per_year"] = self.star_df["ra_mas_per_year"].fillna(0)
        self.star_df["dec_mas_per_year"] = self.star_df["dec_mas_per_year"].fillna(0)
        self.stars = Star.from_dataframe(self.star_df)

    def observer_at(self, lat: float, lon: float, elevation_m: float, when: datetime):
        t = self.ts.from_datetime(when)
        topos = wgs84.latlon(lat, lon, elevation_m)
        position = self.earth + topos
        return t, position.at(t)


def compute_star_positions(ctx: SkyContext, at) -> list[StarPosition]:
    apparent = at.observe(ctx.stars).apparent()
    alt, az, _ = apparent.altaz()
    return [
        StarPosition(
            hip=int(hip),
            alt_degrees=float(a),
            az_degrees=float(z),
            magnitude=float(mag),
        )
        for hip, a, z, mag in zip(
            ctx.star_df.index, alt.degrees, az.degrees, ctx.star_df["magnitude"], strict=True
        )
    ]


def compute_planet_positions(ctx: SkyContext, at) -> dict[str, PlanetPosition]:
    result = {}
    for name, body in ctx.planets.items():
        astrometric = at.observe(body)
        alt, az, _ = astrometric.apparent().altaz()
        mag = float(planetary_magnitude(astrometric))
        result[name] = PlanetPosition(
            alt_degrees=float(alt.degrees), az_degrees=float(az.degrees), magnitude=mag
        )
    return result


def compute_sun(ctx: SkyContext, at) -> BodyPosition:
    alt, az, _ = at.observe(ctx.sun).apparent().altaz()
    return BodyPosition(alt_degrees=float(alt.degrees), az_degrees=float(az.degrees))


def compute_moon(ctx: SkyContext, at, t: Time) -> MoonPosition:
    alt, az, _ = at.observe(ctx.moon).apparent().altaz()
    phase_angle = almanac.moon_phase(ctx.eph, t)
    illuminated = almanac.fraction_illuminated(ctx.eph, "moon", t)
    return MoonPosition(
        alt_degrees=float(alt.degrees),
        az_degrees=float(az.degrees),
        phase_angle_degrees=float(phase_angle.degrees),
        illuminated_fraction=float(illuminated),
    )
