FROM python:3.12-slim

# The app works entirely in naive local datetimes (working hours,
# appointment times, "today"/"now" in the booking flow) and every shop is
# in this one timezone. Without tzdata + TZ the container runs in UTC, so
# datetime.now() lands 2-3h behind and already-passed slots for today
# still get offered. python:*-slim ships no tzdata, hence the apt install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Jerusalem

COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies first so this layer is cached unless pyproject.toml
# or uv.lock actually change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
