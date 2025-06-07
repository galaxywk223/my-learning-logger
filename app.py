import os
import csv
import io
import re
from datetime import date, datetime, timedelta
from itertools import groupby

from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy

# --- Matplotlib 设置 ---
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# --- 基础设置 ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-for-flash-messages'

# --- [核心修改] 兼容线上部署的数据库配置 ---
# 检查是否存在环境变量DATABASE_URL (Render平台会自动注入这个变量)
# 如果存在，就使用生产环境的PostgreSQL数据库
# 如果不存在，就回退到本地的SQLite数据库，这样不影响您在本地电脑上开发测试
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render提供的URL是postgres://...开头的，SQLAlchemy需要postgresql://...
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://", 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'learning_logs.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- 数据模型 (无变化) ---
class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)


class WeeklyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week_num = db.Column(db.Integer, nullable=False)
    efficiency = db.Column(db.String(100), nullable=True)
    __table_args__ = (db.UniqueConstraint('year', 'week_num', name='_year_week_uc'),)


class DailyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, unique=True, nullable=False)
    efficiency = db.Column(db.String(100), nullable=True)


class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(50), nullable=True)
    task = db.Column(db.String(200), nullable=False)
    actual_duration = db.Column(db.Integer, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    mood = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # app.py, inside the LogEntry class
    @property
    def duration_formatted(self):
        # 在计算前先检查值是否存在
        if self.actual_duration is None:
            return "N/A"  # 或者返回空字符串 '' 或 '0h 0m'，根据你的需要

        # 只有在值存在时才进行计算
        h, m = divmod(self.actual_duration, 60)
        if h > 0:
            return f'{h}h {m}m'
        else:
            return f'{m}m'


# --- 辅助函数 (无变化) ---
def get_setting(key, default=None):
    setting = Setting.query.get(key)
    return setting.value if setting else default


def get_custom_week_info(log_date, start_date):
    if not isinstance(log_date, date): log_date = date.fromisoformat(log_date)
    days_diff = (log_date - start_date).days
    if days_diff < 0: return start_date.year, 1
    return log_date.year, (days_diff // 7) + 1


def parse_csv_duration(duration_str):
    if not isinstance(duration_str, str): return 0
    duration_str = duration_str.strip().lower()
    try:
        if 'h' in duration_str: return int(float(duration_str.replace('h', '')) * 60)
        if 'min' in duration_str: return int(float(duration_str.replace('min', '')))
        if '上课' in duration_str: return 90
        return int(float(duration_str) * 60)
    except (ValueError, TypeError):
        return 0


def parse_csv_date(date_str):
    if not isinstance(date_str, str): return None
    try:
        parts = date_str.replace('月', '-').replace('日', '').split('-')
        return date(datetime.now().year, int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, TypeError):
        return None


def parse_efficiency_to_numeric(eff_str):
    if not isinstance(eff_str, str) or not eff_str.strip():
        return 0
    eff_str = eff_str.strip()
    match = re.match(r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)', eff_str)
    if match:
        num, den = float(match.group(1)), float(match.group(2))
        return (num / den) * 5 if den != 0 else 0
    match = re.match(r'(\d+\.?\d*)\s*%', eff_str)
    if match:
        return (float(match.group(1)) / 100) * 5
    match = re.match(r'(\d+\.?\d*)', eff_str)
    if match:
        return float(match.group(1))
    mapping = {"高效": 5, "良好": 4, "不错": 4, "一般": 3, "还行": 3, "及格": 3, "较差": 2, "差": 2, "很差": 1,
               "低效": 1}
    return float(mapping.get(eff_str, 0))


def moving_average(data, window_size=7):
    if len(data) < window_size:
        return np.array([])
    return np.convolve(data, np.ones(window_size), 'valid') / window_size


# --- 路由 ---
@app.route('/')
def index():
    sort_order = request.args.get('sort', 'desc')
    is_reverse = (sort_order == 'desc')

    start_date_str = get_setting('week_start_date')
    if not start_date_str:
        return render_template('index.html', setup_needed=True)
    start_date = date.fromisoformat(start_date_str)

    logs = LogEntry.query.order_by(LogEntry.log_date.asc(), LogEntry.id.asc()).all()

    weekly_efficiencies = {(w.year, w.week_num): w.efficiency for w in WeeklyData.query.all()}
    daily_efficiencies = {d.log_date: d.efficiency for d in DailyData.query.all()}

    def group_key(log):
        return get_custom_week_info(log.log_date, start_date)

    logs_by_week = groupby(logs, key=group_key)
    structured_logs = []
    for (year, week_num), week_logs_iter in logs_by_week:
        week_logs = list(week_logs_iter)
        logs_by_day = groupby(week_logs, key=lambda log: log.log_date)
        days_in_week = []
        for day_date, day_logs_iter in logs_by_day:
            days_in_week.append({
                'date': day_date,
                'efficiency': daily_efficiencies.get(day_date, None),
                'logs': list(day_logs_iter)
            })
        structured_logs.append({
            'year': year, 'week_num': week_num,
            'efficiency': weekly_efficiencies.get((year, week_num), None),
            'days': sorted(days_in_week, key=lambda d: d['date'], reverse=is_reverse)
        })

    sorted_weeks = sorted(structured_logs, key=lambda w: (w['year'], w['week_num']), reverse=is_reverse)

    for week_idx, week in enumerate(sorted_weeks):
        week['week_index'] = week_idx
        for day_idx, day in enumerate(week['days']):
            day['day_index'] = day_idx

    return render_template('index.html',
                           structured_logs=sorted_weeks,
                           current_sort=sort_order)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        start_date_str = request.form.get('week_start_date')
        if start_date_str:
            setting = Setting.query.get('week_start_date')
            if setting:
                setting.value = start_date_str
            else:
                db.session.add(Setting(key='week_start_date', value=start_date_str))
            db.session.commit()
            flash('起始周设置已更新！', 'success')
            return redirect(url_for('index'))
    return render_template('settings.html', current_start_date=get_setting('week_start_date', ''))


@app.route('/import', methods=['GET', 'POST'])
def import_page():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash('请选择一个有效的.csv文件。', 'error')
            return redirect(url_for('import_page'))

        start_date_str = get_setting('week_start_date')
        if not start_date_str:
            flash('请先设置周起始日期，才能导入数据。', 'error')
            return redirect(url_for('settings'))
        start_date = date.fromisoformat(start_date_str)

        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8-SIG"), newline=None)
            csv_reader = csv.DictReader(stream)
            logs_to_add = []
            daily_efficiencies_to_update = {}
            weekly_efficiencies_to_update = {}
            for row in csv_reader:
                log_date = parse_csv_date(row.get('日期'))
                if not log_date: continue
                duration = parse_csv_duration(row.get('总时长'))
                task = row.get('任务')
                if duration and task:
                    mood_str = row.get('心情')
                    mood = int(mood_str) if mood_str and mood_str.isdigit() else 0
                    logs_to_add.append(LogEntry(
                        log_date=log_date, time_slot=row.get('时间段', ''), task=task,
                        actual_duration=duration, mood=mood
                    ))
                daily_efficiency = row.get('今日效率')
                if daily_efficiency and log_date not in daily_efficiencies_to_update:
                    daily_efficiencies_to_update[log_date] = daily_efficiency
                weekly_efficiency = row.get('本周效率')
                if weekly_efficiency:
                    year, week_num = get_custom_week_info(log_date, start_date)
                    if (year, week_num) not in weekly_efficiencies_to_update:
                        weekly_efficiencies_to_update[(year, week_num)] = weekly_efficiency
            for log_date, eff in daily_efficiencies_to_update.items():
                if not eff.strip(): continue
                daily_data = DailyData.query.filter_by(log_date=log_date).first()
                if daily_data:
                    daily_data.efficiency = eff
                else:
                    db.session.add(DailyData(log_date=log_date, efficiency=eff))
            for (year, week_num), eff in weekly_efficiencies_to_update.items():
                if not eff.strip(): continue
                weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num).first()
                if weekly_data:
                    weekly_data.efficiency = eff
                else:
                    db.session.add(WeeklyData(year=year, week_num=week_num, efficiency=eff))
            if logs_to_add: db.session.add_all(logs_to_add)
            db.session.commit()
            flash(
                f'导入成功！新增/更新了 {len(logs_to_add)} 条日志记录，{len(daily_efficiencies_to_update)} 天的日效率，{len(weekly_efficiencies_to_update)} 周的周效率。',
                'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'导入过程中发生严重错误: {e}', 'error')
            return redirect(url_for('import_page'))

    return render_template('import.html')


@app.route('/edit_week/<int:year>/<int:week_num>', methods=['GET', 'POST'])
def edit_week(year, week_num):
    weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num).first()
    if request.method == 'POST':
        efficiency = request.form['efficiency']
        if weekly_data:
            weekly_data.efficiency = efficiency
        else:
            db.session.add(WeeklyData(year=year, week_num=week_num, efficiency=efficiency))
        db.session.commit()
        flash(f'第 {week_num} 周效率已更新！', 'success')
        return redirect(url_for('index'))
    return render_template('edit_week.html', year=year, week_num=week_num, weekly_data=weekly_data)


@app.route('/edit_day/<iso_date>', methods=['GET', 'POST'])
def edit_day(iso_date):
    log_date = date.fromisoformat(iso_date)
    daily_data = DailyData.query.filter_by(log_date=log_date).first()
    if request.method == 'POST':
        efficiency = request.form['efficiency']
        if efficiency and efficiency.strip():  # 只有在用户输入了效率时才检查
            logs_for_day = LogEntry.query.filter_by(log_date=log_date).all()
            for log in logs_for_day:
                if log.actual_duration is None or log.mood is None:
                    flash(f"无法保存效率：记录 “{log.task}” 缺少时长或心情评分。", 'error')
                    # 将已有数据传回模板，避免用户重新输入
                    if not daily_data:
                        daily_data = DailyData(log_date=log_date)
                    daily_data.efficiency = efficiency  # 把用户刚输入的值传回去
                    return render_template('edit_day.html', log_date=log_date, daily_data=daily_data)
        if daily_data:
            daily_data.efficiency = efficiency
        else:
            db.session.add(DailyData(log_date=log_date, efficiency=efficiency))
        db.session.commit()
        flash(f'{log_date.strftime("%Y-%m-%d")} 的效率已更新！', 'success')
        return redirect(url_for('index'))
    return render_template('edit_day.html', log_date=log_date, daily_data=daily_data)


@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        duration_str = request.form.get('actual_duration')
        mood_str = request.form.get('mood')

        # 安全地处理可能为空或无效的数字输入
        try:
            # 如果 duration_str 是非空字符串，则尝试转换为整数，否则为 None
            final_duration = int(duration_str) if duration_str else None
        except ValueError:
            # 如果用户输入了无效内容（比如文字），则安全地设置为 None
            final_duration = None

        try:
            # 对 mood 执行相同的安全处理
            final_mood = int(mood_str) if mood_str else None
        except ValueError:
            final_mood = None

        new_log = LogEntry(
            log_date=date.fromisoformat(request.form['log_date']),
            time_slot=request.form['time_slot'],
            task=request.form['task'],
            actual_duration=final_duration,  # 使用安全处理后的值
            category=request.form['category'],
            mood=final_mood,  # 使用安全处理后的值
            notes=request.form['notes']
        )
        db.session.add(new_log)
        db.session.commit()
        flash('新纪录添加成功！', 'success')
        return redirect(url_for('index'))
    return render_template('add.html', default_date=date.today())


@app.route('/edit/<int:log_id>', methods=['GET', 'POST'])
def edit(log_id):
    # 根据 ID 获取要编辑的记录，如果找不到则返回 404 错误
    log = LogEntry.query.get_or_404(log_id)

    # 如果是表单提交 (POST 请求)
    if request.method == 'POST':
        log.log_date = date.fromisoformat(request.form.get('log_date'))
        log.time_slot = request.form.get('time_slot')
        log.task = request.form.get('task')
        log.category = request.form.get('category')
        log.notes = request.form.get('notes')

        # 安全地处理 actual_duration，允许其为 None
        try:
            duration_str = request.form.get('actual_duration')
            # 如果 duration_str 有内容，则转换为整数；否则，设置为 None
            log.actual_duration = int(duration_str) if duration_str else None
        except (ValueError, TypeError):
            # 如果用户输入了无效内容（比如文字），也将其安全地设置为 None
            log.actual_duration = None

        # 安全地处理 mood，允许其为 None
        try:
            mood_str = request.form.get('mood')
            # 如果 mood_str 有内容，则转换为整数；否则，设置为 None
            log.mood = int(mood_str) if mood_str else None
        except (ValueError, TypeError):
            # 如果用户输入了无效内容，也设置为 None
            log.mood = None

        # 提交会话，将更新保存到数据库
        db.session.commit()

        # 向用户显示成功提示
        flash('记录更新成功！', 'success')

        # 重定向到主页
        return redirect(url_for('index'))

    # 如果是 GET 请求，则显示带有当前记录数据的编辑页面
    return render_template('edit.html', log=log)


@app.route('/delete/<int:log_id>', methods=['POST'])
def delete(log_id):
    log = LogEntry.query.get_or_404(log_id)
    db.session.delete(log);
    db.session.commit()
    flash('记录已删除。', 'info')
    return redirect(url_for('index'))


@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    try:
        db.session.query(LogEntry).delete();
        db.session.query(DailyData).delete();
        db.session.query(WeeklyData).delete()
        db.session.commit()
        flash('所有学习记录和效率数据已被成功清空！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'清空数据时发生错误: {e}', 'error')
    return redirect(url_for('index'))


@app.route('/chart')
def chart_page():
    start_date_str = get_setting('week_start_date')
    if not start_date_str:
        flash('请先在设置页面指定一个起始日期，才能生成图表。', 'warning')
        return redirect(url_for('settings'))
    return render_template('chart.html')


@app.route('/efficiency_chart.png')
def generate_chart():
    start_date_str = get_setting('week_start_date')
    if not start_date_str:
        return "Error: Start date not set.", 400

    start_date = date.fromisoformat(start_date_str)
    end_date = date.today()
    if start_date > end_date: end_date = start_date

    all_daily_data = DailyData.query.filter(DailyData.log_date >= start_date).all()
    efficiency_map = {d.log_date: parse_efficiency_to_numeric(d.efficiency) for d in all_daily_data}

    date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    efficiencies = np.array([efficiency_map.get(d, 0) for d in date_range])

    # --- 开始绘图 ---
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(15, 7))
    fig.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    ax.bar(date_range, efficiencies, color='#EAECEE', width=0.7, zorder=2, label='每日效率值')

    window = 7
    if len(efficiencies) >= window:
        ma_values = moving_average(efficiencies, window)
        ma_dates = date_range[window - 1:]
        ax.plot(ma_dates, ma_values, color='#3498DB', linewidth=2.5, zorder=3, label=f'{window}日移动平均趋势')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#DDDDDD')
    ax.spines['bottom'].set_color('#DDDDDD')
    ax.tick_params(colors='#555555', which='both')
    ax.yaxis.grid(True, which='major', linestyle='--', color='#E5E7E9', zorder=0)
    ax.set_axisbelow(True)

    ax.set_title('每日效率趋势图', fontsize=18, fontweight='bold', color='#333333', pad=20)
    ax.set_ylabel('效率评分 (5分制)', fontsize=12, color='#555555')
    ax.set_xlabel('日期', fontsize=12, color='#555555')
    ax.set_ylim(0, 5.5)
    ax.legend(frameon=False, loc='upper left', fontsize=11)

    locator = mdates.AutoDateLocator(minticks=5, maxticks=12)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    plt.tight_layout(pad=1.5)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)

    return send_file(buf, mimetype='image/png')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # 在本地运行时，监听所有网络接口，方便局域网测试
    app.run(host='0.0.0.0', port=5000, debug=True)
