# syntax=docker/dockerfile:1

FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime

# The base image's own system pip/setuptools (from ensurepip) aren't used
# at runtime at all - the app runs entirely out of the uv-managed .venv
# copied in below - but they still sit in site-packages and get flagged by
# the image vulnerability scanner (pip vendors its own copy of msgpack,
# currently stuck on a version with a known advisory that even the latest
# pip release hasn't updated; setuptools has its own separate CVE). Since
# nothing here needs them, remove them outright rather than chase upstream
# patches for code the app never runs. Globbed (not hardcoded to 3.13) so
# this doesn't silently stop working on the next Python version bump.
RUN rm -rf /usr/local/lib/python3.*/site-packages/*

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live', timeout=2)" || exit 1

CMD ["uvicorn", "home_manager.app:app", "--host", "0.0.0.0", "--port", "8000"]
