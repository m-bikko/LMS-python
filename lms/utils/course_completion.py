from lms.models.course import Course, Module, ModuleProgress
from lms.models.certificate import Certificate
from lms.utils.db import db
from flask import current_app

def check_course_completion(student_id, course_id):
    """
    Check if a student has completed all modules in a course.
    Returns True if course is completed, False otherwise.
    """
    try:
        # Get all modules for the course
        modules = Module.query.filter_by(course_id=course_id).all()
        
        if not modules:
            # If course has no modules, consider it completed
            return True
        
        # Check if all modules are completed
        for module in modules:
            progress = ModuleProgress.query.filter_by(
                student_id=student_id,
                module_id=module.id,
                completed=True
            ).first()
            
            if not progress:
                return False
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error checking course completion: {str(e)}")
        return False

def generate_certificate_if_completed(student_id, course_id):
    """
    Check if course is completed and generate certificate if needed.
    Returns the certificate if generated/exists, None otherwise.
    """
    try:
        # Check if course is completed
        if not check_course_completion(student_id, course_id):
            return None
        
        # Check if certificate already exists
        existing_certificate = Certificate.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).first()
        
        if existing_certificate:
            return existing_certificate
        
        # Create new certificate
        certificate = Certificate.create_certificate(student_id, course_id)
        
        current_app.logger.info(f"Certificate generated for student {student_id} in course {course_id}: {certificate.certificate_number}")
        
        return certificate
    
    except Exception as e:
        current_app.logger.error(f"Error generating certificate: {str(e)}")
        return None

def get_student_certificates(student_id):
    """
    Get all certificates for a student.
    """
    try:
        return Certificate.query.filter_by(student_id=student_id).order_by(Certificate.issued_at.desc()).all()
    except Exception as e:
        current_app.logger.error(f"Error getting student certificates: {str(e)}")
        return []

def get_course_completion_status(student_id, course_id):
    """
    Get detailed completion status for a course.
    Returns a dictionary with completion information.
    """
    try:
        modules = Module.query.filter_by(course_id=course_id).all()
        total_modules = len(modules)
        completed_modules = 0
        
        for module in modules:
            progress = ModuleProgress.query.filter_by(
                student_id=student_id,
                module_id=module.id,
                completed=True
            ).first()
            
            if progress:
                completed_modules += 1
        
        completion_percentage = (completed_modules / total_modules * 100) if total_modules > 0 else 100
        is_completed = completion_percentage == 100
        
        # Check for certificate
        certificate = Certificate.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).first()
        
        return {
            'total_modules': total_modules,
            'completed_modules': completed_modules,
            'completion_percentage': completion_percentage,
            'is_completed': is_completed,
            'certificate': certificate
        }
    
    except Exception as e:
        current_app.logger.error(f"Error getting course completion status: {str(e)}")
        return {
            'total_modules': 0,
            'completed_modules': 0,
            'completion_percentage': 0,
            'is_completed': False,
            'certificate': None
        } 