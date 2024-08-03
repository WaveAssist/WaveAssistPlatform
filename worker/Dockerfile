# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install required system packages and Chrome
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    libhdf5-cpp-103 \
    pkg-config \
    gnupg \
    wget \
    curl \
    unzip \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxrandr2 \
    libxdamage1 \
    libxkbcommon0 \
    libgbm-dev \
    xvfb \
    && wget -O /tmp/google-chrome-stable_current_amd64.deb https://waveassistapps.s3.amazonaws.com/public/ZerodhaAutoLogin/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/google-chrome-stable_current_amd64.deb \
    && apt-get install -f -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome-stable_current_amd64.deb


# Copy the requirements file into the container
COPY requirements.txt ./

# Install any necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project into the container
COPY . .

# Start the Worker
CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info", "-c", "2"]
