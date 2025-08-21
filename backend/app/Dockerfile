# Use an official Python runtime as a parent image
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Copy requirements first for better caching
COPY app/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared mongo connection + cr api client + api source 
COPY mongo/ /app/mongo/
COPY clash_royale_api/ /app/clash_royale_api/
COPY app/src/ /app/src/

# Make the package importable
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Start the app with uvicorn
CMD ["uvicorn", "main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8000"]

