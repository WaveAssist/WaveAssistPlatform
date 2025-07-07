# Use a lighter Python runtime as a parent image
FROM --platform=linux/amd64 python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    build-essential \
    graphviz \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project into the container
COPY . .

# Expose port 8000 to the host
EXPOSE 8000

# Expose port 5555 for Celery Flower
EXPOSE 5555

# Ensure all scripts are executable
RUN chmod +x ./start.sh ./start_beat.sh ./start_flower.sh ./start_camera.sh

# Start the Gunicorn server to serve the Django application ##ToDo: Shift to supervisor if needed.
CMD ["./start.sh"]
