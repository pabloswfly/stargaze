from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request

from stargaze import astronomy, config
from stargaze.models import (
    ConstellationOut,
    ConstellationPoint,
    MoonOut,
    ObserverInfo,
    PlanetOut,
    SkyResponse,
    StarOut,
    SunOut,
)

router = APIRouter()


@router.get("/api/sky", response_model=SkyResponse)
def get_sky(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    elevation: float = Query(0.0),
    time: datetime | None = Query(None),
    mag_limit: float = Query(config.DEFAULT_MAG_LIMIT, ge=-2.0, le=config.MAX_MAG_LIMIT),
) -> SkyResponse:
    ctx: astronomy.SkyContext = request.app.state.sky_context
    star_names: dict = request.app.state.star_names
    constellation_lines: dict = request.app.state.constellation_lines

    when = time if time is not None else datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)

    t, at = ctx.observer_at(lat, lon, elevation, when)

    star_positions = astronomy.compute_star_positions(ctx, at)
    positions_by_hip = {s.hip: s for s in star_positions}

    stars_out = [
        StarOut(
            hip=s.hip,
            name=star_names.get(str(s.hip), {}).get("name"),
            alt=s.alt_degrees,
            az=s.az_degrees,
            mag=s.magnitude,
        )
        for s in star_positions
        if s.magnitude <= mag_limit
    ]

    planets = astronomy.compute_planet_positions(ctx, at)
    planets_out = [
        PlanetOut(name=name, alt=p.alt_degrees, az=p.az_degrees, mag=p.magnitude)
        for name, p in planets.items()
    ]

    sun = astronomy.compute_sun(ctx, at)
    moon = astronomy.compute_moon(ctx, at, t)

    constellations_out = []
    for abbr, entry in constellation_lines.items():
        lines_out = []
        for line in entry["lines"]:
            points = []
            for hip_str in line:
                pos = positions_by_hip.get(int(hip_str))
                if pos is not None:
                    points.append(
                        ConstellationPoint(hip=pos.hip, alt=pos.alt_degrees, az=pos.az_degrees)
                    )
            if len(points) >= 2:
                lines_out.append(points)
        constellations_out.append(ConstellationOut(abbr=abbr, name=entry["name"], lines=lines_out))

    return SkyResponse(
        observer=ObserverInfo(lat=lat, lon=lon, elevation=elevation, time=when),
        stars=stars_out,
        planets=planets_out,
        sun=SunOut(alt=sun.alt_degrees, az=sun.az_degrees),
        moon=MoonOut(
            alt=moon.alt_degrees,
            az=moon.az_degrees,
            phase_angle=moon.phase_angle_degrees,
            illuminated_fraction=moon.illuminated_fraction,
        ),
        constellations=constellations_out,
    )
