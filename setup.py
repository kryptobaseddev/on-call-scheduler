from app import create_app
from extensions import db
from models import User, TeamColor, Role, Permission
from werkzeug.security import generate_password_hash
from routes import seed_core_colors
from permissions import *

def seed_roles_and_permissions():
    app = create_app()
    with app.app_context():
        # Define permissions
        permissions = [
            # View permissions
            {'name': VIEW_DASHBOARD, 'description': 'View the dashboard'},
            {'name': VIEW_TEAM, 'description': 'View team members'},
            {'name': VIEW_ANALYTICS, 'description': 'View analytics'},
            # Manage permissions
            {'name': MANAGE_USERS, 'description': 'Manage user accounts'},
            {'name': MANAGE_TEAMS, 'description': 'Manage teams'},
            {'name': MANAGE_SCHEDULES, 'description': 'Manage schedules'},
            {'name': MANAGE_ROLES, 'description': 'Manage roles'},
            {'name': MANAGE_PERMISSIONS, 'description': 'Manage permissions'},
            {'name': MANAGE_NOTES, 'description': 'Manage notes'},
            {'name': MANAGE_COLORS, 'description': 'Manage colors'},
            # Request permissions
            {'name': REQUEST_TIME_OFF, 'description': 'Request time off'},
        ]

        # Create permissions
        for perm in permissions:
            permission = Permission.query.filter_by(name=perm['name']).first()
            if not permission:
                permission = Permission(name=perm['name'], description=perm['description'])
                db.session.add(permission)

        db.session.commit()

        # Define roles and their permissions
        roles = {
            'Admin': [VIEW_DASHBOARD, MANAGE_USERS, MANAGE_TEAMS, MANAGE_SCHEDULES, MANAGE_ROLES, MANAGE_PERMISSIONS, MANAGE_REPORTS, MANAGE_NOTES, MANAGE_COLORS, VIEW_ANALYTICS, VIEW_TEAM, REQUEST_TIME_OFF],
            'Manager': [VIEW_DASHBOARD, MANAGE_TEAMS, MANAGE_SCHEDULES, VIEW_TEAM, MANAGE_USERS, MANAGE_NOTES, VIEW_ANALYTICS, REQUEST_TIME_OFF],
            'User': [VIEW_DASHBOARD, REQUEST_TIME_OFF]
        }

        # Create roles and assign permissions
        for role_name, perms in roles.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name)
                db.session.add(role)
            for perm_name in perms:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission and not role.has_permission(permission):
                    role.add_permission(permission)

        db.session.commit()
        print("Roles and permissions seeded successfully.")


def create_admin_user():
    app = create_app()
    with app.app_context():
        admin_user = User.query.filter_by(username='admin').first()
        role = Role.query.filter_by(name='Admin').first()
        if admin_user:
            print("Admin user already exists.")
        else:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('adminpassword'),
                role_id=role,
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully.")

def seed_colors():
    app = create_app()
    with app.app_context():
        core_colors = [
            "#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#FF00FF",
            "#00FFFF", "#FFA500", "#800080", "#8B4513", "#808000",
            "#FF6347", "#4682B4", "#32CD32", "#FFD700", "#8A2BE2",
            "#5F9EA0", "#DC143C", "#7FFF00", "#FF69B4", "#B22222"
        ]
        existing_colors = [color.hex_value for color in TeamColor.query.filter(TeamColor.hex_value.in_(core_colors)).all()]
        if set(core_colors).issubset(set(existing_colors)):
            print("Core colors already seeded.")
        else:
            seed_core_colors()
            print("Core colors seeded successfully.")
            
def assign_default_role_to_users():
    app = create_app()
    with app.app_context():
        default_role = Role.query.filter_by(name='User').first()
        users_without_role = User.query.filter(User.role == None).all()
        for user in users_without_role:
            user.role = default_role
        db.session.commit()
        print("Default role assigned to existing users.")

if __name__ == '__main__':
    seed_roles_and_permissions()
    assign_default_role_to_users()
    create_admin_user()
    seed_colors()


