from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Team, Schedule, Note, TimeOffRequest, UserActivity
from app import db
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from scheduling_algorithm import generate_advanced_schedule
import logging
from sqlalchemy import func
from utils import admin_required

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@main.route('/')
@login_required
def index():
    return render_template('dashboard.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            # Record the login activity
            new_activity = UserActivity(user_id=user.id, activity_type='login')
            db.session.add(new_activity)
            db.session.commit()
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@admin.route('/analytics')
@login_required
@admin_required
def analytics_dashboard():
    total_users = User.query.count()
    total_teams = Team.query.count()
    total_schedules = Schedule.query.count()

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # User on-call hours in the last 30 days
    user_hours = db.session.query(
        User.username,
        func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
    ).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(User.username).all()

    # Team on-call hours in the last 30 days
    team_hours = db.session.query(
        Team.name,
        func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
    ).join(User).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(Team.name).all()

    # Time off request status
    time_off_status = db.session.query(
        TimeOffRequest.status,
        func.count(TimeOffRequest.id)
    ).group_by(TimeOffRequest.status).all()

    # Time off request trends (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    time_off_trends = db.session.query(
        func.date_trunc('month', TimeOffRequest.start_date).label('month'),
        func.count(TimeOffRequest.id)
    ).filter(TimeOffRequest.start_date >= six_months_ago).group_by('month').order_by('month').all()

    # User activity (logins in the last 30 days)
    user_activity = db.session.query(
        User.username,
        func.count(UserActivity.id).label('login_count')
    ).join(UserActivity).filter(UserActivity.timestamp >= thirty_days_ago, UserActivity.activity_type == 'login').group_by(User.username).all()

    return render_template('analytics_dashboard.html',
                           total_users=total_users,
                           total_teams=total_teams,
                           total_schedules=total_schedules,
                           user_hours=user_hours,
                           team_hours=team_hours,
                           time_off_status=time_off_status,
                           time_off_trends=time_off_trends,
                           user_activity=user_activity)

@admin.route('/manage_users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    teams = Team.query.all()
    return render_template('user_management.html', users=users, teams=teams)

@admin.route('/manage_users', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    team_id = request.form.get('team_id')

    new_user = User(username=username, email=email, role=role)
    new_user.set_password(password)
    if team_id:
        new_user.team_id = int(team_id)

    try:
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('Error adding user: ' + str(e), 'error')

    return redirect(url_for('admin.manage_users'))

@admin.route('/custom_report', methods=['GET', 'POST'])
@login_required
@admin_required
def custom_report():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')

        if report_type == 'user_hours':
            report_data = db.session.query(
                User.username,
                func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
            ).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(User.username).all()
        elif report_type == 'team_hours':
            report_data = db.session.query(
                Team.name,
                func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
            ).join(User).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(Team.name).all()
        elif report_type == 'time_off_requests':
            report_data = db.session.query(
                User.username,
                TimeOffRequest.start_date,
                TimeOffRequest.end_date,
                TimeOffRequest.status
            ).join(TimeOffRequest).filter(TimeOffRequest.start_date >= start_date, TimeOffRequest.end_date <= end_date).all()
        else:
            report_data = []

        return render_template('custom_report.html', report_type=report_type, report_data=report_data, start_date=start_date, end_date=end_date)

    return render_template('custom_report.html')
