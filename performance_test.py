#!/usr/bin/env python3
import os
import time

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///lms.db'
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_PASSWORD'] = 'adminpassword'

from app_simple import app
from lms.models.user import User
from lms.models.course import Course, Enrollment, Module, Test, ModuleProgress, TestAttempt

def measure_query_time(query_name, query_func):
    """Measure the time it takes to execute a query"""
    start_time = time.time()
    result = query_func()
    end_time = time.time()
    duration = (end_time - start_time) * 1000  # Convert to milliseconds
    print(f"⏱️  {query_name}: {duration:.2f} ms")
    return result, duration

def performance_test():
    """Test the performance of common queries"""
    with app.app_context():
        print("🚀 Performance Test - Common LMS Queries")
        print("=" * 50)
        
        # Test 1: Get all courses
        measure_query_time(
            "All courses query",
            lambda: Course.query.all()
        )
        
        # Test 2: Get courses for teacher
        teacher = User.query.filter_by(email='teacher@gmail.com').first()
        if teacher:
            measure_query_time(
                "Teacher courses query",
                lambda: Course.query.filter_by(teacher_id=teacher.id).all()
            )
        
        # Test 3: Get enrollments for a course
        course = Course.query.first()
        if course:
            measure_query_time(
                "Course enrollments query",
                lambda: Enrollment.query.filter_by(course_id=course.id).all()
            )
            
            # Test 4: Get modules for a course
            measure_query_time(
                "Course modules query",
                lambda: Module.query.filter_by(course_id=course.id).all()
            )
        
        # Test 5: Get all users
        measure_query_time(
            "All users query",
            lambda: User.query.all()
        )
        
        # Test 6: Complex query - Student progress
        student = User.query.filter_by(email='student@example.com').first()
        if student and course:
            measure_query_time(
                "Student progress query",
                lambda: ModuleProgress.query.filter_by(student_id=student.id).all()
            )
        
        print("\n🎯 Performance Tips:")
        print("- Queries under 10ms: Excellent")
        print("- Queries 10-50ms: Good")
        print("- Queries 50-100ms: Acceptable")
        print("- Queries over 100ms: Needs optimization")

if __name__ == '__main__':
    performance_test() 