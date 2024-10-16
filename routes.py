from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Team, Schedule, Note
from app import db
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from scheduling_algorithm import generate_advanced_schedule
import logging

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            return jsonify({"status": "success", "message": "Login successful", "redirect": url_for('main.dashboard')})
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            return jsonify({"status": "error", "message": "Invalid username or password"}), 401
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
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('User created successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                flash('An error occurred while creating the user. Please try again.', 'error')

    users = User.query.all()
    teams = Team.query.all()
    return render_template('user_management.html', users=users, teams=teams)

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    teams = Team.query.all()

    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        user.team_id = request.form.get('team_id') or None

        if request.form.get('password'):
            user.set_password(request.form.get('password'))

        try:
            db.session.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while updating the user. Please try again.', 'error')

    return render_template('edit_user.html', user=user, teams=teams)

@admin.route('/teams', methods=['GET', 'POST'])
@login_required
def manage_teams():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        manager_id = request.form.get('manager_id')

        if Team.query.filter_by(name=name).first():
            flash('Team name already exists.', 'error')
        else:
            try:
                manager_id = manager_id if manager_id else None
                new_team = Team(name=name, manager_id=manager_id)
                db.session.add(new_team)
                db.session.commit()
                flash('Team created successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                flash(f'An error occurred while creating the team: {str(e)}', 'error')

    teams = Team.query.all()
    managers = User.query.filter_by(role='manager').all()
    return render_template('team_management.html', teams=teams, managers=managers)

@admin.route('/teams/edit/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    team = Team.query.get_or_404(team_id)
    managers = User.query.filter_by(role='manager').all()

    if request.method == 'POST':
        team.name = request.form.get('name')
        team.manager_id = request.form.get('manager_id') or None

        try:
            db.session.commit()
            flash('Team updated successfully.', 'success')
            return redirect(url_for('admin.manage_teams'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while updating the team. Please try again.', 'error')

    return render_template('edit_team.html', team=team, managers=managers)

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

@manager.route('/advanced_schedule', methods=['GET', 'POST'])
@login_required
def advanced_schedule():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Admin or Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    teams = Team.query.all()

    if request.method == 'POST':
        team_id = request.form.get('team_id')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')

        try:
            new_schedules = generate_advanced_schedule(team_id, start_date, end_date)
            for schedule in new_schedules:
                db.session.add(schedule)
            db.session.commit()
            flash('Advanced schedule generated successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while generating the schedule. Please try again.', 'error')

    return render_template('advanced_schedule.html', teams=teams)