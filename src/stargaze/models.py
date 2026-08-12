from datetime import datetime

from pydantic import BaseModel


class ObserverInfo(BaseModel):
    lat: float
    lon: float
    elevation: float
    time: datetime


class StarOut(BaseModel):
    hip: int
    name: str | None
    alt: float
    az: float
    mag: float


class PlanetOut(BaseModel):
    name: str
    alt: float
    az: float
    mag: float


class SunOut(BaseModel):
    alt: float
    az: float


class MoonOut(BaseModel):
    alt: float
    az: float
    phase_angle: float
    illuminated_fraction: float


class ConstellationPoint(BaseModel):
    hip: int
    alt: float
    az: float


class ConstellationOut(BaseModel):
    abbr: str
    name: str
    lines: list[list[ConstellationPoint]]


class SkyResponse(BaseModel):
    observer: ObserverInfo
    stars: list[StarOut]
    planets: list[PlanetOut]
    sun: SunOut
    moon: MoonOut
    constellations: list[ConstellationOut]
