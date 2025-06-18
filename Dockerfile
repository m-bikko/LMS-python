FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal for SQLite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for uploads and database
RUN mkdir -p lms/static/uploads/course_images && \
    mkdir -p lms/static/uploads/certificates && \
    mkdir -p lms/static/uploads/payment_receipts && \
    mkdir -p instance

# Set environment variables
ENV FLASK_APP=app_simple.py
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER_CONTAINER=true

# Expose port
EXPOSE 5002

# Use entrypoint script to handle initialization
COPY docker-entrypoint-simple.sh /usr/local/bin/docker-entrypoint-simple.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-simple.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-simple.sh"]

# Default command - runs app_simple.py
CMD ["python", "app_simple.py"]