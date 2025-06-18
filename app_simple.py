from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
import os
from dotenv import load_dotenv

# Set environment variables for local development
os.environ['DATABASE_URL'] = 'sqlite:///lms.db'
os.environ['SECRET_KEY'] = 'dev-secret-key-for-local-development'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_PASSWORD'] = 'adminpassword'
os.environ['GOOGLE_API_KEY'] = 'AIzaSyA7zgkfPqewfQsGhQi7L8OYVxsiZuOguSU'

# Load environment variables (our explicit ones will override .env file)
load_dotenv()

# Create Flask app
app = Flask(
    __name__,
    template_folder='lms/templates',
    static_folder='lms/static'
)

# App configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///lms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"🔧 Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Set upload folder
upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms/static/uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = upload_folder
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.permanent_session_lifetime = timedelta(days=7)

# Initialize database
from lms.utils.db import db
db.init_app(app)

# Setup CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Import models
from lms.models.user import User
from lms.models.message import Message
from lms.models.ai_chat import AIChatMessage
from lms.models.certificate import Certificate
from lms.models.discussion import DiscussionGroup, DiscussionMessage, DiscussionMessageRead
from lms.utils.db import init_db

# Register blueprints
from lms.routes.auth import auth_bp
from lms.routes.admin import admin_bp
from lms.routes.teacher import teacher_bp
from lms.routes.student import student_bp
from lms.routes.course import course_bp
from lms.routes.messages import messages_bp
from lms.routes.discussions import discussions_bp

# Try to import AI chat blueprint with error handling
try:
    from lms.routes.ai_chat import ai_chat_bp
    AI_CHAT_AVAILABLE = True
    print("✅ AI Chat blueprint imported successfully")
except Exception as e:
    print(f"❌ Failed to import AI Chat blueprint: {e}")
    AI_CHAT_AVAILABLE = False

from swagger import swagger_bp

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints with error handling
try:
    app.register_blueprint(auth_bp)
    print("✅ Auth blueprint registered")
except Exception as e:
    print(f"❌ Failed to register auth blueprint: {e}")

try:
    app.register_blueprint(admin_bp, url_prefix='/admin')
    print("✅ Admin blueprint registered")
except Exception as e:
    print(f"❌ Failed to register admin blueprint: {e}")

try:
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    print("✅ Teacher blueprint registered")
except Exception as e:
    print(f"❌ Failed to register teacher blueprint: {e}")

try:
    app.register_blueprint(student_bp, url_prefix='/student')
    print("✅ Student blueprint registered")
except Exception as e:
    print(f"❌ Failed to register student blueprint: {e}")

try:
    app.register_blueprint(course_bp, url_prefix='/courses')
    print("✅ Course blueprint registered")
except Exception as e:
    print(f"❌ Failed to register course blueprint: {e}")

try:
    app.register_blueprint(messages_bp, url_prefix='/messages')
    print("✅ Messages blueprint registered")
except Exception as e:
    print(f"❌ Failed to register messages blueprint: {e}")

try:
    app.register_blueprint(discussions_bp, url_prefix='/discussions')
    print("✅ Discussions blueprint registered")
except Exception as e:
    print(f"❌ Failed to register discussions blueprint: {e}")

# Register AI chat blueprint if available
if AI_CHAT_AVAILABLE:
    try:
        app.register_blueprint(ai_chat_bp, url_prefix='/ai-chat')
        print("✅ AI Chat blueprint registered")
    except Exception as e:
        print(f"❌ Failed to register AI Chat blueprint: {e}")
        AI_CHAT_AVAILABLE = False

try:
    app.register_blueprint(swagger_bp)
    print("✅ Swagger blueprint registered")
except Exception as e:
    print(f"❌ Failed to register swagger blueprint: {e}")

# Make AI_CHAT_AVAILABLE available to templates
@app.context_processor
def inject_ai_chat_status():
    return dict(AI_CHAT_AVAILABLE=AI_CHAT_AVAILABLE)

@app.route('/')
def index():
    return render_template('landing.html')

if __name__ == '__main__':
    with app.app_context():
        init_db()
        print("Database initialized successfully.")
    
    print("Starting LMS on 127.0.0.1:5002 (production mode)")
    # Run without debug mode to avoid watchdog issues
    app.run(debug=False, host='127.0.0.1', port=5002) 