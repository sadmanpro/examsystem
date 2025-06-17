import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configure database with proper PostgreSQL settings
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgresql://"):
    # Configure PostgreSQL with proper pool settings
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "pool_size": 10,
        "max_overflow": 20
    }
else:
    # Fallback to SQLite for development
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///exam_system.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Set upload folder
upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = upload_folder
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(upload_folder, exist_ok=True)

# Initialize the database with the app
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create default admin if it doesn't exist
    from werkzeug.security import generate_password_hash
    admin = models.User.query.filter_by(username='admin', user_type='admin').first()
    if not admin:
        admin_user = models.User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            user_type='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Default admin user created (username: admin, password: admin123)")
    
    # Create default student for testing
    student = models.User.query.filter_by(username='student', user_type='student').first()
    if not student:
        student_user = models.User(
            username='student',
            password_hash=generate_password_hash('student123'),
            user_type='student'
        )
        db.session.add(student_user)
        db.session.commit()
        logging.info("Default student user created (username: student, password: student123)")
    
    # Create default course if it doesn't exist
    default_course = models.Course.query.filter_by(name='General Knowledge').first()
    if not default_course and admin:
        course = models.Course(
            name='General Knowledge',
            description='A general knowledge course for testing purposes',
            published=True,
            created_by=admin.id
        )
        db.session.add(course)
        db.session.commit()
        logging.info("Default course created: General Knowledge")

# Import routes after app initialization
import routes
