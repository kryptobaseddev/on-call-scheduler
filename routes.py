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
        logger.info(f"User {current_user.username} accessing index page")
        user_schedules = db_session.query(Schedule).filter_by(user_id=current_user.id).all()
        all_schedules = db_session.query(Schedule).all()
        notes = db_session.query(Note).filter_by(team_id=current_user.team_id).all()
        return render_template('dashboard.html', user_schedules=user_schedules, all_schedules=all_schedules, notes=notes)
    except OperationalError as e:
        logger.error(f"Database connection error in index route: {str(e)}")
        flash('A database error occurred. Please try again later.', 'error')
        return render_template('dashboard.html')
    except SQLAlchemyError as e:
        logger.error(f"Database error in index route: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Unexpected error in index route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('dashboard.html')
    finally:
        db_session.close()

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                'status': 'success',
                'message': 'Login successful',
                'redirect': url_for('main.index')
            })
        return jsonify({
            'status': 'error',
            'message': 'Invalid username or password'
        })
    
    # Automatically log in as admin for testing purposes
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        login_user(admin_user)
        flash('Logged in as admin for testing purposes', 'info')
        return redirect(url_for('main.index'))
    
    return render_template('login.html')

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

        logger.debug("Executing total_users query")
        total_users_query = db_session.query(User)
        logger.debug(f"SQL Query for total_users: {total_users_query}")
        total_users = total_users_query.count()
        logger.debug(f"Total users: {total_users}")

        logger.debug("Executing total_teams query")
        total_teams_query = db_session.query(Team)
        logger.debug(f"SQL Query for total_teams: {total_teams_query}")
        total_teams = total_teams_query.count()
        logger.debug(f"Total teams: {total_teams}")

        logger.debug("Executing total_schedules query")
        total_schedules_query = db_session.query(Schedule)
        logger.debug(f"SQL Query for total_schedules: {total_schedules_query}")
        total_schedules = total_schedules_query.count()
        logger.debug(f"Total schedules: {total_schedules}")

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        logger.debug(f"Calculating statistics for the last 30 days (since {thirty_days_ago})")
        
        logger.debug("Executing user_hours query")
        user_hours_query = db_session.query(
            User.username,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(User.username)
        logger.debug(f"SQL Query for user_hours: {user_hours_query}")
        user_hours = user_hours_query.all()
        logger.debug(f"User hours: {user_hours}")

        logger.debug("Executing team_hours query")
        team_hours_query = db_session.query(
            Team.name,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(User).join(Schedule).filter(Schedule.start_time >= thirty_days_ago).group_by(Team.name)
        logger.debug(f"SQL Query for team_hours: {team_hours_query}")
        team_hours = team_hours_query.all()
        logger.debug(f"Team hours: {team_hours}")

        logger.debug("Executing time_off_status query")
        time_off_status_query = db_session.query(
            TimeOffRequest.status,
            func.count(TimeOffRequest.id)
        ).group_by(TimeOffRequest.status)
        logger.debug(f"SQL Query for time_off_status: {time_off_status_query}")
        time_off_status = time_off_status_query.all()
        logger.debug(f"Time off status: {time_off_status}")

        six_months_ago = datetime.utcnow() - timedelta(days=180)
        logger.debug(f"Calculating time off trends for the last 6 months (since {six_months_ago})")
        time_off_trends_query = db_session.query(
            func.date_trunc('month', TimeOffRequest.start_date).label('month'),
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= six_months_ago).group_by('month').order_by('month')
        logger.debug(f"SQL Query for time_off_trends: {time_off_trends_query}")
        time_off_trends = time_off_trends_query.all()
        logger.debug(f"Time off trends: {time_off_trends}")

        logger.debug("Executing user_activity query")
        user_activity_query = db_session.query(
            User.username,
            func.count(UserActivity.id).label('login_count')
        ).join(UserActivity).filter(UserActivity.timestamp >= thirty_days_ago, UserActivity.activity_type == 'login').group_by(User.username)
        logger.debug(f"SQL Query for user_activity: {user_activity_query}")
        user_activity = user_activity_query.all()
        logger.debug(f"User activity: {user_activity}")

        template_data = {
            'total_users': total_users,
            'total_teams': total_teams,
            'total_schedules': total_schedules,
            'user_hours': user_hours,
            'team_hours': team_hours,
            'time_off_status': time_off_status,
            'time_off_trends': time_off_trends,
            'user_activity': user_activity
        }
        logger.debug(f"Data being passed to template: {template_data}")

        return render_template('analytics_dashboard.html', **template_data)
    except OperationalError as e:
        logger.error(f"Database connection error in analytics_dashboard route: {str(e)}")
        flash('A database connection error occurred. Please try again later.', 'error')
        return render_template('analytics_dashboard.html')
    except SQLAlchemyError as e:
        logger.error(f"Database error in analytics_dashboard route: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return render_template('analytics_dashboard.html')
    except Exception as e:
        logger.error(f"Unexpected error in analytics_dashboard route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
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
        
        try:
            db_session.execute(text('SELECT 1'))
            logger.info("Database connection is working properly")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

        users_query = db_session.query(User)
        logger.debug(f"SQL Query for users: {users_query}")
        users = users_query.all()
        logger.info(f"Retrieved {len(users)} users")
        logger.debug(f"Retrieved users: {[user.username for user in users]}")

        teams_query = db_session.query(Team)
        logger.debug(f"SQL Query for teams: {teams_query}")
        teams = teams_query.all()
        logger.info(f"Retrieved {len(teams)} teams")
        logger.debug(f"Retrieved teams: {[team.name for team in teams]}")

        return render_template('user_management.html', users=users, teams=teams)
    except OperationalError as e:
        logger.error(f"Database connection error in manage_users route: {str(e)}")
        flash('A database connection error occurred. Please try again later.', 'error')
        return render_template('user_management.html', users=[], teams=[])
    except SQLAlchemyError as e:
        logger.error(f"Database error in manage_users route: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return render_template('user_management.html', users=[], teams=[])
    except Exception as e:
        logger.error(f"Unexpected error in manage_users route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('user_management.html', users=[], teams=[])
    finally:
        db_session.close()

@admin.route('/manage_teams')
@login_required
@admin_required
def manage_teams():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing manage teams page")
        
        try:
            db_session.execute(text('SELECT 1'))
            logger.info("Database connection is working properly")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

        teams_query = db_session.query(Team)
        logger.debug(f"SQL Query for teams: {teams_query}")
        teams = teams_query.all()
        logger.info(f"Retrieved {len(teams)} teams")
        logger.debug(f"Retrieved teams: {[team.name for team in teams]}")

        managers_query = db_session.query(User).filter(User.role.in_(['manager', 'admin']))
        logger.debug(f"SQL Query for managers: {managers_query}")
        managers = managers_query.all()
        logger.info(f"Retrieved {len(managers)} managers")
        logger.debug(f"Retrieved managers: {[manager.username for manager in managers]}")

        return render_template('team_management.html', teams=teams, managers=managers)
    except OperationalError as e:
        logger.error(f"Database connection error in manage_teams route: {str(e)}")
        flash('A database connection error occurred. Please try again later.', 'error')
        return render_template('team_management.html', teams=[], managers=[])
    except SQLAlchemyError as e:
        logger.error(f"Database error in manage_teams route: {str(e)}")
        flash('An error occurred while processing your request.', 'error')
        return render_template('team_management.html', teams=[], managers=[])
    except Exception as e:
        logger.error(f"Unexpected error in manage_teams route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return render_template('team_management.html', teams=[], managers=[])
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

            return render_template('custom_report.html', report_type=report_type, start_date=start_date, end_date=end_date, report_data=report_data)
        
        return render_template('custom_report.html')
    except Exception as e:
        logger.error(f"Error in custom_report route: {str(e)}")
        flash('An error occurred while generating the custom report.', 'error')
        return render_template('custom_report.html')
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
        flash('An error occurred while managing schedules.', 'error')
        return render_template('schedule.html')
    finally:
        db_session.close()

@manager.route('/advanced_schedule', methods=['GET', 'POST'])
@login_required
@manager_required
def advanced_schedule():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        if request.method == 'POST':
            team_id = request.form.get('team_id')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            
            schedules = generate_advanced_schedule(team_id, start_date, end_date)
            
            for schedule in schedules:
                db_session.add(schedule)
            db_session.commit()
            
            flash('Advanced schedule generated successfully', 'success')
            return redirect(url_for('manager.advanced_schedule'))
        
        teams = db_session.query(Team).all()
        schedules = db_session.query(Schedule).all()
        return render_template('advanced_schedule.html', teams=teams, schedules=schedules)
    except Exception as e:
        logger.error(f"Error in advanced_schedule route: {str(e)}")
        flash('An error occurred while generating the advanced schedule.', 'error')
        return render_template('advanced_schedule.html')
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
        flash('An error occurred while submitting your time off request.', 'error')
        return render_template('time_off_request.html')
    finally:
        db_session.close()

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))