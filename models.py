from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    mobile_phone = db.Column(db.String(20))
    call_sequence = db.Column(db.Integer, default=0)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    color = db.Column(db.String(7), default="#000000")
    users = db.relationship('User', backref='team', lazy='dynamic', foreign_keys=[User.team_id])
    manager = db.relationship('User', backref=db.backref('managed_team', uselist=False), lazy='joined', foreign_keys=[manager_id])
    notes = db.relationship('Note', backref='team', lazy='dynamic')

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('schedules', lazy='dynamic'))

class TimeOffRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('time_off_requests', lazy='dynamic'))

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    editable_by = db.Column(db.String(20), default='both')

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))
