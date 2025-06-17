from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app as app
from flask_login import login_required, current_user
from lms.models.ai_chat import AIChatMessage
from lms.models.course import Course, Category
from lms.models.user import User
from lms.utils.db import db
from lms.services.gemini_service import GeminiService
import logging

ai_chat_bp = Blueprint('ai_chat', __name__)
logger = logging.getLogger(__name__)

@ai_chat_bp.route('/')
@login_required
def ai_chat():
    """Show the AI chat interface for course guidance"""
    try:
        # Only allow students to access AI chat for now
        if not current_user.is_student():
            flash('AI Course Advisor is currently only available for students.', 'info')
            return redirect(url_for('messages.inbox'))
        
        # Get conversation history
        history = AIChatMessage.get_conversation_history(current_user.id)
        
        return render_template('ai_chat/chat.html', history=history)
    except Exception as e:
        app.logger.error(f"Error in AI chat view: {str(e)}")
        flash("An error occurred loading the AI chat. Please try again later.", "danger")
        return redirect(url_for('messages.inbox'))

@ai_chat_bp.route('/send', methods=['POST'])
@login_required
def send_message():
    """Handle sending a message to the AI"""
    try:
        # Only allow students
        if not current_user.is_student():
            return jsonify({'error': 'AI Course Advisor is only available for students.'}), 403
        
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty.'}), 400
        
        # Get available courses for AI context
        available_courses = get_available_courses()
        
        # Get conversation history for context
        history = AIChatMessage.get_conversation_history(current_user.id, limit=5)
        
        # Initialize Gemini service
        try:
            gemini_service = GeminiService()
            
            # Get AI response
            ai_response = gemini_service.get_course_guidance(
                user_message=user_message,
                available_courses=available_courses,
                user_history=history
            )
            
            if not ai_response:
                ai_response = "I'm sorry, I'm having trouble processing your request right now. Please try again."
            
        except Exception as e:
            app.logger.error(f"Error getting AI response: {str(e)}")
            ai_response = "I'm currently experiencing technical difficulties. Please try again in a moment, or contact support if the issue persists."
        
        # Save the conversation
        saved_message = AIChatMessage.save_conversation(current_user.id, user_message, ai_response)
        
        if saved_message:
            return jsonify({
                'user_message': user_message,
                'ai_response': ai_response,
                'timestamp': saved_message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            app.logger.error("Failed to save AI chat conversation")
            return jsonify({
                'user_message': user_message,
                'ai_response': ai_response,
                'timestamp': 'now'
            })
    
    except Exception as e:
        app.logger.error(f"Error in AI chat send_message: {str(e)}")
        return jsonify({'error': 'An error occurred processing your message.'}), 500

@ai_chat_bp.route('/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear the user's AI chat history"""
    try:
        if not current_user.is_student():
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete all AI chat messages for this user
        AIChatMessage.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({'message': 'Chat history cleared successfully.'})
    
    except Exception as e:
        app.logger.error(f"Error clearing AI chat history: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to clear chat history.'}), 500

def get_available_courses():
    """Get formatted course information for AI context"""
    try:
        # Get active and approved courses
        courses = Course.query.filter_by(is_active=True, is_approved=True).all()
        
        available_courses = []
        for course in courses:
            # Get teacher info
            teacher = User.query.get(course.teacher_id)
            teacher_name = teacher.get_full_name() if teacher else "Unknown"
            
            # Get category info
            category = Category.query.get(course.category_id) if course.category_id else None
            category_name = category.name if category else "Uncategorized"
            
            course_info = {
                'id': course.id,
                'title': course.title,
                'description': course.description or "No description available.",
                'category': category_name,
                'teacher': teacher_name,
                'price': course.enrollment_price or 0,
                'enrollment_count': course.enrollment_count
            }
            available_courses.append(course_info)
        
        return available_courses
    
    except Exception as e:
        app.logger.error(f"Error getting available courses: {str(e)}")
        return []

@ai_chat_bp.route('/test')
@login_required
def test_ai():
    """Test endpoint to verify AI service is working"""
    try:
        if not current_user.is_admin():
            flash('Access denied.', 'danger')
            return redirect(url_for('index'))
        
        gemini_service = GeminiService()
        
        # Simple test prompt
        test_response = gemini_service.generate_review(
            "Say 'Hello! The AI service is working correctly.' and nothing else."
        )
        
        return jsonify({
            'status': 'success',
            'response': test_response,
            'message': 'AI service is working correctly'
        })
    
    except Exception as e:
        app.logger.error(f"Error testing AI service: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'AI service test failed'
        }), 500 