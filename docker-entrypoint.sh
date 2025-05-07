#!/bin/bash
set -e

# Wait for PostgreSQL to start up
if [ ! -z "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgresql"* ]]; then
  echo "Waiting for PostgreSQL to start..."
  
  # Extract host and port from DATABASE_URL
  if [[ "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/([^?]+) ]]; then
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    
    # Simple sleep-based wait
    for i in {1..30}; do
      if pg_isready -h $DB_HOST -p $DB_PORT 2>/dev/null; then
        echo "PostgreSQL is up - continuing"
        break
      fi
      echo "PostgreSQL is unavailable - sleeping"
      sleep 1
    done
  else
    echo "Could not parse DATABASE_URL, skipping PostgreSQL check"
  fi
fi

# Initialize the database
echo "Setting up database..."
python setup_db.py

# Execute the passed command
exec "$@"