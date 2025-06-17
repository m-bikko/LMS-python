#!/usr/bin/env python3
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///lms.db'
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_PASSWORD'] = 'adminpassword'

from app_simple import app
from lms.models.user import User
from lms.models.course import Course, Enrollment, Module, Test

def check_data():
    with app.app_context():
        print('=== Users ===')
        users = User.query.all()
        for user in users:
            print(f'{user.id}: {user.email} ({user.role.name})')
        
        print('\n=== Courses ===')
        courses = Course.query.all()
        for course in courses:
            print(f'{course.id}: {course.title} (Teacher: {course.teacher_id})')
        
        print('\n=== Enrollments ===')
        enrollments = Enrollment.query.all()
        for enrollment in enrollments:
            print(f'Student {enrollment.student_id} enrolled in Course {enrollment.course_id}')
        
        print('\n=== Modules ===')
        modules = Module.query.all()
        for module in modules:
            print(f'Module {module.id}: {module.title} (Course: {module.course_id})')
            
        print('\n=== Tests ===')
        tests = Test.query.all()
        for test in tests:
            print(f'Test {test.id}: {test.title} (Module: {test.module_id})')

if __name__ == '__main__':
    check_data() 