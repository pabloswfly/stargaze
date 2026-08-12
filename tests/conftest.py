import pytest

from stargaze import astronomy, catalog


@pytest.fixture(scope="session")
def sky_context() -> astronomy.SkyContext:
    constellation_lines = catalog.load_constellation_lines()
    extra_hips = catalog.all_constellation_hips(constellation_lines)
    return astronomy.SkyContext(extra_hips=extra_hips)
