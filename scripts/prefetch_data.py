"""One-off: download and cache the JPL ephemeris and Hipparcos catalog that
Skyfield needs at runtime, without starting the app. Useful to run ahead of
time on a slow connection, or to warm var/skyfield-data/ before a demo.
"""

from stargaze.astronomy import SkyContext


def main() -> None:
    print("Downloading/caching de421.bsp and the Hipparcos catalog...")
    SkyContext()
    print("Done -- cached under var/skyfield-data/")


if __name__ == "__main__":
    main()
