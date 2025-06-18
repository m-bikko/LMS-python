from datetime import datetime
from lms.utils.db import db
from flask import current_app
import logging

class DiscussionGroup(db.Model):
    """Discussion group for each course - includes all enrolled students + teacher"""
    __tablename__ = 'discussion_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    course = db.relationship('Course', backref='discussion_group')
    messages = db.relationship('DiscussionMessage', back_populates='group', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<DiscussionGroup {self.name}>'
    
    @property
    def participants(self):
        """Get all participants (enrolled students + teacher)"""
        from lms.models.user import User
        from lms.models.course import Enrollment
        
        # Get teacher
        teacher = User.query.get(self.course.teacher_id)
        participants = [teacher] if teacher else []
        
        # Get enrolled students with verified payments
        enrolled_students = db.session.query(User).join(
            Enrollment, User.id == Enrollment.student_id
        ).filter(
            Enrollment.course_id == self.course_id,
            Enrollment.payment_verified == True
        ).all()
        
        participants.extend(enrolled_students)
        return participants
    
    @property
    def participant_count(self):
        """Get total number of participants"""
        return len(self.participants)
    
    @property
    def latest_message(self):
        """Get the most recent message in this group"""
        return self.messages.order_by(DiscussionMessage.created_at.desc()).first()
    
    def can_user_participate(self, user_id):
        """Check if a user can participate in this discussion group"""
        from lms.models.course import Enrollment
        
        # Teacher can always participate
        if user_id == self.course.teacher_id:
            return True
        
        # Check if student is enrolled with verified payment
        enrollment = Enrollment.query.filter_by(
            student_id=user_id,
            course_id=self.course_id,
            payment_verified=True
        ).first()
        
        return enrollment is not None
    
    @staticmethod
    def create_for_course(course_id):
        """Create a discussion group for a course"""
        from lms.models.course import Course
        
        course = Course.query.get(course_id)
        if not course:
            return None
        
        # Check if group already exists
        existing_group = DiscussionGroup.query.filter_by(course_id=course_id).first()
        if existing_group:
            return existing_group
        
        # Create new discussion group
        group = DiscussionGroup(
            course_id=course_id,
            name=f"{course.title} - Discussion",
            description=f"Discussion group for {course.title}. Ask questions, share insights, and collaborate with your classmates and teacher."
        )
        
        db.session.add(group)
        db.session.commit()
        return group


class DiscussionMessage(db.Model):
    """Messages within discussion groups"""
    __tablename__ = 'discussion_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('discussion_groups.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, image, etc.
    file_path = db.Column(db.String(255))  # For file attachments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    group = db.relationship('DiscussionGroup', back_populates='messages')
    sender = db.relationship('User', backref='discussion_messages')
    read_receipts = db.relationship('DiscussionMessageRead', back_populates='message', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<DiscussionMessage {self.id} in group {self.group_id}>'
    
    @property
    def sender_name(self):
        """Get sender's full name"""
        return f"{self.sender.first_name} {self.sender.last_name}"
    
    @property
    def sender_role(self):
        """Get sender's role in the course (teacher/student)"""
        if self.sender_id == self.group.course.teacher_id:
            return 'teacher'
        return 'student'
    
    def mark_as_read_by(self, user_id):
        """Mark this message as read by a specific user"""
        existing_read = DiscussionMessageRead.query.filter_by(
            message_id=self.id,
            user_id=user_id
        ).first()
        
        if not existing_read:
            read_receipt = DiscussionMessageRead(
                message_id=self.id,
                user_id=user_id
            )
            db.session.add(read_receipt)
            db.session.commit()
    
    def is_read_by(self, user_id):
        """Check if this message has been read by a specific user"""
        return DiscussionMessageRead.query.filter_by(
            message_id=self.id,
            user_id=user_id
        ).first() is not None
    
    @property
    def read_count(self):
        """Get number of users who have read this message"""
        return len(self.read_receipts)


class DiscussionMessageRead(db.Model):
    """Track which users have read which messages"""
    __tablename__ = 'discussion_message_reads'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('discussion_messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    message = db.relationship('DiscussionMessage', back_populates='read_receipts')
    user = db.relationship('User', backref='message_reads')
    
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id'),)
    
    def __repr__(self):
        return f'<DiscussionMessageRead {self.id}>' 