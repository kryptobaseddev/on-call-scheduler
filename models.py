from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from helpers import format_phone_number

# Association table for team managers
team_managers = db.Table('team_managers',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

# Association table for role permissions
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # This tells SQLAlchemy to use 'users' as the table name
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    role = db.relationship('Role', backref='users')
    team_id = db.Column(
        db.Integer,
        db.ForeignKey('team.id', name='fk_users_team_id_team', use_alter=True, deferrable=True, initially='DEFERRED'),
        nullable=True
    )
    _work_phone = db.Column('work_phone', db.String(20))
    _mobile_phone = db.Column('mobile_phone', db.String(20))
    call_sequence = db.Column(db.Integer, default=0)
    timezone = db.Column(db.String(50), default='UTC')
    is_active = db.Column(db.Boolean, default=True)
    
    def has_permission(self, perm_name):
        if self.role and self.role.permissions:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                return permission in self.role.permissions
        return False
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def work_phone(self):
        return format_phone_number(self._work_phone)

    @work_phone.setter
    def work_phone(self, value):
        self._work_phone = value

    @property
    def mobile_phone(self):
        return format_phone_number(self._mobile_phone)

    @mobile_phone.setter
    def mobile_phone(self, value):
        self._mobile_phone = value

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey('team_colors.id'))
    color = db.relationship("TeamColor", back_populates="teams")
    manager_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', name='fk_team_manager_id_users', use_alter=True, deferrable=True, initially='DEFERRED'),
        nullable=True
    )
    users = db.relationship('User', backref='team', lazy='dynamic', foreign_keys=[User.team_id])
    manager = db.relationship('User', foreign_keys=[manager_id], backref=db.backref('managed_teams', lazy='dynamic'))
    notes = db.relationship('Note', backref='team', lazy='dynamic')

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.relationship('Permission', secondary='role_permissions', backref=db.backref('roles', lazy='dynamic'))

    def __repr__(self):
        return f'<Role {self.name}>'

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions.append(perm)

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions.remove(perm)

    def has_permission(self, perm):
        return perm in self.permissions

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('schedules', lazy='dynamic'))

class TimeOffRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('time_off_requests', lazy='dynamic'))

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    is_priority = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))

class TeamColor(db.Model):
    __tablename__ = 'team_colors'   
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hex_value = db.Column(db.String(7), unique=True, nullable=False)
    is_core = db.Column(db.Boolean, default=False)
    
    teams = db.relationship("Team", back_populates="color", uselist=False)

    @property
    def is_assigned(self):
        return self.teams is not None
