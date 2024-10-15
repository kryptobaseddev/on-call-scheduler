from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from models import User, Team, Schedule, Note
from app import db
from datetime import datetime, timedelta

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/dashboard')
@login_required
def dashboard():
    # Fetch user's schedules for the next 7 days
    end_date = datetime.utcnow() + timedelta(days=7)
    schedules = Schedule.query.filter_by(user_id=current_user.id).filter(Schedule.start_time <= end_date).order_by(Schedule.start_time).all()
    
    # Fetch team notes
    notes = Note.query.filter_by(team_id=current_user.team_id).order_by(Note.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', schedules=schedules, notes=notes)

# Placeholder routes for admin and manager functions
@admin.route('/users')
@login_required
def manage_users():
    # TODO: Implement user management
    return "Manage Users"

@admin.route('/teams')
@login_required
def manage_teams():
    # TODO: Implement team management
    return "Manage Teams"

@manager.route('/schedule')
@login_required
def manage_schedule():
    # TODO: Implement schedule management
    return "Manage Schedule"
