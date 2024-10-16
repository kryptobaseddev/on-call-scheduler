from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from urllib.parse import urlparse

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'fallback-jwt-secret-key')
    app.config['JWT_TOKEN_LOCATION'] = ['headers']

    # Parse the DATABASE_URL
    url = urlparse(app.config['SQLALCHEMY_DATABASE_URI'])

    # Create the SQLAlchemy engine with connection pooling
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )

    # Create a scoped session
    db_session = scoped_session(sessionmaker(bind=engine))

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        from models import User, Team, Schedule, TimeOffRequest, Note
        from routes import main, auth, admin, manager, user
        app.register_blueprint(main)
        app.register_blueprint(auth)
        app.register_blueprint(admin)
        app.register_blueprint(manager)  # Make sure this line is here
        app.register_blueprint(user)

    # Add db_session to app.extensions
    app.extensions['sqlalchemy'] = {
        'db_session': db_session
    }

    return app
