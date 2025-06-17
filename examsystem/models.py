from app import db
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(80), unique=True, nullable=False)
    password_hash = db.Column(String(256), nullable=False)
    user_type = db.Column(String(20), nullable=False)  # 'admin' or 'student'
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    created_courses = relationship('Course', backref='creator', lazy=True)
    created_exams = relationship('Exam', backref='creator', lazy=True)
    exam_attempts = relationship('ExamAttempt', backref='student', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(200), nullable=False)
    thumbnail = db.Column(String(255))  # filename or URL
    description = db.Column(Text)
    published = db.Column(Boolean, default=False)
    approval_required = db.Column(Boolean, default=False)  # New field for approval requirement
    created_at = db.Column(DateTime, default=datetime.utcnow)
    created_by = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationships
    exams = relationship('Exam', back_populates='course', lazy=True, cascade='all, delete-orphan')
    course_requests = relationship('CourseRequest', backref='course', lazy=True, cascade='all, delete-orphan')
    course_enrollments = relationship('CourseEnrollment', backref='course', lazy=True, cascade='all, delete-orphan')

class Exam(db.Model):
    __tablename__ = 'exams'
    
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(200), nullable=False)
    duration_minutes = db.Column(Integer, nullable=False)
    marks_per_question = db.Column(Float, nullable=False)
    negative_marks = db.Column(Float, default=0.0)
    is_published = db.Column(Boolean, default=False)
    end_time = db.Column(DateTime)  # When exam expires
    created_at = db.Column(DateTime, default=datetime.utcnow)
    created_by = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    course_id = db.Column(Integer, ForeignKey('courses.id'), nullable=False)
    
    # Relationships
    course = relationship('Course', back_populates='exams', lazy=True)
    questions = relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')
    attempts = relationship('ExamAttempt', backref='exam', lazy=True)

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(Integer, primary_key=True)
    exam_id = db.Column(Integer, ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(Text, nullable=False)
    option_a = db.Column(Text, nullable=False)
    option_b = db.Column(Text, nullable=False)
    option_c = db.Column(Text, nullable=False)
    option_d = db.Column(Text, nullable=False)
    correct_answer = db.Column(String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    explanation = db.Column(Text)
    question_order = db.Column(Integer, nullable=False)
    
    # Relationships
    student_answers = relationship('StudentAnswer', backref='question', lazy=True)

class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'
    
    id = db.Column(Integer, primary_key=True)
    student_id = db.Column(Integer, ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(Integer, ForeignKey('exams.id'), nullable=False)
    start_time = db.Column(DateTime, default=datetime.utcnow)
    end_time = db.Column(DateTime)
    is_completed = db.Column(Boolean, default=False)
    total_score = db.Column(Float, default=0.0)
    correct_answers = db.Column(Integer, default=0)
    wrong_answers = db.Column(Integer, default=0)
    skipped_answers = db.Column(Integer, default=0)
    negative_marks_deducted = db.Column(Float, default=0.0)
    
    # Relationships
    student_answers = relationship('StudentAnswer', backref='attempt', lazy=True)

class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'
    
    id = db.Column(Integer, primary_key=True)
    attempt_id = db.Column(Integer, ForeignKey('exam_attempts.id'), nullable=False)
    question_id = db.Column(Integer, ForeignKey('questions.id'), nullable=False)
    selected_answer = db.Column(String(1))  # 'A', 'B', 'C', 'D', or None for skipped
    is_correct = db.Column(Boolean)
    answered_at = db.Column(DateTime, default=datetime.utcnow)

class CourseRequest(db.Model):
    __tablename__ = 'course_requests'
    
    id = db.Column(Integer, primary_key=True)
    course_id = db.Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    student_username = db.Column(String(80), nullable=False)
    status = db.Column(String(20), default='pending', nullable=False)  # 'pending', 'approved', 'denied'
    requested_at = db.Column(DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(DateTime)
    reviewed_by = db.Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))

class CourseEnrollment(db.Model):
    __tablename__ = 'course_enrollments'
    
    id = db.Column(Integer, primary_key=True)
    course_id = db.Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    enrolled_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (db.UniqueConstraint('course_id', 'student_id', name='unique_enrollment'),)
