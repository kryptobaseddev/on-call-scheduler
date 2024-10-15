from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Team, Schedule, Note
from app import db
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

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
    end_date = datetime.utcnow() + timedelta(days=7)
    schedules = Schedule.query.filter_by(user_id=current_user.id).filter(Schedule.start_time <= end_date).order_by(Schedule.start_time).all()
    notes = Note.query.filter_by(team_id=current_user.team_id).order_by(Note.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', schedules=schedules, notes=notes)

@admin.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        team_id = request.form.get('team_id') or None

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
        else:
            try:
                new_user = User(username=username, email=email, role=role, team_id=team_id)
                new_user.password_hash = generate_password_hash(password)
                db.session.add(new_user)
                db.session.commit()
                flash('User created successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                flash('An error occurred while creating the user. Please try again.', 'error')

    users = User.query.all()
    teams = Team.query.all()
    return render_template('user_management.html', users=users, teams=teams)

@admin.route('/teams', methods=['GET', 'POST'])
@login_required
def manage_teams():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        manager_id = request.form.get('manager_id') or None

        if Team.query.filter_by(name=name).first():
            flash('Team name already exists.', 'error')
        else:
            try:
                new_team = Team(name=name, manager_id=manager_id)
                db.session.add(new_team)
                db.session.commit()
                flash('Team created successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                flash('An error occurred while creating the team. Please try again.', 'error')

    teams = Team.query.all()
    managers = User.query.filter_by(role='manager').all()
    return render_template('team_management.html', teams=teams, managers=managers)

@manager.route('/schedule', methods=['GET', 'POST'])
@login_required
def manage_schedule():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')

        try:
            new_schedule = Schedule(user_id=user_id, start_time=start_time, end_time=end_time)
            db.session.add(new_schedule)
            db.session.commit()
            flash('Schedule created successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while creating the schedule. Please try again.', 'error')

    team_id = current_user.team_id if current_user.role == 'manager' else None
    users = User.query.filter_by(team_id=team_id).all() if team_id else User.query.all()
    schedules = Schedule.query.join(User).filter(User.team_id == team_id).all() if team_id else Schedule.query.all()
    return render_template('schedule.html', users=users, schedules=schedules)
