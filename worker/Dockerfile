# Use the linux image as the base image
FROM --platform=linux/amd64 python:3.10-slim

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install dependencies in a single RUN command
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libhdf5-dev \
    pkg-config \
    wget \
    curl \
    unzip \
    ffmpeg \
    imagemagick \
    xvfb \
    ca-certificates \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Install the Claude Code CLI (used by the `claude_cli_token` LLM provider, which
# runs `claude -p` authenticated by an account's setup token). Native installer —
# no Node.js required; lands in /root/.local/bin.
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any necessary dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project into the container
COPY . .

# Start the Worker
CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info", "--autoscale=8,1", "--prefetch-multiplier=1"]
