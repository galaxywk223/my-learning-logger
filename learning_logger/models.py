from . import db  # 从当前包的 __init__.py 中导入 db 实例
from werkzeug.security import generate_password_hash, check_password_hash  # <- 导入密码哈希工具
from flask_login import UserMixin  # <- 导入 UserMixin


class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    # 定义与用户相关的其他数据的关系
    # backref='user' 允许我们通过 LogEntry.user 访问关联的 User 对象
    # lazy='dynamic' 使得查询返回的是一个查询对象，而不是直接加载所有记录，性能更好
    log_entries = db.relationship('LogEntry', backref='user', lazy='dynamic')
    countdown_events = db.relationship('CountdownEvent', backref='user', lazy='dynamic')
    weekly_data = db.relationship('WeeklyData', backref='user', lazy='dynamic')
    daily_data = db.relationship('DailyData', backref='user', lazy='dynamic')
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
    # --- 新增 ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # --- 修改唯一性约束，现在是针对每个用户是唯一的 ---
    __table_args__ = (db.UniqueConstraint('year', 'week_num', 'user_id', name='_user_year_week_uc'),)
    def to_dict(self):
        """将 WeeklyData 对象转换为字典。"""
        return {
            'id': self.id,
            'year': self.year,
            'week_num': self.week_num,
            'efficiency': self.efficiency
        }


class DailyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, unique=True, nullable=False)
    efficiency = db.Column(db.String(100), nullable=True)
    # --- 新增 ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # --- 新增唯一性约束 ---
    __table_args__ = (db.UniqueConstraint('log_date', 'user_id', name='_user_log_date_uc'),)

    def to_dict(self):
        """将 DailyData 对象转换为字典。"""
        return {
            'id': self.id,
            'log_date': self.log_date,
            'efficiency': self.efficiency
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
    # --- 新增 ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
            'log_date': self.log_date,
            'time_slot': self.time_slot,
            'task': self.task,
            'actual_duration': self.actual_duration,
            'category': self.category,
            'mood': self.mood,
            'notes': self.notes
        }


class CountdownEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    # 我们将在数据库中以 UTC 标准时间存储，这是最佳实践
    target_datetime_utc = db.Column(db.DateTime(timezone=True), nullable=False)
    # --- 新增 ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<CountdownEvent {self.title}>'

    def to_dict(self):
        """将 CountdownEvent 对象转换为字典。"""
        return {
            'id': self.id,
            'title': self.title,
            'target_datetime_utc': self.target_datetime_utc
        }
