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

from flask import jsonify

@auth.route('/login', methods=['GET', 'POST'])
def login():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logger.debug(f"Login attempt for username: {username}")

        try:
            user = db_session.query(User).filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                logger.info(f"Successful login for user: {user.username}")
                login_user(user)
                logger.debug(f"Redirecting user {user.username} to the index page")
                return jsonify({"status": "success", "redirect": url_for('main.index')})
            else:
                logger.warning(f"Failed login attempt for user: {username}")
                return jsonify({"status": "error", "message": "Invalid username or password"})

        except SQLAlchemyError as e:
            logger.error(f"Database error during login: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"status": "error", "message": "A database error occurred. Please try again later."})
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"status": "error", "message": "An unexpected error occurred. Please try again later."})
        finally:
            db_session.close()
    
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
        ).join(User, User.team_id == Team.id).join(Schedule, Schedule.user_id == User.id).filter(
            Schedule.start_time >= start_date, 
            Schedule.end_time <= end_date
        ).group_by(Team.name).all()
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
        return render_template('analytics_dashboard.html', start_date=datetime.utcnow() - timedelta(days=30), end_date=datetime.utcnow())
    finally:
        db_session.close()

@admin.route('/manage_users', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_users():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        logger.info(f"User {current_user.username} accessing manage users page")
        
        if request.method == 'POST':
            # Handle user creation here
            username = request.form.get('username')
            email = request.form.get('email')
            mobile_phone = request.form.get('mobile_phone')
            role = request.form.get('role')
            team_id = request.form.get('team_id')
            password = request.form.get('password')

            if not username or not email or not role or not team_id or not password or not mobile_phone:
                flash('All fields are required.', 'error')
                return redirect(url_for('admin.manage_users'))
            
            new_user = User(username=username, email=email, role=role, team_id=team_id, password_hash=generate_password_hash(password), mobile_phone=mobile_phone)
            db_session.add(new_user)
            db_session.commit()
            flash('User created successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
        
        users = db_session.query(User).all()
        teams = db_session.query(Team).all()
        
        logger.debug(f"Fetched {len(users)} users and {len(teams)} teams")
        
        return render_template('user_management.html', users=users, teams=teams)
    except Exception as e:
        logger.error(f"Error in manage_users route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading user management.', 'error')
        return render_template('user_management.html', users=[], teams=[])
    finally:
        db_session.close()

@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin.manage_users'))

        if request.method == 'POST':
            user.username = request.form.get('username')
            user.email = request.form.get('email')
            user.role = request.form.get('role')
            user.team_id = request.form.get('team_id') or None
            user.mobile_phone = request.form.get('mobile_phone')
            if request.form.get('password'):
                user.password_hash = generate_password_hash(request.form.get('password'))
            
            db_session.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.manage_users'))

        teams = db_session.query(Team).all()
        return render_template('edit_user.html', user=user, teams=teams)
    except Exception as e:
        logger.error(f"Error in edit_user route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while editing the user.', 'error')
        return redirect(url_for('admin.manage_users'))
    finally:
        db_session.close()

@admin.route('/manage_teams', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_teams():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        if request.method == 'POST':
            name = request.form['name']
            color = request.form['color']
            manager_id = request.form.get('manager_id')
            
            new_team = Team(name=name, color=color)
            if manager_id:
                manager = db_session.query(User).get(manager_id)
                new_team.manager = manager
            
            db_session.add(new_team)
            db_session.commit()
            flash('Team added successfully!', 'success')
            return redirect(url_for('admin.manage_teams'))

        teams = db_session.query(Team).all()
        managers = db_session.query(User).filter(User.role.in_(['admin', 'manager'])).all()
        color_palette = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]
        used_colors = [team.color for team in teams]

        return render_template('team_management.html', 
                               teams=teams, 
                               managers=managers, 
                               available_colors=color_palette,
                               used_colors=used_colors)
    except Exception as e:
        logger.error(f"Error in manage_teams route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading team management.', 'error')
        return render_template('team_management.html', 
                               teams=[], 
                               managers=[], 
                               available_colors=color_palette,
                               used_colors=[])
    finally:
        db_session.close()

@admin.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_team(team_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        team = db_session.query(Team).filter_by(id=team_id).first()
        if team is None:
            flash('Team not found.', 'error')
            return redirect(url_for('admin.manage_teams'))

        if request.method == 'POST':
            team.name = request.form['name']
            team.color = request.form['color']
            manager_id = request.form.get('manager_id')
            if manager_id:
                manager = db_session.query(User).get(manager_id)
                team.manager = manager
            else:
                team.manager = None
            db_session.commit()
            flash('Team updated successfully!', 'success')
            return redirect(url_for('admin.manage_teams'))

        managers = db_session.query(User).filter(User.role.in_(['admin', 'manager'])).all()
        color_palette = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]
        used_colors = [t.color for t in db_session.query(Team).filter(Team.id != team_id).all()]

        return render_template('edit_team.html', team=team, managers=managers, available_colors=color_palette, used_colors=used_colors)
    except Exception as e:
        logger.error(f"Error in edit_team route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while editing the team.', 'error')
        return redirect(url_for('admin.manage_teams'))
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
        schedules = db_session.query(Schedule).order_by(Schedule.start_time.desc()).all()
        return render_template('schedule.html', users=users, schedules=schedules)
    except Exception as e:
        logger.error(f"Error in manage_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
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
        logger.info(f"User {current_user.username} accessing advanced schedule page")
        # Add any data processing or logic needed for advanced scheduling here
        return render_template('advanced_schedule.html')
    except Exception as e:
        logger.error(f"Error in advanced_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while loading the advanced scheduling page.', 'error')
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

@manager.route('/edit_schedule/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_schedule(schedule_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        schedule = db_session.query(Schedule).get(schedule_id)
        if not schedule:
            flash('Schedule not found.', 'error')
            return redirect(url_for('manager.manage_schedule'))

        if request.method == 'POST':
            schedule.user_id = request.form.get('user_id')
            schedule.start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
            schedule.end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
            
            db_session.commit()
            flash('Schedule updated successfully.', 'success')
            return redirect(url_for('manager.manage_schedule'))

        users = db_session.query(User).all()
        return render_template('edit_schedule.html', schedule=schedule, users=users)
    except Exception as e:
        logger.error(f"Error in edit_schedule route: {str(e)}")
        logger.error(traceback.format_exc())
        flash('An error occurred while editing the schedule.', 'error')
        return redirect(url_for('manager.manage_schedule'))
    finally:
        db_session.close()

@manager.route('/delete_schedule/<int:schedule_id>', methods=['GET'])
@login_required
@manager_required
def delete_schedule(schedule_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        schedule = db_session.query(Schedule).get(schedule_id)
        if schedule:
            db_session.delete(schedule)
            db_session.commit()
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
        db_session.close()

@manager.route('/batch_delete_schedules', methods=['POST'])
@login_required
@manager_required
def batch_delete_schedules():
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        schedule_ids = request.form.getlist('schedule_ids[]')
        if schedule_ids:
            db_session.query(Schedule).filter(Schedule.id.in_(schedule_ids)).delete(synchronize_session=False)
            db_session.commit()
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
        db_session.close()

@manager.route('/my_team', methods=['GET', 'POST'])
@login_required
@manager_required
def my_team():
    db_session = current_app.extensions['sqlalchemy']['db_session']
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
                        user = db_session.query(User).get(int(user_id))
                        if user and user.team_id == selected_team.id:
                            user.call_sequence = index + 1
                    db_session.commit()
                    flash(f"{selected_team.name} Call Sequence Updated", 'success')
                    return redirect(url_for('manager.my_team', team_id=selected_team.id))
                except Exception as e:
                    db_session.rollback()
                    logger.error(f"Error updating call sequence: {str(e)}")
                    flash(f"Error updating call sequence: {str(e)}", 'danger')
                    return redirect(url_for('manager.my_team', team_id=selected_team.id))
            
            elif 'add_note' in request.form:
                note_content = request.form.get('note_content')
                is_priority = request.form.get('is_priority') == 'on'
                if note_content:
                    try:
                        new_note = Note(content=note_content, created_at=datetime.utcnow(), team_id=selected_team.id, is_priority=is_priority)
                        db_session.add(new_note)
                        db_session.commit()
                        flash("Team note added successfully", 'success')
                        return redirect(url_for('manager.my_team', team_id=selected_team.id))
                    except Exception as e:
                        db_session.rollback()
                        logger.error(f"Error adding note: {str(e)}")
                        flash("An error occurred while adding the note.", 'danger')
                        return redirect(url_for('manager.my_team', team_id=selected_team.id))
                else:
                    flash("Note content is required.", 'warning')
                    return redirect(url_for('manager.my_team', team_id=selected_team.id))

        # Fetch team members and notes
        team_members = db_session.query(User).filter_by(team_id=selected_team.id).order_by(User.call_sequence).all()
        team_notes = db_session.query(Note).filter_by(team_id=selected_team.id, is_archived=False).order_by(Note.created_at.desc()).all()
        archived_notes = db_session.query(Note).filter_by(team_id=selected_team.id, is_archived=True).order_by(Note.created_at.desc()).all()

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
        db_session.close()

@manager.route('/edit_note/<int:note_id>', methods=['POST'])
@login_required
@manager_required
def edit_note(note_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        note = db_session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            note.content = request.form.get('content')
            note.is_priority = request.form.get('is_priority') == 'true'
            db_session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in edit_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while editing the note"}), 500
    finally:
        db_session.close()

@manager.route('/archive_note/<int:note_id>', methods=['POST'])
@login_required
@manager_required
def archive_note(note_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        note = db_session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            note.is_archived = True
            db_session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in archive_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while archiving the note"}), 500
    finally:
        db_session.close()

@manager.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
@manager_required
def delete_note(note_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        note = db_session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            db_session.delete(note)
            db_session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in delete_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while deleting the note"}), 500
    finally:
        db_session.close()

@manager.route('/unarchive_note/<int:note_id>', methods=['POST'])
@login_required
@manager_required
def unarchive_note(note_id):
    db_session = current_app.extensions['sqlalchemy']['db_session']
    try:
        note = db_session.query(Note).get(note_id)
        if note and note.team.manager_id == current_user.id:
            note.is_archived = False
            db_session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Note not found or unauthorized"}), 404
    except Exception as e:
        logger.error(f"Error in unarchive_note route: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while activating the note"}), 500
    finally:
        db_session.close()