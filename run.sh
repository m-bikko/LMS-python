#!/bin/bash

# Set up Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
mkdir -p lms/static/uploads

# Set environment variables for local development
export SECRET_KEY="dev-secret-key-for-local-development"
export DATABASE_URL="sqlite:///lms.db"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="adminpassword"

echo "Using SQLite database for local development..."
echo "Database URL: $DATABASE_URL"

# Check configuration
echo "Checking configuration..."
python check_config.py

# Initialize database with demo data
echo "Setting up database..."
python setup_db.py

# Run the application
echo "Starting LMS application..."
python app.py