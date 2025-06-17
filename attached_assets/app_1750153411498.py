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

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///exam_system.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
    if not default_course:
        course = models.Course(
            name='General Knowledge',
            description='A general knowledge course for testing purposes',
            published=True,
            created_by=admin.id if admin else 1
        )
        db.session.add(course)
        db.session.commit()
        logging.info("Default course created: General Knowledge")

# Import routes after app initialization
import routes
