# Use the linux image as the base image
FROM --platform=linux/amd64 python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    libhdf5-cpp-103 \
    pkg-config \
    wget \
    curl \
    unzip \
    ffmpeg \
    imagemagick \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project into the container
COPY . .

# Start the Worker
CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info", "--autoscale=16,1"]
