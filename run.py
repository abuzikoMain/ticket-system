from config import Config
from flask import Flask
from models import db, User
from flask_login import LoginManager
import os

if __name__ == '__main__':

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['UPLOAD_FOLDER'] = 'uploads'  # Папка для загрузки файлов
    # celery = make_celery(app)
    db.init_app(app)

    # Создание папки для загрузки, если она не существует
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()  # Создание всех таблиц
    app.run(debug=True)
