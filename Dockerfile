# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev gcc && \
    apt-get clean

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy project files
COPY . /app/

# Expose port
#EXPOSE 8000

# Start Gunicorn server
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "DocumentationBot.wsgi:application"]
