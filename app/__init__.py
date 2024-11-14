from flask import Flask
from .extensions import db, login_manager
from .config import Config
from .routes import main as main_blueprint

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(main_blueprint)

    with app.app_context():
        db.create_all()  # Создание всех таблиц

    return app
