#!/bin/bash
set -e

echo "🚀 Starting LMS Docker Container..."

# Create necessary directories
echo "📁 Creating upload directories..."
mkdir -p /app/lms/static/uploads/course_images
mkdir -p /app/lms/static/uploads/certificates
mkdir -p /app/lms/static/uploads/payment_receipts
mkdir -p /app/instance

# Set proper permissions
chmod -R 755 /app/lms/static/uploads
chmod -R 755 /app/instance

# Initialize the database if it doesn't exist
if [ ! -f "/app/lms.db" ]; then
    echo "📊 Initializing SQLite database..."
    python setup_db.py
else
    echo "📊 Database already exists, skipping initialization..."
fi

# Ensure database permissions
chmod 644 /app/lms.db 2>/dev/null || true

echo "✅ Container setup complete!"
echo "🌐 Starting application on port 5002..."

# Execute the passed command
exec "$@" 