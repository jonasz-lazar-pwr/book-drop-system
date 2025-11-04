# === Stage 1: Build dependencies ===
FROM python:3.11-alpine AS build-stage

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies (required for psycopg2 and others)
RUN apk add --no-cache gcc musl-dev libpq-dev

WORKDIR /app
COPY requirements.txt .

# Install Python packages (compiled here)
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# === Stage 2: Runtime image ===
FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime dependencies only (no compiler)
RUN apk add --no-cache libpq

WORKDIR /app

# Copy installed dependencies from build stage
COPY --from=build-stage /install /usr/local

# Copy application source
COPY . .

# Expose port
EXPOSE 8000

# Cleanup (optional)
RUN rm -rf /root/.cache

# Start the FastAPI app with Uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]