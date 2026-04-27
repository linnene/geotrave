# Use multi-stage build to keep the final image slim
FROM python:3.12-slim AS builder

# Set env variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Clean up to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Use Playwright's native command to handle all system dependencies and browser installation.
# install-deps automatically finds and installs the correct underlying packages for the current Debian version.
RUN playwright install-deps chromium && \
    playwright install chromium && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/ms-playwright/firefox-* && \
    rm -rf /root/.cache/ms-playwright/webkit-*

# Copy project source
COPY . .

# Ensure data directories exist
RUN mkdir -p data/chroma data/checkpointer

# Expose FastAPI port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
