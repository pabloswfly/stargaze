from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from stargaze import astronomy, catalog, config
from stargaze.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    constellation_lines = catalog.load_constellation_lines()
    extra_hips = catalog.all_constellation_hips(constellation_lines)
    app.state.sky_context = astronomy.SkyContext(extra_hips=extra_hips)
    app.state.star_names = catalog.load_star_names()
    app.state.constellation_lines = constellation_lines
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Stargaze", lifespan=lifespan)
    app.include_router(api_router)
    app.mount("/", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="static")
    return app


app = create_app()
