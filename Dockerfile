# Stage 1: Build Next.js frontend
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
# Copy package files first for layer caching
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# Output is in /frontend/out/

# Stage 2: Python backend
FROM python:3.12-slim AS backend
WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend project files
COPY backend/pyproject.toml backend/uv.lock* ./
# Install dependencies (production only, no dev extras)
RUN uv sync --no-dev

# Copy backend application code
COPY backend/app/ ./app/

# Copy frontend static export from Stage 1
COPY --from=frontend-builder /frontend/out/ ./static/

# Create db directory for volume mount
RUN mkdir -p /app/db

# Set environment variables
ENV STATIC_DIR=/app/static
ENV DB_PATH=/app/db/finally.db
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
