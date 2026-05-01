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

# Install Google Chrome (managed browser) for better CDP stability &
# lower anti-bot detection than Playwright's bundled Chromium.
RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | \
        gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
        http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/google-chrome

# Playwright system deps (still needed by Crawl4AI for CDP communication)
RUN playwright install-deps chromium && \
    playwright install chromium && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/ms-playwright/firefox-* && \
    rm -rf /root/.cache/ms-playwright/webkit-*

# Copy project source
COPY . .

# Ensure data directories exist
RUN mkdir -p database/checkpointer data/chrome_profile

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port 8000 & streamlit run test/test_ui.py --server.port 8501 --server.address 0.0.0.0 & wait"]
