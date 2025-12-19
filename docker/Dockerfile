# Base image: glibc uyumlu ve Python 3.11
FROM python:3.11-slim-bullseye

# Gereken paketler
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-venv \
    zip \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /src

# Proje dosyalarını container’a kopyala
COPY . /src

# VENV dizini container içinde de ..venv olacak
ENV VENV_DIR=..venv

# Build script’i çalıştırabiliriz
CMD ["bash", "build_linux.sh"]
