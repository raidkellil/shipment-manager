# Dockerfile for Shipment Management System
# This creates a container with everything needed to run the app
# Created by: Raid Kellil

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyQt6
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libdbus-1-3 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY database.py .
COPY ui_widgets_1.py .
COPY ui_widgets_2.py .
COPY main.py .

# Run the application
CMD ["python", "main.py"]
