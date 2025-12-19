# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        binutils \
        libjpeg-dev \
        zlib1g-dev \
        && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt pyinstaller

COPY src/ ./src

WORKDIR /app/src
RUN pyinstaller --onefile main.py --name plotune-arduino

# Stage 2: Host output
FROM alpine:latest AS output
WORKDIR /output

COPY --from=builder /app/src/dist/plotune-arduino ./
