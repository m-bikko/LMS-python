#!/usr/bin/env python3
"""
Simple script to check the configuration before running the LMS
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_config():
    print("=== LMS Configuration Check ===")
    
    # Check DATABASE_URL
    database_url = os.getenv('DATABASE_URL', 'sqlite:///lms.db')
    print(f"Database URL: {database_url}")
    
    if 'postgresql' in database_url:
        print("✓ Using PostgreSQL database (Docker/Production)")
        if 'db:5432' in database_url:
            print("⚠️  Warning: This configuration is for Docker. For local development, use SQLite.")
    elif 'sqlite' in database_url:
        print("✓ Using SQLite database (Local development)")
    else:
        print("❌ Unknown database configuration")
    
    # Check other environment variables
    secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    
    print(f"Secret Key: {'***' if secret_key else 'Not set'}")
    print(f"Admin Email: {admin_email}")
    
    print("\n=== Recommendations ===")
    if 'postgresql' in database_url and 'db:5432' in database_url:
        print("For local development, run:")
        print("export DATABASE_URL='sqlite:///lms.db'")
        print("or use the updated run.sh script")
    
    return 'sqlite' in database_url

if __name__ == "__main__":
    is_local = check_config()
    if is_local:
        print("\n✓ Configuration looks good for local development!")
    else:
        print("\n⚠️ Configuration might be for Docker/Production") 