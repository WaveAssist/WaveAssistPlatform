# Use a base image with Python support
FROM python:3

# Set the working directory inside the container
WORKDIR /app

# Copy the project files to the container
COPY . /app

# Install project dependencies (if any)
RUN pip install -r requirements.txt

# Command to run your script
ENTRYPOINT ["python3", "run_project.py"]
