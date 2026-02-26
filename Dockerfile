# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME="0.0.0.0"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency metadata
COPY pyproject.toml uv.lock* ./

# Create venv and install dependencies
RUN uv sync

# Copy the rest of the app
COPY . .

EXPOSE 7860

# Run using the uv-managed virtualenv
CMD ["uv", "run", "python", "src/app.py"]
