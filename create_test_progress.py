#!/usr/bin/env python3
import os
from datetime import datetime, timedelta

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///lms.db'
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_PASSWORD'] = 'adminpassword'

from app_simple import app
from lms.models.user import User
from lms.models.course import Course, Enrollment, Module, Test, ModuleProgress, TestAttempt
from lms.utils.db import db

def create_test_progress():
    with app.app_context():
        # Create module progress for student 3 (student@example.com) in course 1
        # Module 1 - completed
        progress1 = ModuleProgress.query.filter_by(student_id=3, module_id=1).first()
        if not progress1:
            progress1 = ModuleProgress(
                student_id=3,
                module_id=1,
                completed=True,
                completed_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(progress1)
        
        # Module 3 - in progress (not completed)
        progress2 = ModuleProgress.query.filter_by(student_id=3, module_id=3).first()
        if not progress2:
            progress2 = ModuleProgress(
                student_id=3,
                module_id=3,
                completed=False
            )
            db.session.add(progress2)
        
        # Create test attempts for student 3
        # Test 1 - passed
        attempt1 = TestAttempt.query.filter_by(student_id=3, test_id=1).first()
        if not attempt1:
            attempt1 = TestAttempt(
                student_id=3,
                test_id=1,
                score=85.0,
                passed=True,
                started_at=datetime.utcnow() - timedelta(days=2),
                completed_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(attempt1)
        
        # Create module progress for student 7 (student@gmail.com) in course 1
        # Module 1 - completed
        progress3 = ModuleProgress.query.filter_by(student_id=7, module_id=1).first()
        if not progress3:
            progress3 = ModuleProgress(
                student_id=7,
                module_id=1,
                completed=True,
                completed_at=datetime.utcnow() - timedelta(days=1)
            )
            db.session.add(progress3)
        
        # Module 3 - completed
        progress4 = ModuleProgress.query.filter_by(student_id=7, module_id=3).first()
        if not progress4:
            progress4 = ModuleProgress(
                student_id=7,
                module_id=3,
                completed=True,
                completed_at=datetime.utcnow() - timedelta(hours=5)
            )
            db.session.add(progress4)
        
        # Create test attempts for student 7
        # Test 1 - failed first attempt
        attempt2 = TestAttempt.query.filter_by(student_id=7, test_id=1).first()
        if not attempt2:
            attempt2 = TestAttempt(
                student_id=7,
                test_id=1,
                score=65.0,
                passed=False,
                started_at=datetime.utcnow() - timedelta(days=1),
                completed_at=datetime.utcnow() - timedelta(days=1)
            )
            db.session.add(attempt2)
        
        # Student 6 in course 2 progress
        progress5 = ModuleProgress.query.filter_by(student_id=6, module_id=2).first()
        if not progress5:
            progress5 = ModuleProgress(
                student_id=6,
                module_id=2,
                completed=True,
                completed_at=datetime.utcnow() - timedelta(days=3)
            )
            db.session.add(progress5)
        
        # Test attempt for student 6 in test 2
        attempt3 = TestAttempt.query.filter_by(student_id=6, test_id=2).first()
        if not attempt3:
            attempt3 = TestAttempt(
                student_id=6,
                test_id=2,
                score=92.0,
                passed=True,
                started_at=datetime.utcnow() - timedelta(days=3),
                completed_at=datetime.utcnow() - timedelta(days=3)
            )
            db.session.add(attempt3)
        
        # Student 7 in course 6 progress
        progress6 = ModuleProgress.query.filter_by(student_id=7, module_id=4).first()
        if not progress6:
            progress6 = ModuleProgress(
                student_id=7,
                module_id=4,
                completed=False  # In progress
            )
            db.session.add(progress6)
        
        # Test attempts for student 7 in course 6
        # Test 3 - passed
        attempt4 = TestAttempt.query.filter_by(student_id=7, test_id=3).first()
        if not attempt4:
            attempt4 = TestAttempt(
                student_id=7,
                test_id=3,
                score=78.0,
                passed=True,
                started_at=datetime.utcnow() - timedelta(hours=2),
                completed_at=datetime.utcnow() - timedelta(hours=2)
            )
            db.session.add(attempt4)
        
        # Test 4 - started but not completed
        attempt5 = TestAttempt.query.filter_by(student_id=7, test_id=4).first()
        if not attempt5:
            attempt5 = TestAttempt(
                student_id=7,
                test_id=4,
                score=None,
                passed=None,
                started_at=datetime.utcnow() - timedelta(minutes=30),
                completed_at=None
            )
            db.session.add(attempt5)
        
        db.session.commit()
        print("Test progress data created successfully!")
        
        # Display created data
        print("\n=== Module Progress ===")
        progresses = ModuleProgress.query.all()
        for progress in progresses:
            status = "Completed" if progress.completed else "In Progress"
            print(f"Student {progress.student_id}, Module {progress.module_id}: {status}")
        
        print("\n=== Test Attempts ===")
        attempts = TestAttempt.query.all()
        for attempt in attempts:
            status = "Completed" if attempt.completed_at else "Started"
            score = f"{attempt.score}%" if attempt.score else "N/A"
            print(f"Student {attempt.student_id}, Test {attempt.test_id}: {status}, Score: {score}")

if __name__ == '__main__':
    create_test_progress() 