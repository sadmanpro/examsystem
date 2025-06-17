# Online MCQ Exam System

## Overview
This is a Flask-based online multiple choice question (MCQ) exam system that allows administrators to create and manage courses and exams while students can take them and view results. The system provides role-based authentication and a comprehensive exam management platform.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework) with SQLAlchemy ORM
- **Database**: PostgreSQL (production) with SQLite fallback for development
- **Authentication**: Session-based authentication with password hashing using Werkzeug
- **Deployment**: Gunicorn WSGI server configured for autoscale deployment on Replit
- **File Handling**: Secure file upload system for course thumbnails with 16MB size limit

### Frontend Architecture
- **Template Engine**: Jinja2 for server-side rendering
- **CSS Framework**: Bootstrap 5 with dark theme for responsive UI
- **Icons**: Font Awesome 6 for consistent iconography
- **JavaScript**: Vanilla JavaScript for interactive features (exam timer, question navigation)
- **Styling**: Custom CSS with glassmorphism design and gradient backgrounds

## Key Components

### Database Models
- **User**: Handles both admin and student accounts with role-based permissions
- **Course**: Manages course creation with thumbnails, descriptions, and publishing states
- **Exam**: Associates with courses, includes duration, scoring, and negative marking
- **Question**: Multiple choice questions with four options (A, B, C, D)
- **ExamAttempt**: Tracks student exam sessions and scores
- **StudentAnswer**: Records individual question responses

### User Management
- **Admin Users**: Create, manage, and publish courses and exams
- **Student Users**: Browse courses, take published exams, and view results
- **Authentication**: Session-based with secure password hashing
- **Role-based Access**: Separate dashboards and permissions for admins and students

### Course Management
- **Course Creation**: Name, description, and thumbnail image support
- **File Uploads**: Secure image upload with allowed extensions validation
- **Publishing System**: Draft/published states for course visibility
- **Course Organization**: Hierarchical structure with exams nested under courses

### Exam System
- **Exam Configuration**: Customizable duration, marks per question, and negative marking
- **Question Management**: Full CRUD operations for multiple choice questions
- **Publishing Control**: Separate publishing system for exam availability
- **Course Association**: All exams must be linked to a specific course

### Exam Taking Interface
- **Timer System**: Real-time countdown with automatic submission
- **Question Navigation**: Visual grid navigation showing answered/unanswered states
- **Answer Persistence**: Real-time saving of student responses via AJAX
- **Progress Tracking**: Visual indicators for exam completion status

## Data Flow

### Admin Workflow
1. Admin logs in through dedicated login page
2. Creates courses with optional thumbnail images
3. Creates exams within courses with scoring configuration
4. Adds multiple choice questions to exams
5. Publishes courses and exams to make them available to students

### Student Workflow
1. Student logs in through student portal
2. Browses available published courses
3. Selects and starts available exams
4. Navigates through questions with timer running
5. Submits exam (automatically or manually)
6. Views detailed results with score breakdown

### Database Relationships
- Users → Courses (one-to-many, creator relationship)
- Users → Exams (one-to-many, creator relationship)
- Courses → Exams (one-to-many)
- Exams → Questions (one-to-many with cascade delete)
- Users → ExamAttempts (one-to-many, student relationship)
- ExamAttempts → StudentAnswers (one-to-many)

## External Dependencies

### Python Packages
- **Flask 3.1.1**: Web framework
- **Flask-SQLAlchemy 3.1.1**: Database ORM
- **SQLAlchemy 2.0.41**: Database toolkit
- **Gunicorn 23.0.0**: WSGI server for production
- **psycopg2-binary 2.9.10**: PostgreSQL adapter
- **Werkzeug 3.1.3**: WSGI utilities and security
- **email-validator 2.2.0**: Email validation support

### Frontend Libraries
- **Bootstrap 5**: CSS framework with dark theme
- **Font Awesome 6**: Icon library
- **Custom CSS**: Glassmorphism effects and gradients

### Infrastructure
- **Replit**: Hosting platform with Nix package management
- **PostgreSQL 16**: Primary database (production)
- **OpenSSL**: Cryptographic functionality

## Deployment Strategy

### Environment Configuration
- **Development**: SQLite database with debug mode enabled
- **Production**: PostgreSQL with connection pooling and optimized settings
- **Session Management**: Environment-based secret key configuration
- **File Storage**: Local filesystem with organized upload directory structure

### Replit Configuration
- **Modules**: Python 3.11 and PostgreSQL 16
- **Deployment Target**: Autoscale for automatic scaling
- **Port Configuration**: Internal port 5000 mapped to external port 80
- **Process Management**: Gunicorn with reload capability for development

### Database Configuration
- **Connection Pooling**: Configured for PostgreSQL with proper pool settings
- **Pool Recycle**: 300 seconds to handle connection timeouts
- **Pool Size**: 10 connections with 20 overflow capacity
- **Health Checks**: Pre-ping enabled for connection validation

## Changelog
- June 17, 2025. Initial setup

## User Preferences
Preferred communication style: Simple, everyday language.