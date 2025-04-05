# Use an official Python runtime as a parent image
FROM python:3.13.1-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy just requirements to build dependencies
COPY requirements.txt .

# Install the dependencies
RUN pip install -U pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .