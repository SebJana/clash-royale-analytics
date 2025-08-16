# Use an official Python runtime as a parent image
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Copy requirements first for better caching
COPY data_scraper/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared mongo connection + data scraper source
COPY mongo/ /app/mongo/
COPY data_scraper/src/ /app/src/
COPY data_scraper/tracked_players.json /app/tracked_players.json

# Make the package importable
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "src/main.py"]
