import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'justine123'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://justine:justine123@localhost/laptop_security_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False