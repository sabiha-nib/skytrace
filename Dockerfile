# Skytrace container. NOTE: this Dockerfile has not been built yet (the build environment
# could not pull base images). It follows the documented install path in README.md.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SKYTRACE_HOST=0.0.0.0 SKYTRACE_PORT=8600
WORKDIR /app
COPY pyproject.toml README.md run.py ./
COPY src ./src
COPY web ./web
COPY config ./config
COPY scripts ./scripts
COPY fixtures ./fixtures
COPY data ./data
RUN pip install --no-cache-dir ".[astro]" \
    && useradd --create-home skytrace && chown -R skytrace /app
USER skytrace
EXPOSE 8600
# Real data: mount a bundle directory at /app/data/bundles, or run scripts/acquire_targets.py inside the container.
CMD ["python", "run.py"]
