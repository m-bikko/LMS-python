from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from lms.models.discussion import DiscussionGroup, DiscussionMessage, DiscussionMessageRead
from lms.models.course import Course, Enrollment
from lms.models.user import User
from lms.utils.db import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

discussions_bp = Blueprint('discussions', __name__)

@discussions_bp.route('/')
@login_required
def list_discussions():
    """List all discussion groups the user can participate in"""
    if current_user.is_student():
        # Get discussion groups for enrolled courses
        enrolled_courses = db.session.query(Course).join(
            Enrollment, Course.id == Enrollment.course_id
        ).filter(
            Enrollment.student_id == current_user.id,
            Enrollment.payment_verified == True
        ).all()
        
        discussion_groups = []
        for course in enrolled_courses:
            group = DiscussionGroup.query.filter_by(course_id=course.id).first()
            if not group:
                # Create discussion group if it doesn't exist
                group = DiscussionGroup.create_for_course(course.id)
            if group:
                discussion_groups.append(group)
    
    elif current_user.is_teacher():
        # Get discussion groups for courses taught by this teacher
        taught_courses = Course.query.filter_by(teacher_id=current_user.id).all()
        discussion_groups = []
        for course in taught_courses:
            group = DiscussionGroup.query.filter_by(course_id=course.id).first()
            if not group:
                # Create discussion group if it doesn't exist
                group = DiscussionGroup.create_for_course(course.id)
            if group:
                discussion_groups.append(group)
    
    elif current_user.is_admin():
        # Admins can see all discussion groups
        discussion_groups = DiscussionGroup.query.filter_by(is_active=True).all()
    
    else:
        discussion_groups = []
    
    return render_template('discussions/list.html', discussion_groups=discussion_groups)

@discussions_bp.route('/<int:group_id>')
@login_required
def view_discussion(group_id):
    """View a specific discussion group"""
    group = DiscussionGroup.query.get_or_404(group_id)
    
    # Check if user can participate
    if not group.can_user_participate(current_user.id) and not current_user.is_admin():
        flash('You do not have access to this discussion group.', 'danger')
        return redirect(url_for('discussions.list_discussions'))
    
    # Get messages (latest 50)
    messages = group.messages.filter_by(is_deleted=False).order_by(
        DiscussionMessage.created_at.asc()
    ).limit(50).all()
    
    # Mark messages as read by current user
    for message in messages:
        if message.sender_id != current_user.id:
            message.mark_as_read_by(current_user.id)
    
    # Get participants
    participants = group.participants
    
    return render_template('discussions/chat.html', 
                         group=group, 
                         messages=messages, 
                         participants=participants)

@discussions_bp.route('/<int:group_id>/send', methods=['POST'])
@login_required
def send_message(group_id):
    """Send a message to a discussion group"""
    group = DiscussionGroup.query.get_or_404(group_id)
    
    # Check if user can participate
    if not group.can_user_participate(current_user.id) and not current_user.is_admin():
        return jsonify({'error': 'You do not have access to this discussion group.'}), 403
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Message content cannot be empty.'}), 400
    
    if len(content) > 2000:
        return jsonify({'error': 'Message is too long (max 2000 characters).'}), 400
    
    # Create message
    message = DiscussionMessage(
        group_id=group_id,
        sender_id=current_user.id,
        content=content,
        message_type='text'
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Mark as read by sender
    message.mark_as_read_by(current_user.id)
    
    return jsonify({
        'id': message.id,
        'content': message.content,
        'sender_name': message.sender_name,
        'sender_role': message.sender_role,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_own_message': True
    })

@discussions_bp.route('/<int:group_id>/messages')
@login_required
def get_messages(group_id):
    """Get messages for a discussion group (for AJAX updates)"""
    group = DiscussionGroup.query.get_or_404(group_id)
    
    # Check if user can participate
    if not group.can_user_participate(current_user.id) and not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get messages after a certain timestamp if provided
    after_timestamp = request.args.get('after')
    query = group.messages.filter_by(is_deleted=False)
    
    if after_timestamp:
        try:
            after_dt = datetime.fromisoformat(after_timestamp.replace('Z', '+00:00'))
            query = query.filter(DiscussionMessage.created_at > after_dt)
        except ValueError:
            pass
    
    messages = query.order_by(DiscussionMessage.created_at.asc()).limit(50).all()
    
    # Mark new messages as read
    for message in messages:
        if message.sender_id != current_user.id:
            message.mark_as_read_by(current_user.id)
    
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'sender_name': message.sender_name,
            'sender_role': message.sender_role,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_own_message': message.sender_id == current_user.id
        })
    
    return jsonify({'messages': messages_data})

@discussions_bp.route('/<int:group_id>/participants')
@login_required
def get_participants(group_id):
    """Get participants of a discussion group"""
    group = DiscussionGroup.query.get_or_404(group_id)
    
    # Check if user can participate
    if not group.can_user_participate(current_user.id) and not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    participants = group.participants
    participants_data = []
    
    for participant in participants:
        role = 'teacher' if participant.id == group.course.teacher_id else 'student'
        participants_data.append({
            'id': participant.id,
            'name': f"{participant.first_name} {participant.last_name}",
            'email': participant.email,
            'role': role,
            'is_current_user': participant.id == current_user.id
        })
    
    return jsonify({'participants': participants_data})

@discussions_bp.route('/<int:group_id>/info')
@login_required
def group_info(group_id):
    """Get information about a discussion group"""
    group = DiscussionGroup.query.get_or_404(group_id)
    
    # Check if user can participate
    if not group.can_user_participate(current_user.id) and not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'course_title': group.course.title,
        'teacher_name': f"{group.course.teacher.first_name} {group.course.teacher.last_name}",
        'participant_count': group.participant_count,
        'created_at': group.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@discussions_bp.route('/unread-count')
@login_required
def unread_count():
    """Get count of unread discussion messages for current user"""
    try:
        # Get all discussion groups user can participate in
        if current_user.is_student():
            enrolled_courses = db.session.query(Course).join(
                Enrollment, Course.id == Enrollment.course_id
            ).filter(
                Enrollment.student_id == current_user.id,
                Enrollment.payment_verified == True
            ).all()
            course_ids = [course.id for course in enrolled_courses]
        elif current_user.is_teacher():
            taught_courses = Course.query.filter_by(teacher_id=current_user.id).all()
            course_ids = [course.id for course in taught_courses]
        else:
            course_ids = []
        
        if not course_ids:
            return jsonify({'count': 0})
        
        # Count unread messages in these groups
        unread_count = db.session.query(DiscussionMessage).join(
            DiscussionGroup, DiscussionMessage.group_id == DiscussionGroup.id
        ).outerjoin(
            DiscussionMessageRead, 
            (DiscussionMessage.id == DiscussionMessageRead.message_id) & 
            (DiscussionMessageRead.user_id == current_user.id)
        ).filter(
            DiscussionGroup.course_id.in_(course_ids),
            DiscussionMessage.sender_id != current_user.id,
            DiscussionMessage.is_deleted == False,
            DiscussionMessageRead.id.is_(None)  # Not read
        ).count()
        
        return jsonify({'count': unread_count})
    
    except Exception as e:
        current_app.logger.error(f"Error getting unread discussion count: {str(e)}")
        return jsonify({'count': 0})

# Auto-create discussion groups when students enroll
@discussions_bp.route('/create-for-course/<int:course_id>', methods=['POST'])
@login_required
def create_for_course(course_id):
    """Create or get discussion group for a course (internal endpoint)"""
    if not current_user.is_teacher() and not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    course = Course.query.get_or_404(course_id)
    
    # Only course teacher or admin can create discussion group
    if current_user.id != course.teacher_id and not current_user.is_admin():
        return jsonify({'error': 'Only the course teacher can create discussion groups'}), 403
    
    group = DiscussionGroup.create_for_course(course_id)
    
    if group:
        return jsonify({
            'success': True,
            'group_id': group.id,
            'group_name': group.name
        })
    else:
        return jsonify({'error': 'Failed to create discussion group'}), 500 