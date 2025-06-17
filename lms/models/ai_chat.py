from datetime import datetime
from lms.utils.db import db
from flask import current_app
import logging

class AIChatMessage(db.Model):
    __tablename__ = 'ai_chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)  # User's message
    response = db.Column(db.Text, nullable=False)  # AI's response
    created_at = db.Column(db.DateTime, default=datetime.utcnow, server_default=db.func.current_timestamp())
    
    # Define relationship
    user = db.relationship('User', backref='ai_chat_messages')
    
    def __repr__(self):
        return f'<AIChatMessage {self.id} from user {self.user_id}>'
    
    @staticmethod
    def get_conversation_history(user_id, limit=10):
        """Get the conversation history for a user"""
        try:
            return AIChatMessage.query.filter_by(user_id=user_id).order_by(AIChatMessage.created_at.desc()).limit(limit).all()
        except Exception as e:
            logging.error(f"Error getting AI chat conversation: {str(e)}")
            return []
    
    @staticmethod
    def save_conversation(user_id, user_message, ai_response):
        """Save a conversation turn between user and AI"""
        try:
            chat_message = AIChatMessage(
                user_id=user_id,
                message=user_message,
                response=ai_response
            )
            db.session.add(chat_message)
            db.session.commit()
            return chat_message
        except Exception as e:
            logging.error(f"Error saving AI chat conversation: {str(e)}")
            db.session.rollback()
            return None 