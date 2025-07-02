from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import date  # 确保导入 date


# ============================================================================
# 1. 新增 Stage 模型
# ============================================================================
class Stage(db.Model):
    """阶段模型，代表一个独立的学习时期，如“大三上学期”"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # 定义与阶段相关的其他数据的关系 (级联删除)
    weekly_data = db.relationship('WeeklyData', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    daily_data = db.relationship('DailyData', backref='stage', lazy='dynamic', cascade="all, delete-orphan")
    log_entries = db.relationship('LogEntry', backref='stage', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        """将 Stage 对象转换为字典。"""
        return {
            'id': self.id,
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Stage {self.name}>'


class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    # ============================================================================
    # 2. 修改关联关系：User 现在关联到 Stage
    # ============================================================================
    stages = db.relationship('Stage', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    # 用户专有的数据保持不变
    countdown_events = db.relationship('CountdownEvent', backref='user', lazy='dynamic')
    settings = db.relationship('Setting', backref='user', lazy='dynamic')

    def set_password(self, password):
        """设置密码，将明文密码哈希后存储"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """检查密码，对比明文密码和哈希值是否匹配"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)

    def to_dict(self):
        """将 Setting 对象转换为字典。"""
        return {
            'key': self.key,
            'value': self.value
        }


class WeeklyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week_num = db.Column(db.Integer, nullable=False)
    efficiency = db.Column(db.String(100), nullable=True)

    # ============================================================================
    # 3. 将 user_id 替换为 stage_id
    # ============================================================================
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)

    # --- 修改唯一性约束，现在是针对每个阶段是唯一的 ---
    __table_args__ = (db.UniqueConstraint('year', 'week_num', 'stage_id', name='_stage_year_week_uc'),)

    def to_dict(self):
        """将 WeeklyData 对象转换为字典。"""
        return {
            'id': self.id,
            'year': self.year,
            'week_num': self.week_num,
            'efficiency': self.efficiency,
            'stage_id': self.stage_id  # 为数据迁移添加 stage_id
        }


class DailyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # --- 修正：移除了列级别的 unique=True，因为它过于严格，应由下方的表级约束来保证唯一性 ---
    log_date = db.Column(db.Date, nullable=False)
    efficiency = db.Column(db.String(100), nullable=True)

    # ============================================================================
    # 4. 将 user_id 替换为 stage_id
    # ============================================================================
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)

    # --- 修改唯一性约束，现在是针对每个阶段是唯一的 ---
    __table_args__ = (db.UniqueConstraint('log_date', 'stage_id', name='_stage_log_date_uc'),)

    def to_dict(self):
        """将 DailyData 对象转换为字典。"""
        return {
            'id': self.id,
            'log_date': self.log_date.isoformat(),  # 转换为 ISO 格式字符串
            'efficiency': self.efficiency,
            'stage_id': self.stage_id
        }


class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(50), nullable=True)
    task = db.Column(db.String(200), nullable=False)
    actual_duration = db.Column(db.Integer, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    mood = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # ============================================================================
    # 5. 将 user_id 替换为 stage_id
    # ============================================================================
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)

    @property
    def duration_formatted(self):
        if self.actual_duration is None:
            return ""
        h, m = divmod(self.actual_duration, 60)
        if h > 0:
            return f'{h}h {m}m'
        else:
            return f'{m}m'

    def to_dict(self):
        """将 LogEntry 对象转换为字典。"""
        return {
            'id': self.id,
            'log_date': self.log_date.isoformat(),  # 转换为 ISO 格式字符串
            'time_slot': self.time_slot,
            'task': self.task,
            'actual_duration': self.actual_duration,
            'category': self.category,
            'mood': self.mood,
            'notes': self.notes,
            'stage_id': self.stage_id
        }


class CountdownEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    target_datetime_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    # 倒计时事件是用户级别的，与阶段无关，保持不变
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<CountdownEvent {self.title}>'

    def to_dict(self):
        """将 CountdownEvent 对象转换为字典。"""
        return {
            'id': self.id,
            'title': self.title,
            'target_datetime_utc': self.target_datetime_utc.isoformat()
        }