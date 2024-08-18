# Use the waveassistchrome image as the base image
FROM --platform=linux/amd64 public.ecr.aws/y1v1f4v7/waveassistchrome:latest

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project into the container
COPY . .

# Start the Worker
CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info", "-c", "2"]
