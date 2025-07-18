# 文件路径: learning_logger/models/user_models.py
from .. import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    stages = db.relationship('Stage', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    milestone_categories = db.relationship('MilestoneCategory', backref='user', lazy='dynamic',
                                           cascade="all, delete-orphan")
    milestones = db.relationship('Milestone', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    countdown_events = db.relationship('CountdownEvent', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    settings = db.relationship('Setting', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    mottos = db.relationship('Motto', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    todos = db.relationship('Todo', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    daily_plans = db.relationship('DailyPlanItem', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Setting(db.Model):
    __tablename__ = 'setting'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)

    def to_dict(self):
        return {'key': self.key, 'value': self.value}
