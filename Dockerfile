# Build stage for PDM dependencies
FROM python:3.12-slim AS pdm

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PDM
RUN pip install -U pip setuptools wheel && \
    pip install pdm

# Copy project files for dependency installation
COPY pyproject.toml pdm.lock ./

# Install production dependencies
RUN --mount=type=cache,target=/root/.cache/pdm pdm install --prod --no-editable

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy dependencies from pdm stage
COPY --from=pdm /app/.venv /app/.venv
COPY main.py main.py
COPY app.py app.py

# Set environment variables
ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages" \
    VIRTUAL_ENV="/app/.venv" \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN adduser --disabled-password --gecos "" --no-create-home appuser && \
    chown -R appuser:appuser /app && \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright python -m playwright install chromium --with-deps

USER appuser

EXPOSE 8000

CMD ["python", "app.py"]
