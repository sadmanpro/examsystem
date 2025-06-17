// Exam taking functionality

function goToQuestion(questionNumber) {
    // Hide all questions
    document.querySelectorAll('.question').forEach(q => q.style.display = 'none');
    
    // Show selected question
    document.getElementById('question-' + questionNumber).style.display = 'block';
    
    // Update current question
    currentQuestion = questionNumber;
    
    // Update navigation buttons
    updateNavigationButtons();
    updateQuestionNavigator();
}

function nextQuestion() {
    if (currentQuestion < totalQuestions) {
        goToQuestion(currentQuestion + 1);
    }
}

function previousQuestion() {
    if (currentQuestion > 1) {
        goToQuestion(currentQuestion - 1);
    }
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    prevBtn.disabled = currentQuestion === 1;
    
    if (currentQuestion === totalQuestions) {
        nextBtn.style.display = 'none';
    } else {
        nextBtn.style.display = 'inline-block';
    }
}

function updateQuestionNavigator() {
    // Update all navigation buttons
    for (let i = 1; i <= totalQuestions; i++) {
        const navBtn = document.getElementById('nav-btn-' + i);
        if (navBtn) {
            navBtn.classList.remove('answered', 'current');
            
            if (i === currentQuestion) {
                navBtn.classList.add('current');
            } else if (answeredQuestions.has(i)) {
                navBtn.classList.add('answered');
            }
        }
    }
}

function saveAnswer(attemptId, questionId, selectedAnswer) {
    const formData = new FormData();
    formData.append('attempt_id', attemptId);
    formData.append('question_id', questionId);
    formData.append('selected_answer', selectedAnswer);
    
    fetch('/save_answer', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mark question as answered
            answeredQuestions.add(currentQuestion);
            updateQuestionNavigator();
        } else {
            console.error('Error saving answer:', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function startTimer() {
    const timerInterval = setInterval(() => {
        timeRemaining--;
        
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        
        const timeDisplay = document.getElementById('time-remaining');
        timeDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        // Warning when 5 minutes left
        if (timeRemaining <= 300) {
            document.getElementById('timer').classList.add('warning');
        }
        
        // Auto-submit when time runs out
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            autoSubmit();
        }
    }, 1000);
}

// Prevent accidental page refresh during exam
window.addEventListener('beforeunload', function(e) {
    if (!examSubmitted) {
        e.preventDefault();
        e.returnValue = 'Are you sure you want to leave? Your progress will be lost.';
    }
});

// Handle page visibility change (detect if user switches tabs)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('User switched away from the exam tab');
        // You could implement additional security measures here
    }
});
