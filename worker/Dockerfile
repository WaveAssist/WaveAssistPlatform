# Use the linux image as the base image.
# Arch-neutral: builds natively for the host (arm64 on Apple silicon / AWS Graviton,
# amd64 on x86 servers). Do not pin --platform here.
FROM python:3.10-slim

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
    # WeasyPrint runtime libraries (report/PDF generation used by reporting agents).
    # Without these `import weasyprint` succeeds but PDF rendering fails at runtime.
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Install the Claude Code CLI (used by the `claude_cli_token` LLM provider, which
# runs `claude -p` authenticated by an account's setup token). Native installer —
# no Node.js required; lands in /root/.local/bin.
ARG INSTALL_CLAUDE_CLI=0
# Optional: only used by the claude_cli LLM provider. Non-fatal — the box uses
# OpenRouter/Azure, and the installer segfaults under amd64 emulation.
RUN if [ "$INSTALL_CLAUDE_CLI" = "1" ]; then curl -fsSL https://claude.ai/install.sh | bash || echo "claude cli install skipped"; else echo "claude cli install disabled (INSTALL_CLAUDE_CLI=0)"; fi
ENV PATH="/root/.local/bin:${PATH}"

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any necessary dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Optional agent-runtime extras. The platform does not yet install a project's
# config.yaml `requirements:` (see worker/Utils/utils.py — disabled), so any node
# deps must be present in the image. This opt-in layer covers the common
# data-agent stack: MSSQL + MySQL drivers (FreeTDS for pymssql), HTTP, and a
# headless-Chromium PDF/screenshot renderer. Off by default to keep the base
# image lean; enable with `--build-arg INSTALL_AGENT_EXTRAS=1`.
ARG INSTALL_AGENT_EXTRAS=0
RUN if [ "$INSTALL_AGENT_EXTRAS" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends freetds-dev freetds-bin \
      && pip install --no-cache-dir pymssql PyMySQL requests playwright \
      && playwright install --with-deps chromium \
      && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* ; \
    else echo "agent extras disabled (INSTALL_AGENT_EXTRAS=0)"; fi

# Copy the entire Django project into the container
COPY . .

# Start the Worker
CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info", "--autoscale=8,1", "--prefetch-multiplier=1"]
