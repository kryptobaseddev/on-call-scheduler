import csv
import os
import shutil
from datetime import datetime
from app import create_app
from extensions import db
from models import User, Role
from werkzeug.security import generate_password_hash

def add_users_from_csv(csv_file_path):
    app = create_app()
    with app.app_context():
        # Ensure roles exist
        roles = {role.name: role for role in Role.query.all()}
        required_roles = ['User', 'Manager', 'Admin']
        for role_name in required_roles:
            if role_name not in roles:
                print(f"Role '{role_name}' not found. Please ensure roles are seeded before adding users.")
                return

        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    username = row['username']
                    email = row['email']
                    password = row['password']
                    role_name = row['role']
                    first_name = row.get('first_name', None)
                    last_name = row.get('last_name', None)
                    mobile_phone = row.get('mobile_phone', None)
                    work_phone = row.get('work_phone', None)
                    timezone = row.get('timezone', 'UTC')
                    is_active = row.get('is_active', 'True').lower() == 'true'

                    # Validate role
                    role = roles.get(role_name)
                    if not role:
                        print(f"Invalid role '{role_name}' for user '{username}'. Skipping user.")
                        continue

                    # Check if the user already exists
                    existing_user = User.query.filter_by(username=username).first()
                    if existing_user:
                        print(f"User '{username}' already exists. Skipping user.")
                        continue

                    # Create new user
                    new_user = User(
                        username=username,
                        email=email,
                        password_hash=generate_password_hash(password),
                        role=role,
                        first_name=first_name,
                        last_name=last_name,
                        mobile_phone=mobile_phone,
                        work_phone=work_phone,
                        timezone=timezone,
                        is_active=is_active
                    )
                    db.session.add(new_user)
                    print(f"Added user '{username}' with role '{role_name}'.")
                db.session.commit()
                print("All users added successfully.")

            # After successful import, rename and move the CSV file
            timestamp = datetime.now().strftime('%Y%m%d_%H-%M-%S')
            filename = os.path.basename(csv_file_path)
            new_filename = f"imported_users_{timestamp}.csv"
            complete_dir = os.path.join(os.path.dirname(csv_file_path), 'complete')

            # Ensure the 'complete' directory exists
            if not os.path.exists(complete_dir):
                os.makedirs(complete_dir)

            # Construct full paths
            new_file_path = os.path.join(complete_dir, new_filename)

            # Move and rename the file
            shutil.move(csv_file_path, new_file_path)
            print(f"CSV file has been moved to '{new_file_path}'.")

        except FileNotFoundError:
            print(f"CSV file '{csv_file_path}' not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()

if __name__ == '__main__':
    csv_file_path = os.path.join('user_import', 'users.csv')  # Path to your CSV file
    add_users_from_csv(csv_file_path)
