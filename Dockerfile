FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /app

# Install dependencies first, as their own cached layer, before copying the
# rest of the project (so editing app code doesn't invalidate this layer).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Bake the Skyfield ephemeris (de421.bsp) and Hipparcos star catalog into the
# image at build time, so the running container never needs outbound network
# access to serve requests (see README: "First run: one-time data download").
RUN python scripts/prefetch_data.py

EXPOSE 8000

# Shell form so $PORT (set by the host platform, e.g. Render) is expanded;
# falls back to 8000 for a plain `docker run` with no PORT set.
CMD ["sh", "-c", "uvicorn stargaze.app:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
