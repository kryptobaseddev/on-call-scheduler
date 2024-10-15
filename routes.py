from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, set_access_cookies
from models import User, Team, Schedule, TimeOffRequest, Note
from app import db
from utils import admin_required, manager_required
from datetime import datetime, timedelta

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__)
manager = Blueprint('manager', __name__)
user = Blueprint('user', __name__)

@main.route('/')
def index():
    return render_template('login.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            access_token = create_access_token(identity=user.id)
            response = jsonify({"msg": "Login successful"})
            set_access_cookies(response, access_token)
            return redirect(url_for('main.dashboard'))
        return jsonify({"msg": "Bad username or password"}), 401
    return render_template('login.html')

@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@admin.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        team_id = request.form.get('team_id')
        
        new_user = User(username=username, email=email, role=role, team_id=team_id)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
    users = User.query.all()
    return render_template('user_management.html', users=users)

@admin.route('/teams', methods=['GET', 'POST'])
@admin_required
def manage_teams():
    if request.method == 'POST':
        name = request.form.get('name')
        manager_id = request.form.get('manager_id')
        
        new_team = Team(name=name, manager_id=manager_id)
        db.session.add(new_team)
        db.session.commit()
        
    teams = Team.query.all()
    return render_template('team_management.html', teams=teams)

@manager.route('/schedule', methods=['GET', 'POST'])
@manager_required
def manage_schedule():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        
        new_schedule = Schedule(user_id=user_id, start_time=start_time, end_time=end_time)
        db.session.add(new_schedule)
        db.session.commit()
    
    team_id = current_user.team_id
    team = Team.query.get(team_id)
    schedules = Schedule.query.join(User).filter(User.team_id == team_id).all()
    return render_template('schedule.html', schedules=schedules, team=team)

@user.route('/my_schedule')
@login_required
def view_schedule():
    schedules = Schedule.query.filter_by(user_id=current_user.id).all()
    return render_template('schedule.html', schedules=schedules)

@user.route('/time_off', methods=['GET', 'POST'])
@login_required
def time_off():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        
        new_request = TimeOffRequest(user_id=current_user.id, start_date=start_date, end_date=end_date)
        db.session.add(new_request)
        db.session.commit()
    
    requests = TimeOffRequest.query.filter_by(user_id=current_user.id).all()
    return render_template('timeoff.html', requests=requests)

@manager.route('/time_off_requests', methods=['GET', 'POST'])
@manager_required
def manage_time_off():
    if request.method == 'POST':
        request_id = request.form.get('request_id')
        status = request.form.get('status')
        
        time_off_request = TimeOffRequest.query.get(request_id)
        time_off_request.status = status
        db.session.commit()
    
    team_id = current_user.team_id
    requests = TimeOffRequest.query.join(User).filter(User.team_id == team_id).all()
    return render_template('timeoff.html', requests=requests)

@main.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    if request.method == 'POST':
        content = request.form.get('content')
        team_id = request.form.get('team_id')
        
        new_note = Note(content=content, created_at=datetime.utcnow(), team_id=team_id)
        db.session.add(new_note)
        db.session.commit()
    
    notes = Note.query.filter_by(team_id=current_user.team_id).all()
    return render_template('dashboard.html', notes=notes)