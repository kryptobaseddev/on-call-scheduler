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
from utils import admin_required, manager_required

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
    try:
        logger.info(f"User {current_user.username} accessing index page")
        user_schedules = Schedule.query.filter_by(user_id=current_user.id).all()
        all_schedules = Schedule.query.all()
        notes = Note.query.filter_by(team_id=current_user.team_id).all()
        return render_template('dashboard.html', user_schedules=user_schedules, all_schedules=all_schedules, notes=notes)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template('dashboard.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            new_activity = UserActivity(user_id=user.id, activity_type='login')
            try:
                db.session.add(new_activity)
                db.session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Error recording login activity: {str(e)}")
                db.session.rollback()
            return jsonify(status="success", redirect=url_for('main.index'))
        else:
            return jsonify(status="error", message="Invalid username or password"), 401
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
    try:
        logger.info(f"User {current_user.username} accessing analytics dashboard")
        
        total_users = User.query.count()
        total_teams = Team.query.count()
        total_schedules = Schedule.query.count()

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        user_hours = db.session.query(
            User.username,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(User.username).all()

        team_hours = db.session.query(
            Team.name,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(User).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(Team.name).all()

        time_off_status = db.session.query(
            TimeOffRequest.status,
            func.count(TimeOffRequest.id)
        ).group_by(TimeOffRequest.status).all()

        six_months_ago = datetime.utcnow() - timedelta(days=180)
        time_off_trends = db.session.query(
            func.date_trunc('month', TimeOffRequest.start_date).label('month'),
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= six_months_ago).group_by('month').order_by('month').all()

        user_activity = db.session.query(
            User.username,
            func.count(UserActivity.id).label('login_count')
        ).join(UserActivity).filter(UserActivity.timestamp >= thirty_days_ago, UserActivity.activity_type == 'login').group_by(User.username).all()

        logger.info(f"Analytics data retrieved successfully for user {current_user.username}")

        return render_template('analytics_dashboard.html',
                               total_users=total_users,
                               total_teams=total_teams,
                               total_schedules=total_schedules,
                               user_hours=user_hours,
                               team_hours=team_hours,
                               time_off_status=time_off_status,
                               time_off_trends=time_off_trends,
                               user_activity=user_activity)
    except Exception as e:
        logger.error(f"Error in analytics_dashboard route: {str(e)}")
        flash('An error occurred while loading the analytics dashboard.', 'error')
        return render_template('analytics_dashboard.html')

@admin.route('/manage_users')
@login_required
@admin_required
def manage_users():
    try:
        logger.info(f"User {current_user.username} accessing manage users page")
        users = User.query.all()
        teams = Team.query.all()
        return render_template('user_management.html', users=users, teams=teams)
    except Exception as e:
        logger.error(f"Error in manage_users route: {str(e)}")
        flash('An error occurred while loading user management.', 'error')
        return render_template('user_management.html')

@admin.route('/manage_users', methods=['POST'])
@login_required
@admin_required
def add_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        team_id = request.form.get('team_id')

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        if team_id:
            new_user.team_id = int(team_id)

        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error adding user: {str(e)}")
        flash('Error adding user: ' + str(e), 'error')

    return redirect(url_for('admin.manage_users'))

@admin.route('/manage_teams')
@login_required
@admin_required
def manage_teams():
    try:
        logger.info(f"User {current_user.username} accessing manage teams page")
        teams = Team.query.all()
        managers = User.query.filter_by(role='manager').all()
        return render_template('team_management.html', teams=teams, managers=managers)
    except Exception as e:
        logger.error(f"Error in manage_teams route: {str(e)}")
        flash('An error occurred while loading team management.', 'error')
        return render_template('team_management.html')

@admin.route('/manage_teams', methods=['POST'])
@login_required
@admin_required
def add_team():
    try:
        name = request.form.get('name')
        manager_id = request.form.get('manager_id')
        color = request.form.get('color')

        new_team = Team(name=name, color=color)
        if manager_id:
            new_team.manager_id = int(manager_id)

        db.session.add(new_team)
        db.session.commit()
        flash('Team added successfully', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error adding team: {str(e)}")
        flash('Error adding team: ' + str(e), 'error')

    return redirect(url_for('admin.manage_teams'))

@admin.route('/custom_report', methods=['GET', 'POST'])
@login_required
@admin_required
def custom_report():
    if request.method == 'POST':
        try:
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
        except Exception as e:
            logger.error(f"Error generating custom report: {str(e)}")
            flash('An error occurred while generating the custom report.', 'error')
            return render_template('custom_report.html')

    return render_template('custom_report.html')

@manager.route('/manage_schedule')
@login_required
@manager_required
def manage_schedule():
    try:
        logger.info(f"User {current_user.username} (role: {current_user.role}) accessing manage schedule page")
        users = User.query.filter_by(team_id=current_user.team_id).all()
        schedules = Schedule.query.join(User).filter(User.team_id == current_user.team_id).all()
        return render_template('schedule.html', users=users, schedules=schedules)
    except Exception as e:
        logger.error(f"Error in manage_schedule route: {str(e)}")
        flash('An error occurred while loading schedule management.', 'error')
        return render_template('schedule.html')

@manager.route('/advanced_schedule', methods=['GET', 'POST'])
@login_required
@manager_required
def advanced_schedule():
    teams = Team.query.all()
    if request.method == 'POST':
        try:
            team_id = request.form.get('team_id')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            
            schedules = generate_advanced_schedule(team_id, start_date, end_date)
            
            for schedule in schedules:
                db.session.add(schedule)
            
            db.session.commit()
            flash('Advanced schedule generated successfully', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error generating advanced schedule: {str(e)}")
            flash('Error generating schedule: ' + str(e), 'error')
        
        return redirect(url_for('manager.manage_schedule'))
    
    return render_template('advanced_schedule.html', teams=teams)

@user.route('/time_off', methods=['GET', 'POST'])
@login_required
def time_off_request():
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            
            new_request = TimeOffRequest(user_id=current_user.id, start_date=start_date, end_date=end_date)
            
            db.session.add(new_request)
            db.session.commit()
            flash('Time-off request submitted successfully', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error submitting time-off request: {str(e)}")
            flash('Error submitting time-off request: ' + str(e), 'error')
        
        return redirect(url_for('main.index'))
    
    return render_template('time_off_request.html')