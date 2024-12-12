# syntax=docker/dockerfile:experimental
FROM python:3.8-slim-buster
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install required system dependencies including build-essential for gcc
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ssh \
    wget \
    curl \
    unzip \
    vim \
    rsync \
    grsync \
    libunwind8 \
    && rm -rf /var/lib/apt/lists/*


# Copy the whole project directory into the container
COPY . /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["tail", "-f", "/dev/null"]
