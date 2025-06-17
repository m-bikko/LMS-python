# Quick Fix for Database Connection Error

## Problem
The application is trying to connect to PostgreSQL database with hostname "db" which is used in Docker, but you're running locally.

## Solution

### Option 1: Use the updated run script (Recommended)
```bash
chmod +x run.sh
./run.sh
```

The updated `run.sh` script now automatically sets the correct environment variables for local development.

### Option 2: Set environment variables manually
```bash
# For macOS/Linux
export DATABASE_URL="sqlite:///lms.db"
export SECRET_KEY="dev-secret-key"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="adminpassword"

# Then run
python setup_db.py
python app.py
```

```cmd
# For Windows
set DATABASE_URL=sqlite:///lms.db
set SECRET_KEY=dev-secret-key
set ADMIN_EMAIL=admin@example.com
set ADMIN_PASSWORD=adminpassword

# Then run
python setup_db.py
python app.py
```

### Option 3: Use Windows batch script
```cmd
run.bat
```

## Verification
Before running, you can check your configuration:
```bash
python check_config.py
```

## What was changed:
1. Updated `run.sh` to set SQLite for local development
2. Updated `run.bat` for Windows users
3. Created `check_config.py` to verify configuration
4. Added this quick fix guide

## For Docker deployment:
If you want to use Docker instead:
```bash
docker-compose up -d
```

This will use PostgreSQL as configured in `docker-compose.yml`. 