from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import date, datetime

class Stage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    weekly_data = db.relationship('WeeklyData', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    daily_data = db.relationship('DailyData', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    log_entries = db.relationship('LogEntry', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    def to_dict(self): return {'id': self.id, 'name': self.name, 'start_date': self.start_date.isoformat(), 'user_id': self.user_id}
    def __repr__(self): return f'<Stage {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    stages = db.relationship('Stage', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade="all, delete-orphan") # 新增
    countdown_events = db.relationship('CountdownEvent', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    settings = db.relationship('Setting', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    mottos = db.relationship('Motto', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    todos = db.relationship('Todo', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def __repr__(self): return f'<User {self.username}>'

class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    def to_dict(self): return {'key': self.key, 'value': self.value}

class WeeklyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week_num = db.Column(db.Integer, nullable=False)
    efficiency = db.Column(db.Float, nullable=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('year', 'week_num', 'stage_id', name='_stage_year_week_uc'),)
    def to_dict(self): return {'id': self.id, 'year': self.year, 'week_num': self.week_num, 'efficiency': self.efficiency, 'stage_id': self.stage_id}

class DailyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False)
    efficiency = db.Column(db.Float, nullable=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('log_date', 'stage_id', name='_stage_log_date_uc'),)
    def to_dict(self): return {'id': self.id, 'log_date': self.log_date.isoformat(), 'efficiency': self.efficiency, 'stage_id': self.stage_id}

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(50), nullable=True)
    task = db.Column(db.String(200), nullable=False)
    actual_duration = db.Column(db.Integer, nullable=True)
    legacy_category = db.Column(db.String(100), nullable=True) # 重命名后的旧字段
    mood = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'), nullable=True) # 新增
    @property
    def duration_formatted(self):
        if self.actual_duration is None: return ""
        h, m = divmod(self.actual_duration, 60)
        return f'{h}h {m}m' if h > 0 else f'{m}m'
    def to_dict(self):
        return {
            'id': self.id, 'log_date': self.log_date.isoformat(), 'time_slot': self.time_slot,
            'task': self.task, 'actual_duration': self.actual_duration, 'legacy_category': self.legacy_category,
            'subcategory_id': self.subcategory_id, 'mood': self.mood, 'notes': self.notes, 'stage_id': self.stage_id
        }

class CountdownEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    target_datetime_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    def __repr__(self): return f'<CountdownEvent {self.title}>'
    def to_dict(self): return {'id': self.id, 'title': self.title, 'target_datetime_utc': self.target_datetime_utc.isoformat()}

class Motto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    def __repr__(self): return f'<Motto {self.content[:20]}>'

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, default=2)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    def __repr__(self): return f'<Todo {self.content[:20]}>'

# 新增的分类模型
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subcategories = db.relationship('SubCategory', backref='category', lazy='dynamic', cascade="all, delete-orphan")
    def __repr__(self): return f'<Category {self.name}>'

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    log_entries = db.relationship('LogEntry', backref='subcategory', lazy='dynamic')
    def __repr__(self): return f'<SubCategory {self.name}>'