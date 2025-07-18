# learning_logger/models/feature_models.py (REVISED)

from .. import db
from datetime import date, datetime

class CountdownEvent(db.Model):
    __tablename__ = 'countdown_event'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    target_datetime_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at_utc = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<CountdownEvent {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'target_datetime_utc': self.target_datetime_utc.isoformat(),
            'created_at_utc': self.created_at_utc.isoformat() if self.created_at_utc else None
        }


class Motto(db.Model):
    __tablename__ = 'motto'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Motto {self.content[:20]}>'


class Todo(db.Model):
    __tablename__ = 'todo'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, default=2)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Todo {self.content[:20]}>'


class MilestoneCategory(db.Model):
    __tablename__ = 'milestone_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # --- REVISED: Added cascade option ---
    milestones = db.relationship('Milestone', backref='category', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<MilestoneCategory {self.name}>'


class Milestone(db.Model):
    __tablename__ = 'milestone'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('milestone_category.id'), nullable=True)

    # --- REVISED: Added cascade option ---
    attachments = db.relationship('MilestoneAttachment', backref='milestone', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Milestone {self.title}>'


class MilestoneAttachment(db.Model):
    __tablename__ = 'milestone_attachment'
    id = db.Column(db.Integer, primary_key=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestone.id'), nullable=False)
    file_path = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MilestoneAttachment {self.original_filename}>'


class DailyPlanItem(db.Model):
    __tablename__ = 'daily_plan_item'
    id = db.Column(db.Integer, primary_key=True)
    plan_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    content = db.Column(db.String(500), nullable=False)
    time_slot = db.Column(db.String(20), nullable=True)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DailyPlanItem {self.content[:30]}>'