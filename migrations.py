
from flask_migrate import Migrate, init, migrate, upgrade
from app import create_app, db

def setup_migrations():
    app = create_app()
    migrate = Migrate(app, db)
    
    with app.app_context():
        init()
        migrate(message="Add mobile_phone to User model")
        upgrade()

if __name__ == "__main__":
    setup_migrations()
    print("Migration completed successfully.")
