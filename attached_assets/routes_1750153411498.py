from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app import app, db
from models import User, Course, Exam, Question, ExamAttempt, StudentAnswer
import logging
import os

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
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
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, user_type='student').first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_type'] = 'student'
            session['username'] = user.username
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('student_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    courses = Course.query.filter_by(created_by=session['user_id']).order_by(Course.created_at.desc()).all()
    exams = Exam.query.filter_by(created_by=session['user_id']).order_by(Exam.created_at.desc()).all()
    return render_template('admin_dashboard.html', courses=courses, exams=exams)

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    
    # Get published courses with their exams
    published_courses = Course.query.filter_by(published=True).all()
    
    # Get student's attempted exams
    attempted_exam_ids = [attempt.exam_id for attempt in 
                         ExamAttempt.query.filter_by(student_id=session['user_id'], is_completed=True).all()]
    
    # Organize courses with available and completed exams
    courses_data = []
    for course in published_courses:
        course_exams = [exam for exam in course.exams if exam.is_published]
        available_exams = [exam for exam in course_exams if exam.id not in attempted_exam_ids]
        completed_exams = [exam for exam in course_exams if exam.id in attempted_exam_ids]
        
        courses_data.append({
            'course': course,
            'available_exams': available_exams,
            'completed_exams': completed_exams,
            'total_exams': len(course_exams)
        })
    
    return render_template('student_dashboard.html', courses_data=courses_data)

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        thumbnail_filename = None
        
        # Handle file upload
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename and file.filename != '':
                original_filename = file.filename or 'upload'
                filename = secure_filename(original_filename)
                # Add timestamp to prevent conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                thumbnail_filename = timestamp + filename
                file.save(os.path.join('static/uploads', thumbnail_filename))
        
        course = Course(
            name=request.form['name'],
            description=request.form['description'],
            thumbnail=thumbnail_filename,
            created_by=session['user_id']
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash('Course created successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('create_course.html')

@app.route('/launch_course/<int:course_id>')
def launch_course(course_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    course = Course.query.get_or_404(course_id)
    if course.created_by != session['user_id']:
        return redirect(url_for('admin_dashboard'))
    
    course.published = True
    db.session.commit()
    flash('Course launched successfully', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    # Get user's courses for the dropdown
    courses = Course.query.filter_by(created_by=session['user_id']).all()
    
    if request.method == 'POST':
        exam = Exam(
            name=request.form['name'],
            duration_minutes=int(request.form['duration']),
            marks_per_question=float(request.form['marks_per_question']),
            negative_marks=float(request.form['negative_marks']),
            created_by=session['user_id'],
            course_id=int(request.form['course_id'])
        )
        
        db.session.add(exam)
        db.session.commit()
        
        return redirect(url_for('add_questions', exam_id=exam.id))
    
    return render_template('create_exam.html', courses=courses)

@app.route('/add_questions/<int:exam_id>', methods=['GET', 'POST'])
def add_questions(exam_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != session['user_id']:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        # Add new question
        question_count = Question.query.filter_by(exam_id=exam_id).count()
        
        if question_count >= 200:
            flash('Maximum 200 questions allowed per exam', 'error')
        else:
            question = Question(
                exam_id=exam_id,
                question_text=request.form['question_text'],
                option_a=request.form['option_a'],
                option_b=request.form['option_b'],
                option_c=request.form['option_c'],
                option_d=request.form['option_d'],
                correct_answer=request.form['correct_answer'],
                explanation=request.form.get('explanation', ''),
                question_order=question_count + 1
            )
            
            db.session.add(question)
            db.session.commit()
            flash('Question added successfully', 'success')
    
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.question_order).all()
    return render_template('add_questions.html', exam=exam, questions=questions)

@app.route('/publish_exam/<int:exam_id>')
def publish_exam(exam_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('index'))
    
    exam = Exam.query.get_or_404(exam_id)
    if exam.created_by != session['user_id']:
        return redirect(url_for('admin_dashboard'))
    
    if Question.query.filter_by(exam_id=exam_id).count() == 0:
        flash('Cannot publish exam without questions', 'error')
        return redirect(url_for('add_questions', exam_id=exam_id))
    
    exam.is_published = True
    db.session.commit()
    flash('Exam published successfully', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/take_exam/<int:exam_id>')
def take_exam(exam_id):
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    
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
        return jsonify({'success': False, 'error': 'Server error'})

@app.route('/submit_exam/<int:attempt_id>')
def submit_exam(attempt_id):
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != session['user_id'] or attempt.is_completed:
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
            # Skipped question
            skipped_count += 1
            if student_answer:
                student_answer.is_correct = False
        else:
            # Answered question
            if student_answer.selected_answer == question.correct_answer:
                correct_count += 1
                total_score += exam.marks_per_question
                student_answer.is_correct = True
            else:
                wrong_count += 1
                if exam.negative_marks > 0:
                    negative_marks_deducted += exam.negative_marks
                    total_score -= exam.negative_marks
                student_answer.is_correct = False
    
    # Update attempt
    attempt.end_time = datetime.utcnow()
    attempt.is_completed = True
    attempt.total_score = total_score
    attempt.correct_answers = correct_count
    attempt.wrong_answers = wrong_count
    attempt.skipped_answers = skipped_count
    attempt.negative_marks_deducted = negative_marks_deducted
    
    db.session.commit()
    
    return redirect(url_for('exam_result', attempt_id=attempt_id))

@app.route('/exam_result/<int:attempt_id>')
def exam_result(attempt_id):
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != session['user_id'] or not attempt.is_completed:
        return redirect(url_for('student_dashboard'))
    
    return render_template('exam_result.html', attempt=attempt)

@app.route('/view_answers/<int:attempt_id>/<answer_type>')
def view_answers(attempt_id, answer_type):
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != session['user_id'] or not attempt.is_completed:
        return redirect(url_for('student_dashboard'))
    
    questions_with_answers = []
    
    for question in attempt.exam.questions:
        student_answer = StudentAnswer.query.filter_by(
            attempt_id=attempt_id, 
            question_id=question.id
        ).first()
        
        include_question = False
        
        if answer_type == 'correct' and student_answer and student_answer.is_correct:
            include_question = True
        elif answer_type == 'wrong' and student_answer and student_answer.is_correct == False and student_answer.selected_answer:
            include_question = True
        elif answer_type == 'skipped' and (not student_answer or not student_answer.selected_answer):
            include_question = True
        
        if include_question:
            questions_with_answers.append({
                'question': question,
                'student_answer': student_answer
            })
    
    return render_template('view_answers.html', 
                         questions_with_answers=questions_with_answers,
                         answer_type=answer_type,
                         attempt=attempt)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
