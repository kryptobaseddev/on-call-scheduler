from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Team, Schedule, Note, TimeOffRequest, UserActivity
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from scheduling_algorithm import generate_advanced_schedule
import logging
from utils import admin_required, manager_required
import traceback
import csv
import io

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
    except OperationalError as e:
        logger.error(f"Database connection error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('A database error occurred. Please try again later.', 'error')
        return render_template('dashboard.html')
    except SQLAlchemyError as e:
        logger.error(f"Database error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while processing your request.', 'error')
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Unexpected error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('dashboard.html')
    finally:
        db_session.close()

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logger.debug(f"Login attempt for username: {username}")
        
        try:
            user = User.query.filter_by(username=username).first()
            if user:
                logger.debug(f"User found: {user.username}")
                if check_password_hash(user.password_hash, password):
                    logger.info(f"Successful login for user: {user.username}")
                    login_user(user)
                    return redirect(url_for('main.index'))
                else:
                    logger.warning(f"Failed login attempt for user: {user.username} - Invalid password")
            else:
                logger.warning(f"Failed login attempt - User not found: {username}")
            
            flash('Invalid username or password')
        except SQLAlchemyError as e:
            logger.error(f"Database error during login: {str(e)}")
            logger.error(traceback.format_exc())
            flash('A database error occurred. Please try again later.', 'error')
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            logger.error(traceback.format_exc())
            flash('An unexpected error occurred. Please try again later.', 'error')
    
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@admin.route('/analytics', methods=['GET', 'POST'])
@login_required
@admin_required
def analytics_dashboard():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing analytics dashboard")
        
        if request.method == 'POST':
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        else:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)

        logger.debug("Fetching total users")
        total_users = db_session.query(func.count(User.id)).scalar()
        logger.debug(f"Total users: {total_users}")

        logger.debug("Fetching total teams")
        total_teams = db_session.query(func.count(Team.id)).scalar()
        logger.debug(f"Total teams: {total_teams}")

        logger.debug("Fetching total schedules")
        total_schedules = db_session.query(func.count(Schedule.id)).scalar()
        logger.debug(f"Total schedules: {total_schedules}")

        logger.debug("Calculating average schedule hours")
        avg_schedule_hours = db_session.query(func.avg(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600)).scalar()
        if avg_schedule_hours is None:
            logger.warning("Average schedule hours is None, setting to 0")
            avg_schedule_hours = 0
        logger.debug(f"Average schedule hours: {avg_schedule_hours:.2f}")

        logger.debug("Fetching user hours")
        user_hours = db_session.query(
            User.username,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(User.username).all()
        logger.debug(f"User hours: {user_hours}")

        logger.debug("Fetching team hours")
        team_hours = db_session.query(
            Team.name,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(User).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(Team.name).all()
        logger.debug(f"Team hours: {team_hours}")

        logger.debug("Fetching time off status")
        time_off_status = db_session.query(
            TimeOffRequest.status,
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= start_date, TimeOffRequest.end_date <= end_date).group_by(TimeOffRequest.status).all()
        logger.debug(f"Time off status: {time_off_status}")

        logger.debug("Fetching time off trends")
        time_off_trends = db_session.query(
            func.date_trunc('month', TimeOffRequest.start_date).label('month'),
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= start_date, TimeOffRequest.end_date <= end_date).group_by('month').order_by('month').all()
        logger.debug(f"Time off trends: {time_off_trends}")

        logger.debug("Fetching user activity")
        user_activity = db_session.query(
            User.username,
            func.count(UserActivity.id).label('login_count')
        ).join(UserActivity).filter(UserActivity.timestamp >= start_date, UserActivity.timestamp <= end_date, UserActivity.activity_type == 'login').group_by(User.username).all()
        logger.debug(f"User activity: {user_activity}")

        return render_template('analytics_dashboard.html',
                               total_users=total_users,
                               total_teams=total_teams,
                               total_schedules=total_schedules,
                               avg_schedule_hours=round(avg_schedule_hours, 2),
                               user_hours=user_hours,
                               team_hours=team_hours,
                               time_off_status=time_off_status,
                               time_off_trends=time_off_trends,
                               user_activity=user_activity,
                               start_date=start_date,
                               end_date=end_date)
    except Exception as e:
        logger.error(f"Error in analytics_dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading the analytics dashboard.', 'error')
        return render_template('analytics_dashboard.html')
    finally:
        db_session.close()

@admin.route('/manage_users')
@login_required
@admin_required
def manage_users():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing manage users page")
        users = db_session.query(User).all()
        teams = db_session.query(Team).all()
        return render_template('user_management.html', users=users, teams=teams)
    except Exception as e:
        logger.error(f"Error in manage_users route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading user management.', 'error')
        return render_template('user_management.html')
    finally:
        db_session.close()

@admin.route('/manage_teams')
@login_required
@admin_required
def manage_teams():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing manage teams page")
        teams = db_session.query(Team).all()
        managers = db_session.query(User).filter(User.role.in_(['manager', 'admin'])).all()
        return render_template('team_management.html', teams=teams, managers=managers)
    except Exception as e:
        logger.error(f"Error in manage_teams route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading team management.', 'error')
        return render_template('team_management.html')
    finally:
        db_session.close()

@manager.route('/manage_schedule', methods=['GET', 'POST'])
@login_required
@manager_required
def manage_schedule():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing manage schedule page")
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            new_schedule = Schedule(user_id=user_id, start_time=start_time, end_time=end_time)
            db_session.add(new_schedule)
            db_session.commit()
            flash('Schedule created successfully', 'success')
            return redirect(url_for('manager.manage_schedule'))
        
        users = db_session.query(User).all()
        schedules = db_session.query(Schedule).all()
        return render_template('schedule.html', users=users, schedules=schedules)
    except Exception as e:
        logger.error(f"Error in manage_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while managing schedules.', 'error')
        return render_template('schedule.html')
    finally:
        db_session.close()

@user.route('/time_off_request', methods=['GET', 'POST'])
@login_required
def time_off_request():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        if request.method == 'POST':
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            
            new_request = TimeOffRequest(user_id=current_user.id, start_date=start_date, end_date=end_date)
            db_session.add(new_request)
            db_session.commit()
            flash('Time off request submitted successfully', 'success')
            return redirect(url_for('main.index'))
        
        return render_template('time_off_request.html')
    except Exception as e:
        logger.error(f"Error in time_off_request route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while submitting your time off request.', 'error')
        return render_template('time_off_request.html')
    finally:
        db_session.close()

@admin.route('/custom_report', methods=['GET', 'POST'])
@login_required
@admin_required
def custom_report():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        if request.method == 'POST':
            report_type = request.form.get('report_type')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')

            if report_type == 'user_hours':
                report_data = db_session.query(
                    User.username,
                    func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
                ).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(User.username).all()
            elif report_type == 'team_hours':
                report_data = db_session.query(
                    Team.name,
                    func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
                ).join(User).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(Team.name).all()
            elif report_type == 'time_off_requests':
                report_data = db_session.query(
                    User.username,
                    TimeOffRequest.start_date,
                    TimeOffRequest.end_date,
                    TimeOffRequest.status
                ).join(TimeOffRequest).filter(TimeOffRequest.start_date >= start_date, TimeOffRequest.end_date <= end_date).all()
            else:
                report_data = []

            if request.form.get('export') == 'csv':
                return export_to_csv(report_type, report_data)

            return render_template('custom_report.html', report_type=report_type, start_date=start_date, end_date=end_date, report_data=report_data)
        
        return render_template('custom_report.html')
    except Exception as e:
        logger.error(f"Error in custom_report route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while generating the custom report.', 'error')
        return render_template('custom_report.html')
    finally:
        db_session.close()

def export_to_csv(report_type, report_data):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'user_hours' or report_type == 'team_hours':
        writer.writerow(['Name', 'Total Hours'])
        for row in report_data:
            writer.writerow([row[0], f"{row[1]:.2f}"])
    elif report_type == 'time_off_requests':
        writer.writerow(['Username', 'Start Date', 'End Date', 'Status'])
        for row in report_data:
            writer.writerow([row[0], row[1].strftime('%Y-%m-%d'), row[2].strftime('%Y-%m-%d'), row[3]])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename=f'{report_type}_report.csv'
    )