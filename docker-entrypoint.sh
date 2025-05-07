#!/bin/bash
set -e

# Wait for PostgreSQL to start up
if [ ! -z "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgresql"* ]]; then
  echo "Waiting for PostgreSQL to start..."
  
  # Extract host and port from DATABASE_URL
  if [[ "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/([^?]+) ]]; then
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_NAME="${BASH_REMATCH[5]}"
    
    # Simple sleep-based wait
    max_attempts=60
    for i in $(seq 1 $max_attempts); do
      echo "Attempt $i of $max_attempts: checking PostgreSQL connection..."
      if PGPASSWORD=$DB_PASS pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER 2>/dev/null; then
        echo "PostgreSQL is up - continuing"
        break
      fi
      
      if [ $i -eq $max_attempts ]; then
        echo "PostgreSQL not available after $max_attempts attempts - giving up"
        exit 1
      fi
      
      echo "PostgreSQL is unavailable - sleeping 1 second"
      sleep 1
    done
    
    # Verify DB connection
    echo "Testing database connection to $DB_NAME..."
    if ! PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" >/dev/null 2>&1; then
      echo "Failed to connect to database. Please check credentials."
      PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -l
      exit 1
    fi
    echo "Database connection successful!"
  else
    echo "Could not parse DATABASE_URL, skipping PostgreSQL check: $DATABASE_URL"
  fi
fi

# Initialize the database
echo "Setting up database..."
python setup_db.py

# Execute the passed command
exec "$@"