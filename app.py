import logging
import os
from flask import Flask, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import traceback
from extensions import db, migrate, jwt, login_manager
from routes import main, auth, admin, manager, user, seed_core_colors
from dotenv import load_dotenv

# Configure logging at the top
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    if app.config['SQLALCHEMY_DATABASE_URI'] is None:
        raise ValueError("No DATABASE_URL set for Flask application")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'fallback-jwt-secret-key')
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['DEBUG'] = True

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(manager, url_prefix='/manager')
    app.register_blueprint(user, url_prefix='/user')

    # Initialize LoginManager
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        logger.debug(f"load_user called with user_id={user_id}, returning user={user}")
        return user

    # Seed core colors
    with app.app_context():
        db.create_all()  # Ensure all tables are created
        seed_core_colors()  # Seed or update core colors

    # Global error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        db.session.rollback()
        logger.exception("Unhandled exception: %s", str(e))
        return render_template('500.html'), 500

    # Database connection test
    @app.before_request
    def test_database_connection():
        try:
            db.session.execute(text('SELECT 1'))
            logger.debug("Database connection test successful")
        except OperationalError as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return "Database connection error", 500

    @app.after_request
    def after_request(response):
        if response.status_code == 500:
            logger.error(f"500 error occurred: {traceback.format_exc()}")
        return response

    return app

app = create_app()

if __name__ == '__main__':
    app.run()
