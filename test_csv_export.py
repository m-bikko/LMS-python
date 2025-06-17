#!/usr/bin/env python3
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///lms.db'
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_PASSWORD'] = 'adminpassword'

from app_simple import app
from lms.models.user import User, Role
from lms.models.course import (Course, Enrollment, Module, Test, ModuleProgress, 
                              TestAttempt)
import csv
import io
from datetime import datetime

def test_csv_export():
    with app.app_context():
        # Test for course 1 (Course #1) which has students and modules
        course_id = 1
        course = Course.query.get(course_id)
        
        if not course:
            print(f"Course with ID {course_id} not found!")
            return
        
        print(f"Testing CSV export for course: {course.title}")
        print(f"Course teacher ID: {course.teacher_id}")
        
        # Get all enrolled students
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        students = [enrollment.student for enrollment in enrollments]
        
        print(f"Found {len(students)} enrolled students:")
        for student in students:
            print(f"  - {student.get_full_name()} ({student.email})")
        
        # Get all modules and tests for this course
        modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
        
        print(f"Found {len(modules)} modules:")
        for module in modules:
            print(f"  - Module {module.id}: {module.title}")
            tests = Test.query.filter_by(module_id=module.id).all()
            for test in tests:
                print(f"    - Test {test.id}: {test.title}")
        
        # Create CSV data structure
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Create header row
        header = ['Student ID', 'Student Name', 'Student Email', 'Enrolled Date', 'Overall Grade']
        
        # Add module columns
        for module in modules:
            header.append(f'Module: {module.title}')
            # Add test columns for this module
            tests = Test.query.filter_by(module_id=module.id).all()
            for test in tests:
                header.append(f'Test: {test.title} (Module: {module.title})')
        
        writer.writerow(header)
        print(f"\nCSV Header: {header}")
        
        # Add student data rows
        for student in students:
            # Get enrollment info
            enrollment = Enrollment.query.filter_by(student_id=student.id, course_id=course.id).first()
            
            row = [
                student.id,
                student.get_full_name(),
                student.email,
                enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M') if enrollment else 'N/A',
                f"{enrollment.overall_grade:.1f}%" if enrollment and enrollment.overall_grade else 'Not Graded'
            ]
            
            # Add module progress
            for module in modules:
                module_progress = ModuleProgress.query.filter_by(
                    student_id=student.id, 
                    module_id=module.id
                ).first()
                
                if module_progress and module_progress.completed:
                    status = f"Completed ({module_progress.completed_at.strftime('%Y-%m-%d')})" if module_progress.completed_at else "Completed"
                else:
                    status = "In Progress"
                
                row.append(status)
                
                # Add test results for this module
                tests = Test.query.filter_by(module_id=module.id).all()
                for test in tests:
                    # Get the best attempt for this test
                    best_attempt = TestAttempt.query.filter_by(
                        test_id=test.id,
                        student_id=student.id
                    ).order_by(TestAttempt.score.desc()).first()
                    
                    if best_attempt:
                        if best_attempt.completed_at:
                            test_status = f"{best_attempt.score:.1f}% ({'PASSED' if best_attempt.passed else 'FAILED'})"
                        else:
                            test_status = "Started"
                    else:
                        test_status = "Not Attempted"
                    
                    row.append(test_status)
            
            writer.writerow(row)
            print(f"Student row: {row}")
        
        # Display CSV content
        output.seek(0)
        csv_content = output.getvalue()
        print(f"\n=== Generated CSV Content ===")
        print(csv_content)
        
        # Save to file for testing
        filename = f"test_export_{course.title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)
        
        print(f"\nCSV file saved as: {filename}")

if __name__ == '__main__':
    test_csv_export() 