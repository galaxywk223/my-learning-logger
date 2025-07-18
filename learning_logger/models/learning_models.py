# my-learning-logger/learning_logger/models/learning_models.py (REVISED)

from .. import db
from datetime import date


class Stage(db.Model):
    __tablename__ = 'stage'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    weekly_data = db.relationship('WeeklyData', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    daily_data = db.relationship('DailyData', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    log_entries = db.relationship('LogEntry', backref='stage', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'start_date': self.start_date.isoformat(), 'user_id': self.user_id}

    def __repr__(self):
        return f'<Stage {self.name}>'


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    subcategories = db.relationship('SubCategory', backref='category', lazy='dynamic', cascade="all, delete-orphan")

    # --- FIX: Added the missing to_dict() method ---
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'user_id': self.user_id}

    # --- END FIX ---

    def __repr__(self):
        return f'<Category {self.name}>'


class SubCategory(db.Model):
    __tablename__ = 'sub_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    log_entries = db.relationship('LogEntry', backref='subcategory', lazy='dynamic')

    # --- ADDED: Also adding to_dict() here for consistency and future use ---
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'category_id': self.category_id}

    # --- END ADDITION ---

    def __repr__(self):
        return f'<SubCategory {self.name}>'


class LogEntry(db.Model):
    __tablename__ = 'log_entry'
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(50), nullable=True)
    task = db.Column(db.String(200), nullable=False)
    actual_duration = db.Column(db.Integer, nullable=True)
    legacy_category = db.Column(db.String(100), nullable=True)
    mood = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'), nullable=True)

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


class WeeklyData(db.Model):
    __tablename__ = 'weekly_data'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week_num = db.Column(db.Integer, nullable=False)
    efficiency = db.Column(db.Float, nullable=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('year', 'week_num', 'stage_id', name='_stage_year_week_uc'),)

    def to_dict(self):
        return {'id': self.id, 'year': self.year, 'week_num': self.week_num, 'efficiency': self.efficiency,
                'stage_id': self.stage_id}


class DailyData(db.Model):
    __tablename__ = 'daily_data'
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False)
    efficiency = db.Column(db.Float, nullable=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('log_date', 'stage_id', name='_stage_log_date_uc'),)

    def to_dict(self):
        return {'id': self.id, 'log_date': self.log_date.isoformat(), 'efficiency': self.efficiency,
                'stage_id': self.stage_id}