from stargaze import catalog


def test_star_names_load_and_have_expected_shape():
    names = catalog.load_star_names()
    assert len(names) > 300
    sirius = next(v for v in names.values() if v["name"] == "Sirius")
    assert sirius["con"] == "CMa"


def test_star_names_keys_are_numeric_hip_strings():
    names = catalog.load_star_names()
    for hip in names:
        assert hip.isdigit()


def test_constellation_lines_load_and_have_expected_shape():
    lines = catalog.load_constellation_lines()
    assert len(lines) == 88
    orion = lines["Ori"]
    assert orion["name"] == "Orion"
    assert len(orion["lines"]) > 0
    for line in orion["lines"]:
        assert len(line) >= 2
        for hip in line:
            assert hip.isdigit()


def test_all_constellation_hips_returns_nonempty_int_set():
    lines = catalog.load_constellation_lines()
    hips = catalog.all_constellation_hips(lines)
    assert len(hips) > 300
    assert all(isinstance(h, int) for h in hips)


def test_constellation_hips_exist_in_star_catalog(sky_context):
    lines = catalog.load_constellation_lines()
    hips = catalog.all_constellation_hips(lines)
    missing = hips - set(sky_context.star_df.index)
    assert not missing, f"constellation-line HIPs missing from catalog: {missing}"
