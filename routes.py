import pytz
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Team, Schedule, Note, TimeOffRequest, UserActivity, TeamColor, Role, Permission
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from scheduling_algorithm import generate_advanced_schedule
import logging
from utils import admin_required, manager_required, get_user_local_time, permission_required
from permissions import *
import traceback
import csv
import io
import pytz
from forms import UserForm, TeamForm, PhoneNumberField
from extensions import db
from sqlalchemy.orm import joinedload

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

logger = logging.getLogger(__name__)

# Rest of your route definitions remain unchanged
@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('auth.login'))

@main.route('/dashboard')
@login_required
@permission_required(VIEW_DASHBOARD)
def dashboard():
    logger.debug(f"User authenticated: {current_user.is_authenticated}")
    logger.debug(f"Current user: {current_user}")
    try:
        logger.debug("Starting index route")
        logger.info(f"User {current_user.username} accessing index page")
        
        logger.debug("Fetching user schedules")
        user_schedules = db.session.query(Schedule).filter_by(user_id=current_user.id).all()
        user_tz = pytz.timezone(current_user.timezone)
        for schedule in user_schedules:
            schedule.start_time = schedule.start_time.replace(tzinfo=timezone.utc).astimezone(user_tz)
            schedule.end_time = schedule.end_time.replace(tzinfo=timezone.utc).astimezone(user_tz)
        if user_schedules is None:
            logger.warning("User schedules query returned None")
            user_schedules = []
        
        logger.debug("Fetching all schedules")
        all_schedules = db.session.query(Schedule).options(
            db.joinedload(Schedule.user).joinedload(User.team).joinedload(Team.color)
        ).all()
        if all_schedules is None:
            logger.warning("All schedules query returned None")
            all_schedules = []
        
        logger.debug("Fetching team notes")
        notes = db.session.query(Note).filter_by(team_id=current_user.team_id).all()
        if notes is None:
            logger.warning("Team notes query returned None")
            notes = []
        
        now = datetime.now(timezone.utc)
        user_local_time = get_user_local_time(current_user)
        on_call_users = db.session.query(User).join(Schedule).filter(
            Schedule.start_time <= now,
            Schedule.end_time >= now
        ).options(db.joinedload(User.team)).all()
       
        logger.debug(f"Rendering dashboard for user {current_user.username}")
        return render_template('dashboard.html', user_schedules=user_schedules, all_schedules=all_schedules, notes=notes, on_call_users=on_call_users, user_local_time=user_local_time)
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
        return "An error occurred", 500
    finally:
        pass

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logger.debug(f"Login attempt for username: {username}")

        try:
            user = db.session.query(User).filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                logger.debug(f"user.is_active: {user.is_active}")
                logger.info(f"Successful login for user: {user.username}")
                login_user(user)
                logger.debug(f"After login_user, current_user.is_authenticated: {current_user.is_authenticated}")
                logger.debug(f"Redirecting user {user.username} to the index page")

                # Redirect to the page the user was trying to access or index
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.dashboard'))
            else:
                logger.warning(f"Failed login attempt for user: {username}")
                flash('Invalid username or password.', 'danger')
                return render_template('login.html')

        except SQLAlchemyError as e:
            logger.error(f"Database error during login: {str(e)}")
            logger.error(traceback.format_exc())
            flash('A database error occurred. Please try again later.', 'danger')
            return render_template('login.html')
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            logger.error(traceback.format_exc())
            flash('An unexpected error occurred. Please try again later.', 'danger')
            return render_template('login.html')
        finally:
            pass

    logger.debug("Rendering login page")
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@admin.route('/analytics', methods=['GET', 'POST'])
@login_required
@permission_required(VIEW_ANALYTICS)
def analytics_dashboard():
    
    try:
        logger.info(f"User {current_user.username} accessing analytics dashboard")
        
        if request.method == 'POST':
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        else:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)

        logger.debug("Fetching total users")
        total_users = db.session.query(func.count(User.id)).scalar()
        logger.debug(f"Total users: {total_users}")

        logger.debug("Fetching total teams")
        total_teams = db.session.query(func.count(Team.id)).scalar()
        logger.debug(f"Total teams: {total_teams}")

        logger.debug("Fetching total schedules")
        total_schedules = db.session.query(func.count(Schedule.id)).scalar()
        logger.debug(f"Total schedules: {total_schedules}")

        logger.debug("Calculating average schedule hours")
        avg_schedule_hours = db.session.query(func.avg(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600)).scalar()
        if avg_schedule_hours is None:
            logger.warning("Average schedule hours is None, setting to 0")
            avg_schedule_hours = 0
        logger.debug(f"Average schedule hours: {avg_schedule_hours:.2f}")

        logger.debug("Fetching user hours")
        user_hours = db.session.query(
            User.username,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(Schedule).filter(Schedule.start_time >= start_date, Schedule.end_time <= end_date).group_by(User.username).all()
        logger.debug(f"User hours: {user_hours}")

        logger.debug("Fetching team hours")
        team_hours = db.session.query(
            Team.name,
            func.sum(func.extract('epoch', Schedule.end_time - Schedule.start_time) / 3600).label('total_hours')
        ).join(User, User.team_id == Team.id).join(Schedule, Schedule.user_id == User.id).filter(
            Schedule.start_time >= start_date, 
            Schedule.end_time <= end_date
        ).group_by(Team.name).all()
        logger.debug(f"Team hours: {team_hours}")

        logger.debug("Fetching time off status")
        time_off_status = db.session.query(
            TimeOffRequest.status,
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= start_date, TimeOffRequest.end_date <= end_date).group_by(TimeOffRequest.status).all()
        logger.debug(f"Time off status: {time_off_status}")

        logger.debug("Fetching time off trends")
        time_off_trends = db.session.query(
            func.date_trunc('month', TimeOffRequest.start_date).label('month'),
            func.count(TimeOffRequest.id)
        ).filter(TimeOffRequest.start_date >= start_date, TimeOffRequest.end_date <= end_date).group_by('month').order_by('month').all()
        logger.debug(f"Time off trends: {time_off_trends}")

        logger.debug("Fetching user activity")
        user_activity = db.session.query(
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
        return render_template('analytics_dashboard.html', start_date=datetime.now(timezone.utc) - timedelta(days=30), end_date=datetime.now(timezone.utc))
    finally:
        pass

@admin.route('/manage_users', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_USERS)
def manage_users():
    form = UserForm()
    if form.validate_on_submit():
        new_user = User(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            work_phone=form.work_phone.data,
            mobile_phone=form.mobile_phone.data,
            timezone=form.timezone.data,
            role_id=form.role_id.data,
            team_id=form.team_id.data if form.team_id.data != 0 else None,
            is_active=form.is_active.data
        )
        if form.password.data:
            new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    
    users = User.query.all()
    return render_template('user_management.html', users=users, form=form)

@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_USERS)
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        form.populate_obj(user)
        if form.password.data:
            user.set_password(form.password.data)
        if form.team_id.data == 0:
            user.team_id = None
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('edit_user.html', form=form, user=user)
    
        
@admin.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_USERS)
def delete_user(user_id):
    try:    
        user = db.session.query(User).get(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in delete_user route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "An error occurred while deleting the user."})
    finally:
        pass
        
@admin.route('/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_USERS)
def toggle_user_status(user_id):
    try:
        user = db.session.query(User).get(user_id)
        user.is_active = not user.is_active
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in toggle_user_status route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "An error occurred while toggling the user status."})
    finally:
        pass

# @admin.route('/manage_teams', methods=['GET', 'POST'])
# @login_required
# @permission_required(MANAGE_TEAMS)
# def manage_teams():
    
#     try:
#         if request.method == 'POST':
#             name = request.form['name']
#             color_id = request.form.get('color_id') or default_color_id()  # No need to pass db.session
#             manager_id = request.form.get('manager_id')
            
#             new_team = Team(name=name, color_id=color_id)
#             if manager_id:
#                 manager = db.session.query(User).get(manager_id)
#                 new_team.manager = manager
            
#             db.session.add(new_team)
#             db.session.commit()
#             flash('Team added successfully!', 'success')
#             return redirect(url_for('admin.manage_teams'))

#         teams = db.session.query(Team).all()
#         managers = db.session.query(User).filter(User.role.in_(['admin', 'manager'])).all()
#         available_colors = db.session.query(TeamColor).all()
#         used_colors = [team.color_id for team in teams]

#         return render_template('team_management.html', 
#                                teams=teams, 
#                                managers=managers, 
#                                available_colors=available_colors,
#                                used_colors=used_colors)
#     except Exception as e:
#         logger.error(f"Error in manage_teams route: {str(e)}")
#         flash('An error occurred while loading team management.', 'error')
#         return render_template('team_management.html', 
#                                teams=[], 
#                                managers=[], 
#                                available_colors=[],
#                                used_colors=[])
#     finally:
#         pass

# def default_color_id():
#     # This function should return the ID of the default color, e.g., blue
#     default_color = TeamColor.query.filter_by(hex_value='#0206f5').first()
#     return default_color.id if default_color else None

# @admin.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
# @login_required
# @permission_required(MANAGE_TEAMS)
# def edit_team(team_id):
    
#     try:
#         team = db.session.query(Team).filter_by(id=team_id).first()
#         if team is None:
#             flash('Team not found.', 'error')
#             return redirect(url_for('admin.manage_teams'))

#         if request.method == 'POST':
#             team.name = request.form['name']
#             team.color_id = request.form['color_id']  # Ensure this matches the form field name
#             manager_id = request.form.get('manager_id')
#             if manager_id:
#                 manager = db.session.query(User).get(manager_id)
#                 team.manager = manager
#             else:
#                 team.manager = None
#             db.session.commit()
#             flash('Team updated successfully!', 'success')
#             return redirect(url_for('admin.manage_teams'))

#         managers = db.session.query(User).filter(User.role.in_(['admin', 'manager'])).all()
#         available_colors = db.session.query(TeamColor).all()
#         used_colors = [t.color_id for t in db.session.query(Team).filter(Team.id != team_id).all()]

#         return render_template('edit_team.html', team=team, managers=managers, available_colors=available_colors, used_colors=used_colors)
#     except Exception as e:
#         logger.error(f"Error in edit_team route: {str(e)}")
#         flash('An error occurred while editing the team.', 'error')
#         return redirect(url_for('admin.manage_teams'))
#     finally:
#         pass

@admin.route('/manage_teams', methods=['GET'])
@login_required
@permission_required(MANAGE_TEAMS)
def manage_teams():
    teams = Team.query.all()
    managers = User.query.filter(User.role.has(name='manager')).all()
    available_colors = TeamColor.query.all()
    used_colors = [team.color_id for team in teams]
    return render_template('manage_teams.html', teams=teams, managers=managers, available_colors=available_colors, used_colors=used_colors)

@admin.route('/create_team', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_TEAMS)
def create_team():
    form = TeamForm()
    if form.validate_on_submit():
        new_team = Team(name=form.name.data, color_id=form.color_id.data, manager_id=form.manager_id.data)
        db.session.add(new_team)
        db.session.commit()
        flash('Team created successfully!', 'success')
        return redirect(url_for('admin.manage_teams'))
    managers = User.query.filter(User.role.has(name='manager')).all()
    available_colors = TeamColor.query.all()
    used_colors = [team.color_id for team in Team.query.all()]
    return render_template('create_team.html', form=form, managers=managers, available_colors=available_colors, used_colors=used_colors)

@admin.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_TEAMS)
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    form = TeamForm(obj=team)
    if form.validate_on_submit():
        form.populate_obj(team)
        db.session.commit()
        flash('Team updated successfully!', 'success')
        return redirect(url_for('admin.manage_teams'))
    managers = User.query.filter(User.role.has(name='manager')).all()
    available_colors = TeamColor.query.all()
    used_colors = [t.color_id for t in Team.query.filter(Team.id != team_id).all()]
    return render_template('edit_team.html', form=form, team=team, managers=managers, available_colors=available_colors, used_colors=used_colors)

@admin.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_TEAMS)
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted successfully!', 'success')
    return redirect(url_for('admin.manage_teams'))

@admin.route('/details_team/<int:team_id>')
@login_required
@permission_required(MANAGE_TEAMS)
def details_team(team_id):
    team = Team.query.get_or_404(team_id)
    return render_template('details_team.html', team=team)

@manager.route('/manage_schedule', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_SCHEDULES)
def manage_schedule():
    
    try:
        logger.info(f"User {current_user.username} accessing manage schedule page")
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            new_schedule = Schedule(user_id=user_id, start_time=start_time, end_time=end_time)
            db.session.add(new_schedule)
            db.session.commit()
            flash('Schedule created successfully', 'success')
            return redirect(url_for('manager.manage_schedule'))
        
        users = db.session.query(User).all()
        schedules = db.session.query(Schedule).order_by(Schedule.start_time.desc()).all()
        return render_template('schedule.html', users=users, schedules=schedules)
    except Exception as e:
        logger.error(f"Error in manage_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while managing schedules.', 'error')
        return render_template('schedule.html')
    finally:
        pass
        
@manager.route('/advanced_schedule', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_SCHEDULES)
def advanced_schedule():
    
    try:
        logger.info(f"User {current_user.username} accessing advanced schedule page")
        # Add any data processing or logic needed for advanced scheduling here
        return render_template('advanced_schedule.html')
    except Exception as e:
        logger.error(f"Error in advanced_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading the advanced scheduling page.', 'error')
        return render_template('advanced_schedule.html')
    finally:
        pass


@user.route('/time_off_request', methods=['GET', 'POST'])
@login_required
@permission_required(REQUEST_TIME_OFF)
def time_off_request():
    try:
        if request.method == 'POST':
            user_tz = pytz.timezone(current_user.timezone)
            start_date = user_tz.localize(datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')).astimezone(timezone.utc)
            end_date = user_tz.localize(datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')).astimezone(timezone.utc)
            
            new_request = TimeOffRequest(user_id=current_user.id, start_date=start_date, end_date=end_date)
            db.session.add(new_request)
            db.session.commit()
            flash('Time off request submitted successfully', 'success')
            return redirect(url_for('main.index'))
        
        return render_template('time_off_request.html')
    except Exception as e:
        logger.error(f"Error in time_off_request route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while submitting your time off request.', 'error')
        return render_template('time_off_request.html')
    finally:
        pass

@admin.route('/custom_report', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_REPORTS)
def custom_report():
    
    try:
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
        pass

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

@manager.route('/edit_schedule/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_SCHEDULES)
def edit_schedule(schedule_id):
    
    try:
        schedule = db.session.query(Schedule).get(schedule_id)
        if not schedule:
            flash('Schedule not found.', 'error')
            return redirect(url_for('manager.manage_schedule'))

        if request.method == 'POST':
            schedule.user_id = request.form.get('user_id')
            schedule.start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
            schedule.end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
            
            db.session.commit()
            flash('Schedule updated successfully.', 'success')
            return redirect(url_for('manager.manage_schedule'))

        users = db.session.query(User).all()
        return render_template('edit_schedule.html', schedule=schedule, users=users)
    except Exception as e:
        logger.error(f"Error in edit_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while editing the schedule.', 'error')
        return redirect(url_for('manager.manage_schedule'))
    finally:
        pass

@manager.route('/delete_schedule/<int:schedule_id>', methods=['GET'])
@login_required
@permission_required(MANAGE_SCHEDULES)
def delete_schedule(schedule_id):
    
    try:
        schedule = db.session.query(Schedule).get(schedule_id)
        if schedule:
            db.session.delete(schedule)
            db.session.commit()
            flash('Schedule deleted successfully.', 'success')
        else:
            flash('Schedule not found.', 'error')
        return redirect(url_for('manager.manage_schedule'))
    except Exception as e:
        logger.error(f"Error in delete_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while deleting the schedule.', 'error')
        return redirect(url_for('manager.manage_schedule'))
    finally:
        pass

@manager.route('/batch_delete_schedules', methods=['POST'])
@login_required
@permission_required(MANAGE_SCHEDULES)
def batch_delete_schedules():
    
    try:
        schedule_ids = request.form.getlist('schedule_ids[]')
        if schedule_ids:
            db.session.query(Schedule).filter(Schedule.id.in_(schedule_ids)).delete(synchronize_session=False)
            db.session.commit()
            flash(f'{len(schedule_ids)} schedules deleted successfully.', 'success')
        else:
            flash('No schedules selected for deletion.', 'warning')
        return redirect(url_for('manager.manage_schedule'))
    except Exception as e:
        logger.error(f"Error in batch_delete_schedules route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while deleting the schedules.', 'error')
        return redirect(url_for('manager.manage_schedule'))
    finally:
        pass

@manager.route('/my_team', methods=['GET', 'POST'])
@login_required
@permission_required(VIEW_TEAM)
def my_team():
    
    try:
        managed_teams = current_user.managed_teams
        if not managed_teams:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "error", "message": "You are not assigned to manage any team."})
            flash('You are not assigned to manage any team.', 'warning')
            return render_template('my_team.html', managed_teams=[], selected_team=None, team_members=[], team_notes=[], archived_notes=[])

        selected_team_id = request.args.get('team_id', type=int) or request.form.get('team_id', type=int)
        selected_team = next((team for team in managed_teams if team.id == selected_team_id), managed_teams[0])

        if request.method == 'POST':
            if 'update_sequence' in request.form:
                try:
                    new_sequence = request.form.getlist('user_sequence')
                    for index, user_id in enumerate(new_sequence):
                        user = db.session.query(User).get(int(user_id))
                        if user and user.team_id == selected_team.id:
                            user.call_sequence = index + 1
                    db.session.commit()
                    flash(f"{selected_team.name} Call Sequence Updated", 'success')
                    return redirect(url_for('manager.my_team', team_id=selected_team.id))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error updating call sequence: {str(e)}")
                    flash(f"Error updating call sequence: {str(e)}", 'danger')
                    return redirect(url_for('manager.my_team', team_id=selected_team.id))
            
            elif 'add_note' in request.form:
                note_content = request.form.get('note_content')
                is_priority = request.form.get('is_priority') == 'on'
                if note_content:
                    try:
                        new_note = Note(content=note_content, created_at=datetime.utcnow(), team_id=selected_team.id, is_priority=is_priority)
                        db.session.add(new_note)
                        db.session.commit()
                        flash("Team note added successfully", 'success')
                        return redirect(url_for('manager.my_team', team_id=selected_team.id))
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error adding note: {str(e)}")
                        flash("An error occurred while adding the note.", 'danger')
                        return redirect(url_for('manager.my_team', team_id=selected_team.id))
                else:
                    flash("Note content is required.", 'warning')
                    return redirect(url_for('manager.my_team', team_id=selected_team.id))

        # Fetch team members and notes
        team_members = db.session.query(User).filter_by(team_id=selected_team.id).order_by(User.call_sequence).all()
        team_notes = db.session.query(Note).filter_by(team_id=selected_team.id, is_archived=False).order_by(Note.created_at.desc()).all()
        archived_notes = db.session.query(Note).filter_by(team_id=selected_team.id, is_archived=True).order_by(Note.created_at.desc()).all()

        # Add a debug log statement to log the notes
        logger.debug(f"Fetched notes for team {selected_team.id}: {[note.content for note in team_notes]}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "status": "success",
                "html": render_template('my_team.html', 
                                        managed_teams=managed_teams,
                                        selected_team=selected_team, 
                                        team_members=team_members, 
                                        team_notes=team_notes,
                                        archived_notes=archived_notes)
            })
        return render_template('my_team.html', 
                               managed_teams=managed_teams,
                               selected_team=selected_team, 
                               team_members=team_members, 
                               team_notes=team_notes,
                               archived_notes=archived_notes)
    except Exception as e:
        logger.error(f"Error in my_team route: {str(e)}")
        logger.error(traceback.format_exc())
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"})
        flash('An error occurred while loading the team management page.', 'error')
        return render_template('my_team.html', managed_teams=[], selected_team=None, team_members=[], team_notes=[], archived_notes=[])
    finally:
        pass

@manager.route('/edit_note/<int:note_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_NOTES)
def edit_note(note_id):
    
    try:
        note = db.session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            note.content = request.form.get('content')
            note.is_priority = request.form.get('is_priority') == 'true'
            db.session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in edit_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while editing the note"}), 500
    finally:
        pass

@manager.route('/archive_note/<int:note_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_NOTES)
def archive_note(note_id):
    
    try:
        note = db.session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            note.is_archived = True
            db.session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in archive_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while archiving the note"}), 500
    finally:
        pass

@manager.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_NOTES)
def delete_note(note_id):
    
    try:
        note = db.session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            db.session.delete(note)
            db.session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in delete_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while deleting the note"}), 500
    finally:
        pass

@manager.route('/unarchive_note/<int:note_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_NOTES)
def unarchive_note(note_id):
    
    try:
        note = db.session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            note.is_archived = False
            db.session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in unarchive_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while activating the note"}), 500
    finally:
        pass

@admin.route('/manage_colors', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_COLORS)
def manage_colors():
    
    try:
        if request.method == 'POST':
            hex_value = request.form.get('hex_value')
            try:
                new_color = TeamColor(hex_value=hex_value)
                db.session.add(new_color)
                db.session.commit()
                flash('Color added successfully!', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('This color already exists.', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'error')
        
        colors = db.session.query(TeamColor).all()
        return render_template('manage_colors.html', colors=colors)
    except Exception as e:
        logger.error(f"Error in manage_colors route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while managing colors.', 'error')
        return render_template('manage_colors.html', colors=[])
    finally:
        pass

@admin.route('/delete_color/<int:color_id>', methods=['POST'])
@login_required
@permission_required(MANAGE_COLORS)
def delete_color(color_id):
    
    try:
        color = db.session.query(TeamColor).get(color_id)
        if color and not color.is_assigned and not color.is_core:
            db.session.delete(color)
            db.session.commit()
            flash('Color deleted successfully!', 'success')
        elif color.is_core:
            flash('Core colors cannot be deleted.', 'warning')
        else:
            flash('Color cannot be deleted because it is assigned to a team.', 'warning')
    except Exception as e:
        logger.error(f"Error deleting color: {str(e)}")
        flash('An error occurred while deleting the color.', 'error')
    finally:
        pass
    return redirect(url_for('admin.manage_colors'))

@admin.route('/edit_color/<int:color_id>', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_COLORS)
def edit_color(color_id):
    
    try:
        color = db.session.query(TeamColor).get(color_id)
        if request.method == 'POST':
            color.hex_value = request.form['hex_value']
            db.session.commit()
            flash('Color updated successfully!', 'success')
            return redirect(url_for('admin.manage_colors'))
        return render_template('edit_color.html', color=color)
    except Exception as e:
        logger.error(f"Error in edit_color route: {str(e)}")
        flash('An error occurred while editing the color.', 'error')
    finally:
        pass
    return render_template('edit_color.html', color=None)    

@admin.route('/check_colors')
@login_required
@permission_required(MANAGE_COLORS)
def check_colors():
    
    try:
        colors = db.session.query(TeamColor).all()
        return jsonify([{"id": color.id, "hex_value": color.hex_value} for color in colors])
    except Exception as e:
        logger.error(f"Error checking colors: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        pass

# Check to see if core colors exist based on hex values, if not seed them
def seed_core_colors():
    core_colors = [
        "#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#FF00FF",
        "#00FFFF", "#FFA500", "#800080", "#8B4513", "#808000",
        "#FF6347", "#4682B4", "#32CD32", "#FFD700", "#8A2BE2",
        "#5F9EA0", "#DC143C", "#7FFF00", "#FF69B4", "#B22222"
    ]
    try:
        for hex_value in core_colors:
            color = TeamColor.query.filter_by(hex_value=hex_value).first()
            if color:
                # Update existing color
                color.is_core = True
            else:
                # Create new color if it doesn't exist
                new_color = TeamColor(hex_value=hex_value, is_core=True)
                db.session.add(new_color)

        db.session.commit()
        current_app.logger.info("Core colors seeded/updated successfully")
    except Exception as e:
        current_app.logger.error(f"Error seeding/updating core colors: {str(e)}")
        db.session.rollback()
    finally:
        pass

@admin.route('/roles')
@login_required
@permission_required(MANAGE_ROLES)
def list_roles():
    roles = Role.query.all()
    return render_template('roles.html', roles=roles)

@admin.route('/roles/create', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_ROLES)
def create_role():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.commit()
        flash('Role created successfully', 'success')
        return redirect(url_for('admin.list_roles'))
    return render_template('create_role.html')

@admin.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(MANAGE_ROLES)
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    if request.method == 'POST':
        role.name = request.form.get('name')
        role.description = request.form.get('description')
        # Update permissions
        selected_permissions = request.form.getlist('permissions')
        role.permissions = [Permission.query.get(int(pid)) for pid in selected_permissions]
        db.session.commit()
        flash('Role updated successfully', 'success')
        return redirect(url_for('admin.list_roles'))
    permissions = Permission.query.all()
    return render_template('edit_role.html', role=role, permissions=permissions)
