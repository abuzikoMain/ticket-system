import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tickets.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CELERY_BROKER_URL = 'redis://localhost:6379/0'  # URL вашего брокера
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # URL для хранения 
    SECRET_KEY = os.urandom(24)
