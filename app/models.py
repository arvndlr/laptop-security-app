# models.py
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    laptops = db.relationship('Laptop', backref='owner', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Laptop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    serial_number = db.Column(db.String(120), index=True, unique=True)
    is_stolen = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    readings = db.relationship('SensorReading', backref='laptop', lazy='dynamic', cascade="all, delete-orphan")
    
    # ADD THESE COLUMNS
    ibeacon_uuid = db.Column(db.String(36))
    ibeacon_major = db.Column(db.Integer)
    ibeacon_minor = db.Column(db.Integer)

    def __repr__(self):
        return f'<Laptop {self.name} - {self.serial_number}>'

class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    ibeacon_uuid = db.Column(db.String(36))
    ibeacon_major = db.Column(db.Integer)
    ibeacon_minor = db.Column(db.Integer)
    ibeacon_rssi = db.Column(db.Integer)
    
    # Columns for the four ultrasonic sensors
    ultrasonic_distance_1_cm = db.Column(db.Float)
    ultrasonic_distance_2_cm = db.Column(db.Float)
    ultrasonic_distance_3_cm = db.Column(db.Float)
    ultrasonic_distance_4_cm = db.Column(db.Float)
    
    # NEW: Flag to indicate an intrusion from the ultrasonic sensor
    ultrasonic_intrusion_detected = db.Column(db.Boolean, default=False)
    
    laptop_id = db.Column(db.Integer, db.ForeignKey('laptop.id'))

    def __repr__(self):
        return f'<SensorReading {self.timestamp} from Laptop {self.laptop_id}>'