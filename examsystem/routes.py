from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app import app, db
from models import User, Course, Exam, Question, ExamAttempt, StudentAnswer, CourseRequest, CourseEnrollment
import logging
import os

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('admin_login.html')
        
        user = User.query.filter_by(username=username, user_type='admin').first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_type'] = 'admin'
            session['username'] = user.username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin_login.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('student_login.html')
        
        user = User.query.filter_by(username=username, user_type='student').first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_type'] = 'student'
            session['username'] = user.username
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('student_login.html')

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('student_register.html')
        
        # Username validation
        if len(username) < 3 or len(username) > 20:
            flash('Username must be between 3 and 20 characters', 'error')
            return render_template('student_register.html')
        
        if not username.replace('_', '').isalnum():
            flash('Username can only contain letters, numbers, and underscores', 'error')
            return render_template('student_register.html')
        
        # Password validation
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('student_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('student_register.html')
        
        try:
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('student_register.html')
            
            # Create new student user
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                user_type='student'
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            logging.info(f"New student registered: {username}")
            flash('Registration successful! You can now login with your credentials.', 'success')
            return redirect(url_for('student_login'))
            
        except Exception as e:
            logging.error(f"Error during student registration: {str(e)}")
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template('student_register.html')
    
    return render_template('student_register.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        courses = Course.query.filter_by(created_by=session['user_id']).order_by(Course.created_at.desc()).all()
        exams = Exam.query.filter_by(created_by=session['user_id']).order_by(Exam.created_at.desc()).all()
        return render_template('admin_dashboard.html', courses=courses, exams=exams)
    except Exception as e:
        logging.error(f"Error in admin_dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('user_type') != 'student':
        flash('Access denied. Please login as student.', 'error')
        return redirect(url_for('index'))
    
    try:
        student_id = session['user_id']
        
        # Get student info
        student = User.query.get(student_id)
        
        # Get all exam attempts for profile
        all_attempts = ExamAttempt.query.filter_by(student_id=student_id, is_completed=True).all()
        
        # Calculate overall statistics
        total_correct = sum(attempt.correct_answers for attempt in all_attempts)
        total_wrong = sum(attempt.wrong_answers for attempt in all_attempts)
        total_skipped = sum(attempt.skipped_answers for attempt in all_attempts)
        
        # Get all published courses
        all_courses = Course.query.filter_by(published=True).all()
        
        # Get student's enrollments
        enrollments = CourseEnrollment.query.filter_by(student_id=student_id).all()
        enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]
        
        # Get student's pending/approved requests
        requests = CourseRequest.query.filter_by(student_id=student_id).all()
        request_data = {req.course_id: req.status for req in requests}
        
        # Get student's enrolled courses with fresh queries
        my_courses = Course.query.filter(Course.id.in_(enrolled_course_ids), Course.published == True).all()
        
        # Get live exams from enrolled courses
        live_exams = []
        attempted_exam_ids = [attempt.exam_id for attempt in all_attempts]
        
        current_time = datetime.utcnow()
        for course in my_courses:
            course_exams = Exam.query.filter_by(course_id=course.id, is_published=True).all()
            for exam in course_exams:
                if (exam.id not in attempted_exam_ids and
                    (not exam.end_time or exam.end_time > current_time)):
                    live_exams.append({
                        'exam': exam,
                        'course': course
                    })
        
        return render_template('student_dashboard.html', 
                             student=student,
                             all_attempts=all_attempts,
                             total_correct=total_correct,
                             total_wrong=total_wrong,
                             total_skipped=total_skipped,
                             all_courses=all_courses,
                             my_courses=my_courses,
                             live_exams=live_exams,
                             enrolled_course_ids=enrolled_course_ids,
                             request_data=request_data)
    except Exception as e:
        logging.error(f"Error in student_dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Course name is required', 'error')
                return render_template('create_course.html')
            
            thumbnail_filename = None
            
            # Handle file upload
            if 'thumbnail' in request.files:
                file = request.files['thumbnail']
                if file and file.filename and file.filename != '' and allowed_file(file.filename):
                    original_filename = file.filename
                    filename = secure_filename(original_filename)
                    # Add timestamp to prevent conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    thumbnail_filename = timestamp + filename
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))
            
            course = Course(
                name=name,
                description=description,
                thumbnail=thumbnail_filename,
                created_by=session['user_id']
            )
            
            db.session.add(course)
            db.session.commit()
            
            flash('Course created successfully', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            logging.error(f"Error creating course: {str(e)}")
            db.session.rollback()
            flash('Error creating course', 'error')
    
    return render_template('create_course.html')

@app.route('/launch_course/<int:course_id>')
def launch_course(course_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        course = Course.query.get_or_404(course_id)
        if course.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        course.published = True
        db.session.commit()
        flash('Course launched successfully', 'success')
    except Exception as e:
        logging.error(f"Error launching course: {str(e)}")
        db.session.rollback()
        flash('Error launching course', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        course = Course.query.get_or_404(course_id)
        if course.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Course name is required', 'error')
                return render_template('edit_course.html', course=course)
            
            # Handle thumbnail upload
            if 'thumbnail' in request.files:
                file = request.files['thumbnail']
                if file and file.filename and file.filename != '' and allowed_file(file.filename):
                    # Delete old thumbnail if exists
                    if course.thumbnail:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], course.thumbnail)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # Save new thumbnail
                    original_filename = file.filename
                    filename = secure_filename(original_filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    thumbnail_filename = timestamp + filename
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))
                    course.thumbnail = thumbnail_filename
            
            course.name = name
            course.description = description
            db.session.commit()
            
            flash('Course updated successfully', 'success')
            return redirect(url_for('admin_dashboard'))
        
        return render_template('edit_course.html', course=course)
    except Exception as e:
        logging.error(f"Error editing course: {str(e)}")
        flash('Error editing course', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/delete_course/<int:course_id>')
def delete_course(course_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        course = Course.query.get_or_404(course_id)
        if course.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Delete thumbnail file if exists
        if course.thumbnail:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], course.thumbnail)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete course (cascade will handle exams and questions)
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully', 'success')
    except Exception as e:
        logging.error(f"Error deleting course: {str(e)}")
        db.session.rollback()
        flash('Error deleting course', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get user's courses for the dropdown
        courses = Course.query.filter_by(created_by=session['user_id']).all()
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            duration = request.form.get('duration')
            marks_per_question = request.form.get('marks_per_question')
            negative_marks = request.form.get('negative_marks', '0')
            course_id = request.form.get('course_id')
            
            if not name or not duration or not marks_per_question or not course_id:
                flash('All fields are required', 'error')
                return render_template('create_exam.html', courses=courses)
            
            try:
                duration = int(duration)
                marks_per_question = float(marks_per_question)
                negative_marks = float(negative_marks)
                course_id = int(course_id)
            except ValueError:
                flash('Invalid numeric values', 'error')
                return render_template('create_exam.html', courses=courses)
            
            # Verify course belongs to user
            course = Course.query.filter_by(id=course_id, created_by=session['user_id']).first()
            if not course:
                flash('Invalid course selected', 'error')
                return render_template('create_exam.html', courses=courses)
            
            # Handle end time
            end_time = None
            end_time_str = request.form.get('end_time')
            if end_time_str and end_time_str.strip():
                try:
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid end time format', 'error')
                    return render_template('create_exam.html', courses=courses)
            
            exam = Exam(
                name=name,
                duration_minutes=duration,
                marks_per_question=marks_per_question,
                negative_marks=negative_marks,
                end_time=end_time,
                created_by=session['user_id'],
                course_id=course_id
            )
            
            db.session.add(exam)
            db.session.commit()
            
            return redirect(url_for('add_questions', exam_id=exam.id))
        
        return render_template('create_exam.html', courses=courses)
    except Exception as e:
        logging.error(f"Error in create_exam: {str(e)}")
        flash('Error creating exam', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/add_questions/<int:exam_id>', methods=['GET', 'POST'])
def add_questions(exam_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = Exam.query.get_or_404(exam_id)
        if exam.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if request.method == 'POST':
            # Add new question
            question_count = Question.query.filter_by(exam_id=exam_id).count()
            
            if question_count >= 200:
                flash('Maximum 200 questions allowed per exam', 'error')
            else:
                question_text = request.form.get('question_text', '').strip()
                option_a = request.form.get('option_a', '').strip()
                option_b = request.form.get('option_b', '').strip()
                option_c = request.form.get('option_c', '').strip()
                option_d = request.form.get('option_d', '').strip()
                correct_answer = request.form.get('correct_answer')
                explanation = request.form.get('explanation', '').strip()
                
                if not all([question_text, option_a, option_b, option_c, option_d, correct_answer]):
                    flash('All question fields are required', 'error')
                elif correct_answer not in ['A', 'B', 'C', 'D']:
                    flash('Please select a valid correct answer', 'error')
                else:
                    question = Question(
                        exam_id=exam_id,
                        question_text=question_text,
                        option_a=option_a,
                        option_b=option_b,
                        option_c=option_c,
                        option_d=option_d,
                        correct_answer=correct_answer,
                        explanation=explanation,
                        question_order=question_count + 1
                    )
                    
                    db.session.add(question)
                    db.session.commit()
                    flash('Question added successfully', 'success')
        
        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_order).all()
        return render_template('add_questions.html', exam=exam, questions=questions)
    except Exception as e:
        logging.error(f"Error in add_questions: {str(e)}")
        flash('Error managing questions', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        question = Question.query.get_or_404(question_id)
        exam = question.exam
        if exam.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if request.method == 'POST':
            question_text = request.form.get('question_text', '').strip()
            option_a = request.form.get('option_a', '').strip()
            option_b = request.form.get('option_b', '').strip()
            option_c = request.form.get('option_c', '').strip()
            option_d = request.form.get('option_d', '').strip()
            correct_answer = request.form.get('correct_answer')
            explanation = request.form.get('explanation', '').strip()
            
            if not all([question_text, option_a, option_b, option_c, option_d, correct_answer]):
                flash('All question fields are required', 'error')
            elif correct_answer not in ['A', 'B', 'C', 'D']:
                flash('Please select a valid correct answer', 'error')
            else:
                question.question_text = question_text
                question.option_a = option_a
                question.option_b = option_b
                question.option_c = option_c
                question.option_d = option_d
                question.correct_answer = correct_answer
                question.explanation = explanation
                
                db.session.commit()
                flash('Question updated successfully', 'success')
                return redirect(url_for('add_questions', exam_id=exam.id))
        
        return render_template('edit_question.html', question=question, exam=exam)
    except Exception as e:
        logging.error(f"Error editing question: {str(e)}")
        flash('Error editing question', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/delete_question/<int:question_id>')
def delete_question(question_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        question = Question.query.get_or_404(question_id)
        exam = question.exam
        if exam.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        exam_id = exam.id
        question_order = question.question_order
        
        # Delete the question
        db.session.delete(question)
        
        # Reorder remaining questions
        remaining_questions = Question.query.filter_by(exam_id=exam_id).filter(
            Question.question_order > question_order
        ).all()
        
        for q in remaining_questions:
            q.question_order -= 1
        
        db.session.commit()
        flash('Question deleted successfully', 'success')
        return redirect(url_for('add_questions', exam_id=exam_id))
    except Exception as e:
        logging.error(f"Error deleting question: {str(e)}")
        db.session.rollback()
        flash('Error deleting question', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/publish_exam/<int:exam_id>')
def publish_exam(exam_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = Exam.query.get_or_404(exam_id)
        if exam.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if Question.query.filter_by(exam_id=exam_id).count() == 0:
            flash('Cannot publish exam without questions', 'error')
            return redirect(url_for('add_questions', exam_id=exam_id))
        
        exam.is_published = True
        db.session.commit()
        flash('Exam published successfully', 'success')
    except Exception as e:
        logging.error(f"Error publishing exam: {str(e)}")
        db.session.rollback()
        flash('Error publishing exam', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = Exam.query.get_or_404(exam_id)
        if exam.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        courses = Course.query.filter_by(created_by=session['user_id']).all()
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            duration = request.form.get('duration')
            marks_per_question = request.form.get('marks_per_question')
            negative_marks = request.form.get('negative_marks', '0')
            course_id = request.form.get('course_id')
            
            if not name or not duration or not marks_per_question or not course_id:
                flash('All fields are required', 'error')
                return render_template('edit_exam.html', exam=exam, courses=courses)
            
            try:
                duration = int(duration)
                marks_per_question = float(marks_per_question)
                negative_marks = float(negative_marks)
                course_id = int(course_id)
            except ValueError:
                flash('Invalid numeric values', 'error')
                return render_template('edit_exam.html', exam=exam, courses=courses)
            
            # Verify course belongs to user
            course = Course.query.filter_by(id=course_id, created_by=session['user_id']).first()
            if not course:
                flash('Invalid course selected', 'error')
                return render_template('edit_exam.html', exam=exam, courses=courses)
            
            # Handle end time
            end_time = None
            end_time_str = request.form.get('end_time')
            if end_time_str and end_time_str.strip():
                try:
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid end time format', 'error')
                    return render_template('edit_exam.html', exam=exam, courses=courses)
            
            exam.name = name
            exam.duration_minutes = duration
            exam.marks_per_question = marks_per_question
            exam.negative_marks = negative_marks
            exam.end_time = end_time
            exam.course_id = course_id
            
            db.session.commit()
            flash('Exam updated successfully', 'success')
            return redirect(url_for('admin_dashboard'))
        
        return render_template('edit_exam.html', exam=exam, courses=courses)
    except Exception as e:
        logging.error(f"Error editing exam: {str(e)}")
        flash('Error editing exam', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/delete_exam/<int:exam_id>')
def delete_exam(exam_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = Exam.query.get_or_404(exam_id)
        if exam.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Delete exam (cascade will handle questions)
        db.session.delete(exam)
        db.session.commit()
        flash('Exam deleted successfully', 'success')
    except Exception as e:
        logging.error(f"Error deleting exam: {str(e)}")
        db.session.rollback()
        flash('Error deleting exam', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/take_exam/<int:exam_id>')
def take_exam(exam_id):
    if session.get('user_type') != 'student':
        flash('Access denied. Please login as student.', 'error')
        return redirect(url_for('index'))
    
    try:
        exam = Exam.query.get_or_404(exam_id)
        if not exam.is_published:
            flash('Exam is not available', 'error')
            return redirect(url_for('student_dashboard'))
        
        # Check if student has already attempted this exam
        existing_attempt = ExamAttempt.query.filter_by(
            student_id=session['user_id'], 
            exam_id=exam_id, 
            is_completed=True
        ).first()
        
        if existing_attempt:
            flash('You have already completed this exam', 'error')
            return redirect(url_for('student_dashboard'))
        
        # Check for ongoing attempt
        ongoing_attempt = ExamAttempt.query.filter_by(
            student_id=session['user_id'], 
            exam_id=exam_id, 
            is_completed=False
        ).first()
        
        if not ongoing_attempt:
            # Create new attempt
            ongoing_attempt = ExamAttempt(
                student_id=session['user_id'],
                exam_id=exam_id
            )
            db.session.add(ongoing_attempt)
            db.session.commit()
        
        questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_order).all()
        
        # Calculate remaining time
        elapsed_time = datetime.utcnow() - ongoing_attempt.start_time
        remaining_minutes = exam.duration_minutes - (elapsed_time.total_seconds() / 60)
        
        if remaining_minutes <= 0:
            # Time up, submit exam automatically
            return redirect(url_for('submit_exam', attempt_id=ongoing_attempt.id))
        
        # Get existing answers
        existing_answers = {}
        for answer in ongoing_attempt.student_answers:
            existing_answers[answer.question_id] = answer.selected_answer
        
        return render_template('take_exam.html', 
                             exam=exam, 
                             questions=questions, 
                             attempt=ongoing_attempt,
                             remaining_minutes=int(remaining_minutes),
                             existing_answers=existing_answers)
    except Exception as e:
        logging.error(f"Error in take_exam: {str(e)}")
        flash('Error loading exam', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/save_answer', methods=['POST'])
def save_answer():
    try:
        if session.get('user_type') != 'student':
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        attempt_id = request.form.get('attempt_id')
        question_id = request.form.get('question_id')
        selected_answer = request.form.get('selected_answer')
        
        if not attempt_id or not question_id:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        attempt = ExamAttempt.query.get(attempt_id)
        if not attempt:
            return jsonify({'success': False, 'error': 'Attempt not found'})
            
        if attempt.student_id != session['user_id'] or attempt.is_completed:
            return jsonify({'success': False, 'error': 'Invalid attempt'})
        
        # Update or create student answer
        student_answer = StudentAnswer.query.filter_by(
            attempt_id=attempt_id, 
            question_id=question_id
        ).first()
        
        if student_answer:
            student_answer.selected_answer = selected_answer if selected_answer else None
            student_answer.answered_at = datetime.utcnow()
        else:
            student_answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_answer=selected_answer if selected_answer else None
            )
            db.session.add(student_answer)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Error saving answer: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Server error'})

@app.route('/submit_exam/<int:attempt_id>')
def submit_exam(attempt_id):
    if session.get('user_type') != 'student':
        flash('Access denied. Please login as student.', 'error')
        return redirect(url_for('index'))
    
    try:
        attempt = ExamAttempt.query.get_or_404(attempt_id)
        if attempt.student_id != session['user_id'] or attempt.is_completed:
            flash('Invalid exam attempt', 'error')
            return redirect(url_for('student_dashboard'))
        
        # Calculate results
        exam = attempt.exam
        questions = Question.query.filter_by(exam_id=exam.id).all()
        
        correct_count = 0
        wrong_count = 0
        skipped_count = 0
        total_score = 0.0
        negative_marks_deducted = 0.0
        
        for question in questions:
            student_answer = StudentAnswer.query.filter_by(
                attempt_id=attempt_id, 
                question_id=question.id
            ).first()
            
            if not student_answer or not student_answer.selected_answer:
                skipped_count += 1
                if student_answer:
                    student_answer.is_correct = False
            else:
                if student_answer.selected_answer == question.correct_answer:
                    correct_count += 1
                    total_score += exam.marks_per_question
                    student_answer.is_correct = True
                else:
                    wrong_count += 1
                    negative_marks_deducted += exam.negative_marks
                    total_score -= exam.negative_marks
                    student_answer.is_correct = False
        
        # Update attempt record
        attempt.end_time = datetime.utcnow()
        attempt.is_completed = True
        attempt.total_score = max(0, total_score)  # Ensure score doesn't go negative
        attempt.correct_answers = correct_count
        attempt.wrong_answers = wrong_count
        attempt.skipped_answers = skipped_count
        attempt.negative_marks_deducted = negative_marks_deducted
        
        db.session.commit()
        
        return redirect(url_for('exam_results', attempt_id=attempt_id))
    except Exception as e:
        logging.error(f"Error submitting exam: {str(e)}")
        db.session.rollback()
        flash('Error submitting exam', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/exam_results/<int:attempt_id>')
def exam_results(attempt_id):
    if session.get('user_type') != 'student':
        flash('Access denied. Please login as student.', 'error')
        return redirect(url_for('index'))
    
    try:
        attempt = ExamAttempt.query.get_or_404(attempt_id)
        if attempt.student_id != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('student_dashboard'))
        
        exam = attempt.exam
        questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.question_order).all()
        
        # Get student answers with question details
        question_results = []
        for question in questions:
            student_answer = StudentAnswer.query.filter_by(
                attempt_id=attempt_id,
                question_id=question.id
            ).first()
            
            question_results.append({
                'question': question,
                'student_answer': student_answer,
                'selected_option': student_answer.selected_answer if student_answer else None,
                'is_correct': student_answer.is_correct if student_answer else False
            })
        
        return render_template('exam_results.html', 
                             attempt=attempt, 
                             exam=exam, 
                             question_results=question_results)
    except Exception as e:
        logging.error(f"Error showing exam results: {str(e)}")
        flash('Error loading results', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logging.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

# Course Approval and Enrollment Routes
@app.route('/join_course/<int:course_id>', methods=['POST'])
def join_course(course_id):
    if session.get('user_type') != 'student':
        flash('Access denied. Please login as student.', 'error')
        return redirect(url_for('index'))
    
    try:
        course = Course.query.get_or_404(course_id)
        student_id = session['user_id']
        
        # Check if student is already enrolled
        existing_enrollment = CourseEnrollment.query.filter_by(
            course_id=course_id, student_id=student_id).first()
        if existing_enrollment:
            flash('You are already enrolled in this course.', 'info')
            return redirect(url_for('student_dashboard'))
        
        # Check if student already has a pending request
        existing_request = CourseRequest.query.filter_by(
            course_id=course_id, student_id=student_id, status='pending').first()
        if existing_request:
            flash('You already have a pending request for this course.', 'info')
            return redirect(url_for('student_dashboard'))
        
        if course.approval_required:
            # Create a course request
            course_request = CourseRequest(
                course_id=course_id,
                student_id=student_id,
                student_username=session['username']
            )
            db.session.add(course_request)
            db.session.commit()
            flash('Your request to join the course has been submitted. Please wait for admin approval.', 'success')
        else:
            # Direct enrollment
            enrollment = CourseEnrollment(
                course_id=course_id,
                student_id=student_id
            )
            db.session.add(enrollment)
            db.session.commit()
            flash('You have successfully joined the course!', 'success')
        
        return redirect(url_for('student_dashboard'))
    except Exception as e:
        logging.error(f"Error joining course: {str(e)}")
        db.session.rollback()
        flash('Error joining course', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/toggle_course_approval/<int:course_id>')
def toggle_course_approval(course_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        course = Course.query.get_or_404(course_id)
        if course.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('admin_dashboard'))
        
        course.approval_required = not course.approval_required
        db.session.commit()
        
        status = "enabled" if course.approval_required else "disabled"
        flash(f'Student approval for "{course.name}" has been {status}.', 'success')
        
    except Exception as e:
        logging.error(f"Error toggling course approval: {str(e)}")
        db.session.rollback()
        flash('Error updating course approval settings', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/manage_course_requests')
def manage_course_requests():
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get all pending requests for admin's courses
        admin_courses = Course.query.filter_by(created_by=session['user_id']).all()
        admin_course_ids = [course.id for course in admin_courses]
        
        if admin_course_ids:
            pending_requests = CourseRequest.query.join(Course).filter(
                CourseRequest.course_id.in_(admin_course_ids),
                CourseRequest.status == 'pending'
            ).all()
        else:
            pending_requests = []
        
        return render_template('manage_course_requests.html', 
                             pending_requests=pending_requests)
    except Exception as e:
        logging.error(f"Error loading course requests: {str(e)}")
        flash('Error loading course requests', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/approve_course_request/<int:request_id>')
def approve_course_request(request_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        course_request = CourseRequest.query.get_or_404(request_id)
        
        # Verify admin owns the course
        course = Course.query.get(course_request.course_id)
        if course.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('manage_course_requests'))
        
        # Check if student is already enrolled
        existing_enrollment = CourseEnrollment.query.filter_by(
            course_id=course_request.course_id, 
            student_id=course_request.student_id).first()
        
        if not existing_enrollment:
            # Create enrollment
            enrollment = CourseEnrollment(
                course_id=course_request.course_id,
                student_id=course_request.student_id
            )
            db.session.add(enrollment)
        
        # Update request status
        course_request.status = 'approved'
        course_request.reviewed_at = datetime.utcnow()
        course_request.reviewed_by = session['user_id']
        
        db.session.commit()
        flash(f'Request from {course_request.student_username} has been approved.', 'success')
        
    except Exception as e:
        logging.error(f"Error approving course request: {str(e)}")
        db.session.rollback()
        flash('Error approving request', 'error')
    
    return redirect(url_for('manage_course_requests'))

@app.route('/deny_course_request/<int:request_id>')
def deny_course_request(request_id):
    if session.get('user_type') != 'admin':
        flash('Access denied. Please login as admin.', 'error')
        return redirect(url_for('index'))
    
    try:
        course_request = CourseRequest.query.get_or_404(request_id)
        
        # Verify admin owns the course
        course = Course.query.get(course_request.course_id)
        if course.created_by != session['user_id']:
            flash('Access denied', 'error')
            return redirect(url_for('manage_course_requests'))
        
        # Update request status
        course_request.status = 'denied'
        course_request.reviewed_at = datetime.utcnow()
        course_request.reviewed_by = session['user_id']
        
        db.session.commit()
        flash(f'Request from {course_request.student_username} has been denied.', 'success')
        
    except Exception as e:
        logging.error(f"Error denying course request: {str(e)}")
        db.session.rollback()
        flash('Error denying request', 'error')
    
    return redirect(url_for('manage_course_requests'))
