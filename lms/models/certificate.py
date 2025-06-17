from datetime import datetime
from lms.utils.db import db

class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_number = db.Column(db.String(50), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completion_date = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    student = db.relationship('User', backref='course_certificates', foreign_keys=[student_id])
    course = db.relationship('Course', backref='certificates')
    
    # Unique constraint: one certificate per student per course
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id'),)
    
    def __repr__(self):
        return f'<Certificate {self.certificate_number}>'
    
    @staticmethod
    def generate_certificate_number(student_id, course_id):
        """Generate a unique certificate number"""
        timestamp = int(datetime.utcnow().timestamp())
        return f"CERT-{student_id}-{course_id}-{timestamp}"
    
    @staticmethod
    def create_certificate(student_id, course_id):
        """Create a new certificate for course completion"""
        from lms.models.user import User
        from lms.models.course import Course
        
        # Check if certificate already exists
        existing = Certificate.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).first()
        
        if existing:
            return existing
        
        # Generate certificate number
        cert_number = Certificate.generate_certificate_number(student_id, course_id)
        
        # Create new certificate
        certificate = Certificate(
            student_id=student_id,
            course_id=course_id,
            certificate_number=cert_number,
            completion_date=datetime.utcnow()
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        return certificate
    
    def get_student_name(self):
        """Get the full name of the student"""
        return f"{self.student.first_name} {self.student.last_name}"
    
    def get_course_title(self):
        """Get the title of the course"""
        return self.course.title
    
    def get_teacher_name(self):
        """Get the name of the course teacher"""
        return f"{self.course.teacher.first_name} {self.course.teacher.last_name}" 