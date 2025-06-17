from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, make_response
from flask_login import login_required, current_user
from lms.utils.db import db
from lms.utils.forms import (CourseCreationForm, MaterialForm, AssignmentForm, GradingForm,
                            ModuleForm, TestForm, QuestionForm, OptionForm, CertificateForm)
from lms.models.user import User, Role
from lms.models.course import (Course, Category, Material, Assignment, Submission, Enrollment,
                              Module, Test, Question, QuestionOption, TestAttempt, TestAnswer, 
                              ModuleProgress, TeacherSubscriptionPlan)
from werkzeug.utils import secure_filename
import os
import csv
import io
from functools import wraps
from datetime import datetime

teacher_bp = Blueprint('teacher', __name__)

# Debug flag - can be removed in production
DEBUG_MODE = False

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    # Get courses created by this teacher
    all_courses = Course.query.filter_by(teacher_id=current_user.id).all()
    
    # Split into pending and approved courses
    pending_courses = [course for course in all_courses if not course.is_approved]
    approved_courses = [course for course in all_courses if course.is_approved]
    
    # Get statistics
    total_courses = len(all_courses)
    active_courses = sum(1 for course in all_courses if course.is_active and course.is_approved)
    
    # Process course stats for approved courses only
    course_stats = []
    for course in approved_courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).count()
        assignments = Assignment.query.filter_by(course_id=course.id).count()
        course_stats.append({
            'id': course.id,
            'title': course.title,
            'enrollments': enrollments,
            'assignments': assignments,
            'is_active': course.is_active
        })
    
    return render_template('teacher/dashboard.html', 
                           total_courses=total_courses,
                           active_courses=active_courses,
                           pending_courses=pending_courses,
                           approved_courses=course_stats)
                           
@teacher_bp.route('/courses/<int:course_id>/toggle-status', methods=['POST'])
@login_required
@teacher_required
def toggle_course_status(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to modify this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    try:
        # Toggle the active status
        course.is_active = not course.is_active
        db.session.commit()
        
        status = "activated" if course.is_active else "deactivated"
        flash(f'Course "{course.title}" has been {status} successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling course status: {str(e)}")
        flash(f'An error occurred while updating the course: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.dashboard'))
    
@teacher_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to delete this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    course_title = course.title
    
    try:
        # Delete all enrollments
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            db.session.delete(enrollment)
        
        # Delete all assignments and submissions
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        for assignment in assignments:
            # Delete submissions
            from lms.models.course import Submission
            submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
            for submission in submissions:
                db.session.delete(submission)
            db.session.delete(assignment)
        
        # Delete all modules and their content
        modules = Module.query.filter_by(course_id=course.id).all()
        for module in modules:
            # Delete materials
            Material.query.filter_by(module_id=module.id).delete()
            
            # Delete tests and their content
            tests = Test.query.filter_by(module_id=module.id).all()
            for test in tests:
                # Delete questions and options
                questions = Question.query.filter_by(test_id=test.id).all()
                for question in questions:
                    QuestionOption.query.filter_by(question_id=question.id).delete()
                    db.session.delete(question)
                
                # Delete test attempts and answers
                from lms.models.course import TestAttempt, TestAnswer
                attempts = TestAttempt.query.filter_by(test_id=test.id).all()
                for attempt in attempts:
                    TestAnswer.query.filter_by(attempt_id=attempt.id).delete()
                    db.session.delete(attempt)
                
                db.session.delete(test)
            
            # Delete module progress
            from lms.models.course import ModuleProgress
            ModuleProgress.query.filter_by(module_id=module.id).delete()
            
            # Delete the module
            db.session.delete(module)
        
        # Delete course materials not associated with a module
        Material.query.filter_by(course_id=course.id, module_id=None).delete()
        
        # Delete the course
        db.session.delete(course)
        db.session.commit()
        
        flash(f'Course "{course_title}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting course: {str(e)}")
        flash(f'An error occurred while deleting the course: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.dashboard'))

@teacher_bp.route('/certificate', methods=['GET', 'POST'])
@login_required
@teacher_required
def certificate():
    try:
        # Check if certificate functionality is available
        has_certificate_attr = hasattr(current_user, 'certificate_path')
        if not has_certificate_attr:
            flash('Certificate functionality is not available in this version.', 'warning')
            return redirect(url_for('teacher.dashboard'))
            
        form = CertificateForm()
        
        if form.validate_on_submit():
            # Handle certificate upload
            if form.certificate.data:
                try:
                    certificate_file = form.certificate.data
                    filename = secure_filename(certificate_file.filename)
                    # Create a unique filename
                    unique_filename = f"certificate_{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
                    certificate_path = os.path.join('uploads', 'certificates', unique_filename)
                    
                    # Make sure the directory exists
                    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save the file
                    certificate_file.save(os.path.join(upload_dir, unique_filename))
                    
                    # Update user record
                    current_user.certificate_path = certificate_path
                    current_user.certificate_submitted_at = datetime.utcnow()
                    current_user.certificate_verified = False
                    
                    db.session.commit()
                    flash('Your certificate has been submitted and is awaiting verification.', 'success')
                    return redirect(url_for('teacher.certificate'))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Certificate upload error: {str(e)}")
                    flash(f'Error uploading certificate: {str(e)}', 'danger')
        
        return render_template('teacher/certificate.html', form=form)
    except Exception as e:
        current_app.logger.error(f"Certificate route error: {str(e)}")
        flash('An error occurred accessing the certificate feature. Please contact support.', 'danger')
        return redirect(url_for('teacher.dashboard'))

@teacher_bp.route('/courses/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_course():
    # DEBUG INFORMATION
    if DEBUG_MODE:
        current_app.logger.debug(f"REQUEST METHOD: {request.method}")
        current_app.logger.debug(f"REQUEST FORM: {request.form}")
        current_app.logger.debug(f"REQUEST FILES: {request.files}")
        
        # Log subscription plans
        try:
            plans = TeacherSubscriptionPlan.query.all()
            current_app.logger.debug(f"Available plans: {[(p.id, p.name) for p in plans]}")
        except Exception as e:
            current_app.logger.error(f"Error getting subscription plans: {str(e)}")
    
    # Check if certificates are enabled and required
    try:
        # Use the has_verified_certificate method which has built-in error handling
        if not current_user.can_create_courses():
            flash('You need to submit your teaching certificate and have it verified before creating courses.', 'warning')
            return redirect(url_for('teacher.certificate'))
    except Exception as e:
        # If there's an error with the certificate check, log it but continue
        current_app.logger.error(f"Certificate check error: {str(e)}")
        # Certificate functionality may not be enabled, so continue
    
    form = CourseCreationForm()
    
    # Get available categories for the dropdown
    categories = Category.query.limit(100).all()  # Limit categories
    form.category.choices = [(c.id, c.name) for c in categories]
    
    # Get available subscription plans for the dropdown
    try:
        subscription_plans = TeacherSubscriptionPlan.query.limit(20).all()  # Limit plans
        if subscription_plans:
            form.subscription_plan.choices = [(p.id, f"{p.name} - {p.price_per_month} KZT/month") for p in subscription_plans]
        else:
            # If no plans exist, create a default one for development purposes
            if DEBUG_MODE:
                flash('No subscription plans found. Creating a default plan for debugging.', 'warning')
                default_plan = TeacherSubscriptionPlan(
                    name="Default Plan - Up to 10 students", 
                    max_students=10, 
                    price_per_month=20000, 
                    description="Default plan created for debugging"
                )
                db.session.add(default_plan)
                db.session.commit()
                form.subscription_plan.choices = [(default_plan.id, f"{default_plan.name} - {default_plan.price_per_month} KZT/month")]
            else:
                flash('No subscription plans are available. Please contact the administrator.', 'danger')
                return redirect(url_for('teacher.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error setting up subscription plans: {str(e)}")
        flash('An error occurred with subscription plans. Please try again later.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    if request.method == 'POST':
        current_app.logger.debug(f"Form submitted: {request.form}")
        current_app.logger.debug(f"Form files: {request.files}")
    
    if form.validate_on_submit():
        current_app.logger.debug("Form validation passed")
        image_path = None
        payment_receipt_path = None
        
        # Handle course image upload
        if form.course_image.data:
            image = form.course_image.data
            image_filename = secure_filename(image.filename)
            # Create a unique filename to avoid collisions
            unique_filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{image_filename}"
            image_path = os.path.join('uploads', 'course_images', unique_filename)
            
            # Make sure the directory exists
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'course_images')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            image.save(os.path.join(upload_dir, unique_filename))
        
        # Handle payment receipt upload
        if form.payment_receipt.data:
            receipt = form.payment_receipt.data
            receipt_filename = secure_filename(receipt.filename)
            # Create a unique filename
            unique_receipt_name = f"teacher_{current_user.id}_{int(datetime.utcnow().timestamp())}_{receipt_filename}"
            payment_receipt_path = os.path.join('uploads', 'payment_receipts', unique_receipt_name)
            
            # Make sure the directory exists
            receipt_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payment_receipts')
            os.makedirs(receipt_dir, exist_ok=True)
            
            # Save the file
            receipt.save(os.path.join(receipt_dir, unique_receipt_name))
        
        try:
            # Create the course with payment information
            try:
                enrollment_price = int(form.enrollment_price.data)
            except ValueError:
                # If price is not an integer, try to handle it
                try:
                    # Remove any commas or spaces and try again
                    clean_price = form.enrollment_price.data.replace(',', '').replace(' ', '')
                    enrollment_price = int(clean_price)
                except ValueError:
                    flash('Please enter a valid integer for the enrollment price.', 'danger')
                    return render_template('teacher/create_course.html', form=form)
                
            subscription_plan_id = form.subscription_plan.data
            
            # For development, if no payment receipt provided but DEBUG_MODE is on,
            # auto-approve the payment
            payment_verified = DEBUG_MODE and not payment_receipt_path
            
            course = Course(
                title=form.title.data,
                description=form.description.data,
                category_id=form.category.data,
                teacher_id=current_user.id,
                image_path=image_path,
                is_approved=False,  # Course is not approved by default
                
                # Payment-related fields
                enrollment_price=enrollment_price,
                subscription_plan_id=subscription_plan_id,
                payment_receipt_path=payment_receipt_path,
                payment_verified=payment_verified  # Auto-verified in debug mode if no receipt
            )
            
            db.session.add(course)
            db.session.commit()
            flash('Course created successfully! It will be available after admin approval and payment verification.', 'success')
            
            # Redirect to add modules instead of directly to course content
            return redirect(url_for('teacher.manage_modules', course_id=course.id))
        except ValueError as e:
            flash(f'Invalid price format: {str(e)}', 'danger')
            return render_template('teacher/create_course.html', form=form)
    else:
        current_app.logger.debug(f"Form validation failed. Errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return render_template('teacher/create_course.html', form=form)

@teacher_bp.route('/courses/<int:course_id>/content')
@login_required
@teacher_required
def add_course_content(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    material_form = MaterialForm()
    assignment_form = AssignmentForm()
    
    return render_template('teacher/course_content.html', 
                           course=course, 
                           material_form=material_form, 
                           assignment_form=assignment_form)

def save_file(file):
    try:
        # Create a meaningful filename with timestamp to avoid collisions
        original_filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        filename = f"{int(datetime.utcnow().timestamp())}_{original_filename}"
        
        # Create upload directory if it doesn't exist
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        
        # Full path for saving
        file_path = os.path.join(upload_dir, filename)
        
        # Save the file
        file.save(file_path)
        
        # Return the relative path for storing in database
        relative_path = os.path.join('uploads', filename)
        current_app.logger.debug(f"File saved at {file_path}, relative path: {relative_path}")
        return relative_path
    except Exception as e:
        current_app.logger.error(f"Error saving file: {str(e)}")
        raise Exception(f"Error saving file: {str(e)}")

@teacher_bp.route('/courses/<int:course_id>/materials/add', methods=['POST'])
@login_required
@teacher_required
def add_material(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = MaterialForm()
    if form.validate_on_submit():
        file_path = None
        content = form.content.data
        
        if form.content_type.data == 'file' and form.file.data:
            file_path = save_file(form.file.data)
        
        material = Material(
            title=form.title.data,
            content_type=form.content_type.data,
            content=content,
            file_path=file_path,
            course_id=course.id
        )
        db.session.add(material)
        db.session.commit()
        flash('Material added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.add_course_content', course_id=course.id))

@teacher_bp.route('/courses/<int:course_id>/assignments/add', methods=['POST'])
@login_required
@teacher_required
def add_assignment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = AssignmentForm()
    if form.validate_on_submit():
        assignment = Assignment(
            title=form.title.data,
            description=form.description.data,
            course_id=course.id
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.add_course_content', course_id=course.id))

@teacher_bp.route('/courses/<int:course_id>/students')
@login_required
@teacher_required
def course_students(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    enrolled_students = [enrollment.student for enrollment in enrollments]
    
    return render_template('teacher/course_students.html', 
                           course=course, 
                           students=enrolled_students)

@teacher_bp.route('/assignments/<int:assignment_id>/submissions')
@login_required
@teacher_required
def assignment_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view these submissions.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    
    return render_template('teacher/submissions.html', 
                           course=course, 
                           assignment=assignment, 
                           submissions=submissions)

@teacher_bp.route('/submissions/<int:submission_id>/grade', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    course = assignment.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to grade this submission.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = GradingForm()
    
    if form.validate_on_submit():
        submission.grade = form.grade.data
        submission.feedback = form.feedback.data
        submission.graded_at = datetime.utcnow()
        db.session.commit()
        
        # Update overall student grade for the course
        update_student_course_grade(submission.student_id, course.id)
        
        flash('Submission graded successfully!', 'success')
        return redirect(url_for('teacher.assignment_submissions', assignment_id=assignment.id))
    elif request.method == 'GET':
        if submission.grade is not None:
            form.grade.data = submission.grade
            form.feedback.data = submission.feedback
    
    return render_template('teacher/grade_submission.html', 
                           form=form, 
                           submission=submission, 
                           assignment=assignment, 
                           student=submission.student)

def update_student_course_grade(student_id, course_id):
    """Calculate and update the overall grade for a student in a course"""
    # Get all assignments for this course
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    if not assignments:
        return  # No assignments to grade
    
    total_points = 0
    earned_points = 0
    
    # Calculate points from assignments
    for assignment in assignments:
        submission = Submission.query.filter_by(
            assignment_id=assignment.id, 
            student_id=student_id
        ).first()
        
        # If the submission exists and has been graded
        if submission and submission.grade is not None:
            # Assume all assignments are worth 100 points
            total_points += 100
            earned_points += submission.grade
    
    # Get test attempts
    module_ids = [module.id for module in Module.query.filter_by(course_id=course_id).all()]
    
    if module_ids:
        tests = Test.query.filter(Test.module_id.in_(module_ids)).all()
        
        for test in tests:
            # Get the best attempt for this test
            best_attempt = TestAttempt.query.filter_by(
                test_id=test.id,
                student_id=student_id
            ).order_by(TestAttempt.score.desc()).first()
            
            if best_attempt and best_attempt.score is not None:
                total_points += 100
                earned_points += best_attempt.score
    
    # Calculate overall grade if there are points possible
    if total_points > 0:
        overall_grade = (earned_points / total_points) * 100
        
        # Update the enrollment record
        enrollment = Enrollment.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).first()
        
        if enrollment:
            enrollment.overall_grade = overall_grade
            db.session.commit()

# Module management routes
@teacher_bp.route('/courses/<int:course_id>/modules')
@login_required
@teacher_required
def manage_modules(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to manage this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
    form = ModuleForm()
    
    return render_template('teacher/manage_modules.html',
                          course=course,
                          modules=modules,
                          form=form)
                          
# Delete module route
@teacher_bp.route('/modules/<int:module_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to delete this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    course_id = course.id
    module_title = module.title
    
    try:
        # Delete all materials in the module
        Material.query.filter_by(module_id=module.id).delete()
        
        # Delete all tests in the module
        tests = Test.query.filter_by(module_id=module.id).all()
        for test in tests:
            # Delete all questions in the test
            questions = Question.query.filter_by(test_id=test.id).all()
            for question in questions:
                # Delete all options for the question
                QuestionOption.query.filter_by(question_id=question.id).delete()
                db.session.delete(question)
            
            # Delete all attempts
            from lms.models.course import TestAttempt, TestAnswer
            attempts = TestAttempt.query.filter_by(test_id=test.id).all()
            for attempt in attempts:
                TestAnswer.query.filter_by(attempt_id=attempt.id).delete()
                db.session.delete(attempt)
                
            db.session.delete(test)
        
        # Delete module progress
        from lms.models.course import ModuleProgress
        ModuleProgress.query.filter_by(module_id=module.id).delete()
        
        # Delete the module itself
        db.session.delete(module)
        db.session.commit()
        
        flash(f'Module "{module_title}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting module: {str(e)}")
        flash(f'An error occurred while deleting the module: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.manage_modules', course_id=course_id))

@teacher_bp.route('/courses/<int:course_id>/modules/add', methods=['POST'])
@login_required
@teacher_required
def add_module(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to manage this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = ModuleForm()
    if form.validate_on_submit():
        module = Module(
            title=form.title.data,
            description=form.description.data,
            order=form.order.data,
            course_id=course.id
        )
        db.session.add(module)
        db.session.commit()
        flash('Module added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.manage_modules', course_id=course.id))

@teacher_bp.route('/modules/<int:module_id>')
@login_required
@teacher_required
def view_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    materials = Material.query.filter_by(module_id=module.id).order_by(Material.order).all()
    tests = Test.query.filter_by(module_id=module.id).all()
    
    material_form = MaterialForm()
    test_form = TestForm()
    
    return render_template('teacher/view_module.html',
                          course=course,
                          module=module,
                          materials=materials,
                          tests=tests,
                          material_form=material_form,
                          test_form=test_form)

@teacher_bp.route('/modules/<int:module_id>/materials/add', methods=['POST'])
@login_required
@teacher_required
def add_module_material(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Before creating the form, check if we need to enforce file validation
    content_type = request.form.get('content_type')
    if content_type == 'file' and not request.files.get('file'):
        flash('Please select a file to upload.', 'danger')
        return redirect(url_for('teacher.view_module', module_id=module.id))
    
    form = MaterialForm()
    
    # Log form data for debugging
    current_app.logger.debug(f"Form data: {request.form}")
    current_app.logger.debug(f"Files: {request.files}")
    
    if form.validate_on_submit():
        file_path = None
        content = form.content.data or ''
        
        # Handle file upload
        if form.content_type.data == 'file' and form.file.data:
            try:
                file_path = save_file(form.file.data)
                current_app.logger.debug(f"File saved to {file_path}")
            except Exception as e:
                current_app.logger.error(f"Error saving file: {str(e)}")
                flash(f"Error saving file: {str(e)}", 'danger')
                return redirect(url_for('teacher.view_module', module_id=module.id))
        
        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(Material.order)).filter_by(module_id=module.id).scalar() or 0
        
        try:
            material = Material(
                title=form.title.data,
                content_type=form.content_type.data,
                content=content,
                file_path=file_path,
                course_id=course.id,
                module_id=module.id,
                order=highest_order + 1
            )
            db.session.add(material)
            db.session.commit()
            flash('Material added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding material: {str(e)}")
            flash(f"Error adding material: {str(e)}", 'danger')
    else:
        current_app.logger.error(f"Form validation failed: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                label = getattr(form, field).label.text if hasattr(getattr(form, field), 'label') else field
                flash(f"{label}: {error}", 'danger')
    
    return redirect(url_for('teacher.view_module', module_id=module.id))

# Test management routes
@teacher_bp.route('/modules/<int:module_id>/tests/add', methods=['POST'])
@login_required
@teacher_required
def add_test(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = TestForm()
    
    # Log form data for debugging
    current_app.logger.debug(f"Test form data: {request.form}")
    
    if form.validate_on_submit():
        try:
            # Sanitize the passing score (ensure it's between 0 and 100)
            passing_score = min(max(float(form.passing_score.data or 70.0), 0), 100)
            
            test = Test(
                title=form.title.data,
                description=form.description.data,
                passing_score=passing_score,
                module_id=module.id
            )
            db.session.add(test)
            db.session.commit()
            flash('Test added successfully!', 'success')
            return redirect(url_for('teacher.edit_test', test_id=test.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding test: {str(e)}")
            flash(f"Error adding test: {str(e)}", 'danger')
    else:
        current_app.logger.error(f"Test form validation failed: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                try:
                    label = getattr(form, field).label.text
                except AttributeError:
                    label = field
                flash(f"{label}: {error}", 'danger')
    
    return redirect(url_for('teacher.view_module', module_id=module.id))

@teacher_bp.route('/tests/<int:test_id>/edit')
@login_required
@teacher_required
def edit_test(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this test.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    questions = Question.query.filter_by(test_id=test.id).all()
    question_form = QuestionForm()
    
    return render_template('teacher/edit_test.html',
                          course=course,
                          module=module,
                          test=test,
                          questions=questions,
                          question_form=question_form)
                          
@teacher_bp.route('/tests/<int:test_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_test(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to delete this test.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    module_id = module.id
    test_title = test.title
    
    try:
        # Delete all questions and options
        questions = Question.query.filter_by(test_id=test.id).all()
        for question in questions:
            # Delete options
            QuestionOption.query.filter_by(question_id=question.id).delete()
            db.session.delete(question)
        
        # Delete all attempts and answers
        from lms.models.course import TestAttempt, TestAnswer
        attempts = TestAttempt.query.filter_by(test_id=test.id).all()
        for attempt in attempts:
            TestAnswer.query.filter_by(attempt_id=attempt.id).delete()
            db.session.delete(attempt)
        
        # Delete the test
        db.session.delete(test)
        db.session.commit()
        
        flash(f'Test "{test_title}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting test: {str(e)}")
        flash(f'An error occurred while deleting the test: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.view_module', module_id=module_id))

@teacher_bp.route('/tests/<int:test_id>/questions/add', methods=['POST'])
@login_required
@teacher_required
def add_question(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this test.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = QuestionForm()
    if form.validate_on_submit():
        question = Question(
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            points=form.points.data,
            test_id=test.id
        )
        db.session.add(question)
        db.session.commit()
        
        # If it's true/false, automatically add Yes/No options
        if form.question_type.data == 'true_false':
            true_option = QuestionOption(
                option_text='True',
                is_correct=True,
                question_id=question.id
            )
            false_option = QuestionOption(
                option_text='False',
                is_correct=False,
                question_id=question.id
            )
            db.session.add_all([true_option, false_option])
            db.session.commit()
            flash('True/False question added successfully!', 'success')
        else:
            flash('Question added successfully! Now add options for this question.', 'success')
            return redirect(url_for('teacher.edit_question', question_id=question.id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.edit_test', test_id=test.id))

@teacher_bp.route('/questions/<int:question_id>/edit')
@login_required
@teacher_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    test = question.test
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    options = QuestionOption.query.filter_by(question_id=question.id).all()
    option_form = OptionForm()
    
    return render_template('teacher/edit_question.html',
                          course=course,
                          module=module,
                          test=test,
                          question=question,
                          options=options,
                          option_form=option_form)
                          
@teacher_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    test = question.test
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to delete this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    test_id = test.id
    question_text = question.question_text[:30] + '...' if len(question.question_text) > 30 else question.question_text
    
    try:
        # Delete all options for this question
        QuestionOption.query.filter_by(question_id=question.id).delete()
        
        # Delete answers for this question
        from lms.models.course import TestAnswer
        TestAnswer.query.filter_by(question_id=question.id).delete()
        
        # Delete the question
        db.session.delete(question)
        db.session.commit()
        
        flash(f'Question "{question_text}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting question: {str(e)}")
        flash(f'An error occurred while deleting the question: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.edit_test', test_id=test_id))

@teacher_bp.route('/questions/<int:question_id>/options/add', methods=['POST'])
@login_required
@teacher_required
def add_option(question_id):
    question = Question.query.get_or_404(question_id)
    test = question.test
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = OptionForm()
    if form.validate_on_submit():
        option = QuestionOption(
            option_text=form.option_text.data,
            is_correct=form.is_correct.data,
            question_id=question.id
        )
        db.session.add(option)
        db.session.commit()
        flash('Option added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.edit_question', question_id=question.id))

@teacher_bp.route('/tests/<int:test_id>/results')
@login_required
@teacher_required
def test_results(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view these results.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get all attempts for this test grouped by student
    attempts = db.session.query(
        User, 
        db.func.count(TestAttempt.id).label('num_attempts'),
        db.func.max(TestAttempt.score).label('highest_score')
    ).join(
        TestAttempt, User.id == TestAttempt.student_id
    ).filter(
        TestAttempt.test_id == test.id
    ).group_by(
        User.id
    ).all()
    
    return render_template('teacher/test_results.html',
                          course=course,
                          module=module,
                          test=test,
                          attempts=attempts)

@teacher_bp.route('/courses/<int:course_id>/export-progress')
@login_required
@teacher_required
def export_course_progress(course_id):
    """Export student progress for a course as CSV file"""
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to export this course data.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get all enrolled students with eager loading
    enrollments = Enrollment.query.filter_by(course_id=course.id).options(
        db.joinedload(Enrollment.student)
    ).all()
    students = [enrollment.student for enrollment in enrollments]
    
    # Get all modules and tests for this course with eager loading
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
    
    # Pre-fetch all module progress and test attempts to reduce queries
    student_ids = [s.id for s in students]
    module_ids = [m.id for m in modules]
    
    # Get all module progress for these students
    module_progress_dict = {}
    if student_ids and module_ids:
        progresses = ModuleProgress.query.filter(
            ModuleProgress.student_id.in_(student_ids),
            ModuleProgress.module_id.in_(module_ids)
        ).all()
        for progress in progresses:
            module_progress_dict[(progress.student_id, progress.module_id)] = progress
    
    # Get all tests and test attempts
    tests_dict = {}
    test_attempts_dict = {}
    if module_ids:
        tests = Test.query.filter(Test.module_id.in_(module_ids)).all()
        test_ids = [t.id for t in tests]
        
        for test in tests:
            if test.module_id not in tests_dict:
                tests_dict[test.module_id] = []
            tests_dict[test.module_id].append(test)
        
        if student_ids and test_ids:
            attempts = TestAttempt.query.filter(
                TestAttempt.student_id.in_(student_ids),
                TestAttempt.test_id.in_(test_ids)
            ).order_by(TestAttempt.score.desc()).all()
            
            for attempt in attempts:
                key = (attempt.student_id, attempt.test_id)
                if key not in test_attempts_dict:
                    test_attempts_dict[key] = attempt
    
    # Create CSV data structure
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Create header row
    header = ['Student ID', 'Student Name', 'Student Email', 'Enrolled Date', 'Overall Grade']
    
    # Add module columns
    for module in modules:
        header.append(f'Module: {module.title}')
        # Add test columns for this module
        module_tests = tests_dict.get(module.id, [])
        for test in module_tests:
            header.append(f'Test: {test.title} (Module: {module.title})')
    
    writer.writerow(header)
    
    # Add student data rows
    for student in students:
        # Get enrollment info (already loaded via eager loading)
        enrollment = next((e for e in enrollments if e.student_id == student.id), None)
        
        row = [
            student.id,
            student.get_full_name(),
            student.email,
            enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M') if enrollment else 'N/A',
            f"{enrollment.overall_grade:.1f}%" if enrollment and enrollment.overall_grade else 'Not Graded'
        ]
        
        # Add module progress using pre-fetched data
        for module in modules:
            module_progress = module_progress_dict.get((student.id, module.id))
            
            if module_progress and module_progress.completed:
                status = f"Completed ({module_progress.completed_at.strftime('%Y-%m-%d')})" if module_progress.completed_at else "Completed"
            else:
                status = "In Progress"
            
            row.append(status)
            
            # Add test results for this module using pre-fetched data
            module_tests = tests_dict.get(module.id, [])
            for test in module_tests:
                best_attempt = test_attempts_dict.get((student.id, test.id))
                
                if best_attempt:
                    if best_attempt.completed_at:
                        test_status = f"{best_attempt.score:.1f}% ({'PASSED' if best_attempt.passed else 'FAILED'})"
                    else:
                        test_status = "Started"
                else:
                    test_status = "Not Attempted"
                
                row.append(test_status)
        
        writer.writerow(row)
    
    # Prepare response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{course.title}_student_progress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    return response