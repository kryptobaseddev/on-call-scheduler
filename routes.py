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
from werkzeug.routing.exceptions import BuildError

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

@main.route('/')
@login_required
def index():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing index page")
        user_schedules = db_session.query(Schedule).filter_by(user_id=current_user.id).all()
        all_schedules = db_session.query(Schedule).all()
        notes = db_session.query(Note).filter_by(team_id=current_user.team_id).all()
        return render_template('dashboard.html', user_schedules=user_schedules, all_schedules=all_schedules, notes=notes)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template('dashboard.html')
    finally:
        db_session.close()

@admin.route('/analytics')
@login_required
@admin_required
def analytics_dashboard():
    logger.debug('Starting analytics_dashboard route')
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing analytics dashboard")
        
        try:
            db_session.execute(text('SELECT 1'))
            logger.info("Database connection is working properly")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        # Combine queries for better performance
        analytics_data = db_session.query(
            func.count(func.distinct(User.id)).label('total_users'),
            func.count(func.distinct(Team.id)).label('total_teams'),
            func.count(func.distinct(Schedule.id)).label('total_schedules'),
            func.avg(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('avg_schedule_hours')
        ).select_from(User).outerjoin(Team).outerjoin(Schedule).first()

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

        template_data = {
            'total_users': analytics_data.total_users or 0,
            'total_teams': analytics_data.total_teams or 0,
            'total_schedules': analytics_data.total_schedules or 0,
            'avg_schedule_hours': round(analytics_data.avg_schedule_hours or 0, 2),
            'user_hours': user_hours or [],
            'team_hours': team_hours or [],
            'time_off_status': time_off_status or [],
            'time_off_trends': time_off_trends or [],
            'user_activity': user_activity or []
        }
        logger.debug(f"Data being passed to template: {template_data}")

        return render_template('analytics_dashboard.html', **template_data)
    except BuildError as e:
        logger.error(f"URL build error in analytics_dashboard route: {str(e)}")
        flash('An error occurred while building the URL. Please check if all blueprints are correctly registered.', 'error')
        return render_template('error.html', error_message="URL build error. Please contact the administrator.")
    except OperationalError as e:
        logger.error(f"Database connection error in analytics_dashboard route: {str(e)}")
        flash('A database connection error occurred. Please try again later.', 'error')
        return render_template('error.html', error_message="Database connection error. Please try again later.")
    except SQLAlchemyError as e:
        logger.error(f"Database error in analytics_dashboard route: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return render_template('error.html', error_message="Database error. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error in analytics_dashboard route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('error.html', error_message="An unexpected error occurred. Please try again later.")
    finally:
        db_session.close()

# Add other routes here (manager, user)
