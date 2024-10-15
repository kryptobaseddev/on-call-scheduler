import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY") or "jwt-secret-key"
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = True
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True

    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    with app.app_context():
        from models import User, Team, Schedule, TimeOffRequest, Note
        db.create_all()

        from routes import main, auth, admin, manager, user
        app.register_blueprint(main)
        app.register_blueprint(auth)
        app.register_blueprint(admin)
        app.register_blueprint(manager)
        app.register_blueprint(user)

    return app
