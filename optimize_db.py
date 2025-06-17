#!/usr/bin/env python3
import os

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///lms.db'
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_PASSWORD'] = 'adminpassword'

from app_simple import app
from lms.utils.db import db
from sqlalchemy import text

def optimize_database():
    """Add indexes to improve database performance"""
    with app.app_context():
        try:
            # Create indexes for frequently queried columns
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_courses_teacher_id ON courses (teacher_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_enrollments_student_id ON enrollments (student_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON enrollments (course_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_modules_course_id ON modules (course_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_materials_course_id ON materials (course_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_materials_module_id ON materials (module_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_tests_module_id ON tests (module_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_test_attempts_student_id ON test_attempts (student_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_test_attempts_test_id ON test_attempts (test_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_module_progress_student_id ON module_progress (student_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_module_progress_module_id ON module_progress (module_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_assignments_course_id ON assignments (course_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_submissions_student_id ON submissions (student_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_submissions_assignment_id ON submissions (assignment_id)'))
            
            # Commit the changes
            db.session.commit()
            print("✅ Database indexes created successfully!")
            
            # Analyze database to update statistics
            db.session.execute(text('ANALYZE'))
            db.session.commit()
            print("✅ Database statistics updated!")
            
            # Show database size
            result = db.session.execute(text("SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'")).fetchone()
            print(f"📊 Database has {result[0]} tables")
            
            print("✅ Database optimization completed!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error optimizing database: {e}")

if __name__ == '__main__':
    optimize_database() 