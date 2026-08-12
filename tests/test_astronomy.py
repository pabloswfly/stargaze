import datetime as dt

from stargaze import astronomy

GREENWICH_LAT = 51.4769
GREENWICH_LON = 0.0
SIRIUS_HIP = 32349


def test_sun_altitude_near_equinox_local_noon(sky_context):
    # At local solar noon near the equinox, the Sun's altitude should be
    # close to (90 - latitude), and it should sit close to due south (180 deg
    # azimuth) as seen from the northern hemisphere.
    when = dt.datetime(2026, 3, 20, 12, 0, 0, tzinfo=dt.UTC)
    _, at = sky_context.observer_at(GREENWICH_LAT, GREENWICH_LON, 0.0, when)
    sun = astronomy.compute_sun(sky_context, at)

    expected_altitude = 90 - GREENWICH_LAT
    assert abs(sun.alt_degrees - expected_altitude) < 1.0
    assert abs(sun.az_degrees - 180) < 5.0


def test_sirius_matches_catalog_magnitude(sky_context):
    when = dt.datetime(2026, 1, 1, 22, 0, 0, tzinfo=dt.UTC)
    _, at = sky_context.observer_at(GREENWICH_LAT, GREENWICH_LON, 0.0, when)
    stars = astronomy.compute_star_positions(sky_context, at)

    sirius = next(s for s in stars if s.hip == SIRIUS_HIP)
    # Sirius, the brightest star in the sky, has a well-known magnitude
    # around -1.46; our catalog copy should be within a few hundredths.
    assert abs(sirius.magnitude - (-1.46)) < 0.1
    assert -90 <= sirius.alt_degrees <= 90
    assert 0 <= sirius.az_degrees < 360


def test_moon_phase_is_physically_plausible(sky_context):
    when = dt.datetime(2026, 6, 15, 3, 0, 0, tzinfo=dt.UTC)
    t, at = sky_context.observer_at(GREENWICH_LAT, GREENWICH_LON, 0.0, when)
    moon = astronomy.compute_moon(sky_context, at, t)

    assert 0 <= moon.illuminated_fraction <= 1
    assert 0 <= moon.phase_angle_degrees < 360
    assert -90 <= moon.alt_degrees <= 90
    assert 0 <= moon.az_degrees < 360


def test_outer_planet_magnitudes_are_in_expected_ranges(sky_context):
    # Outer planet brightness barely changes year to year, so a loose bound
    # is a good regression guard against a broken magnitude computation.
    when = dt.datetime(2026, 6, 15, 3, 0, 0, tzinfo=dt.UTC)
    _, at = sky_context.observer_at(GREENWICH_LAT, GREENWICH_LON, 0.0, when)
    planets = astronomy.compute_planet_positions(sky_context, at)

    assert -3.5 < planets["Jupiter"].magnitude < -1.0
    assert -1.0 < planets["Saturn"].magnitude < 2.0
    assert 5.0 < planets["Uranus"].magnitude < 6.5
    assert 7.0 < planets["Neptune"].magnitude < 8.5
    for name, planet in planets.items():
        assert -90 <= planet.alt_degrees <= 90, name
        assert 0 <= planet.az_degrees < 360, name
