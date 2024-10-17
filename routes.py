from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Team, Schedule, Note, TimeOffRequest, UserActivity
from sqlalchemy import func, text
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from scheduling_algorithm import generate_advanced_schedule
import logging
from utils import admin_required, manager_required
import traceback

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@main.route('/')
@login_required
def index():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.debug("Starting index route")
        logger.info(f"User {current_user.username} accessing index page")
        
        logger.debug("Fetching user schedules")
        user_schedules = db_session.query(Schedule).filter_by(user_id=current_user.id).all()
        if user_schedules is None:
            logger.warning("User schedules query returned None")
            user_schedules = []
        
        logger.debug("Fetching all schedules")
        all_schedules = db_session.query(Schedule).all()
        if all_schedules is None:
            logger.warning("All schedules query returned None")
            all_schedules = []
        
        logger.debug("Fetching team notes")
        notes = db_session.query(Note).filter_by(team_id=current_user.team_id).all()
        if notes is None:
            logger.warning("Team notes query returned None")
            notes = []
        
        logger.debug("Rendering dashboard template")
        return render_template('dashboard.html', user_schedules=user_schedules, all_schedules=all_schedules, notes=notes)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template('dashboard.html')
    finally:
        db_session.close()

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Invalid username or password')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@admin.route('/analytics')
@login_required
@admin_required
def analytics_dashboard():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing analytics dashboard")
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        total_users = db_session.query(func.count(User.id)).scalar()
        total_teams = db_session.query(func.count(Team.id)).scalar()
        total_schedules = db_session.query(func.count(Schedule.id)).scalar()
        avg_schedule_hours = db_session.query(func.avg(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600)).scalar()

        user_hours = db_session.query(
            User.username,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(User.username).all()

        team_hours = db_session.query(
            Team.name,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(User).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(Team.name).all()

        time_off_status = db_session.query(
            TimeOffRequest.status,
            func.count(TimeOffRequest.id)
        ).group_by(TimeOffRequest.status).all()

        time_off_trends = db_session.query(
            func.date_trunc('month', TimeOffRequest.start_date).label('month'),
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= six_months_ago).group_by('month').order_by('month').all()

        user_activity = db_session.query(
            User.username,
            func.count(UserActivity.id).label('login_count')
        ).join(UserActivity).filter(UserActivity.timestamp >= thirty_days_ago, UserActivity.activity_type == 'login').group_by(User.username).all()

        return render_template('analytics_dashboard.html',
                               total_users=total_users,
                               total_teams=total_teams,
                               total_schedules=total_schedules,
                               avg_schedule_hours=avg_schedule_hours,
                               user_hours=user_hours,
                               team_hours=team_hours,
                               time_off_status=time_off_status,
                               time_off_trends=time_off_trends,
                               user_activity=user_activity)
    except Exception as e:
        logger.error(f"Error in analytics_dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading the analytics dashboard.', 'error')
        return render_template('analytics_dashboard.html')
    finally:
        db_session.close()

# Add similar try-except-finally blocks for other routes (manage_users, manage_teams, etc.)
# ...
