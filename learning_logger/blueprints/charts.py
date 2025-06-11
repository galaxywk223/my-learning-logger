from datetime import date, timedelta
from flask import Blueprint, render_template
from sqlalchemy import func
# --- MODIFIED: 导入登录管理工具 ---
from flask_login import login_required, current_user

from .. import db
# --- MODIFIED: 导入 Setting 模型用于查询用户设置 ---
from ..models import LogEntry, WeeklyData, DailyData, Setting
from ..helpers import get_custom_week_info
import json
import collections

charts_bp = Blueprint('charts', 'charts_bp', url_prefix='/charts')


def calculate_sma(data, window_size=3):
    """
    计算简单移动平均值 (SMA)。
    此版本能安全处理 None 和字符串形式的数字。
    """
    if not data:
        return []

    window = collections.deque(maxlen=window_size)
    sma_values = []

    for value in data:
        numeric_value = None
        if value is not None and value != '':
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                numeric_value = None

        window.append(numeric_value if numeric_value is not None else 0)

        # 只有当窗口已满时才计算
        # 并且只有当当前值是数字时才添加SMA值，否则为None
        if len(window) == window_size:
            sma = sum(val for val in window if val is not None) / len(window)
            if numeric_value is not None:
                sma_values.append(round(sma, 2))
            else:
                sma_values.append(None)
        else:
            # 在窗口未满时，不计算SMA
            sma_values.append(None)

    return sma_values


@charts_bp.route('/')
# --- MODIFIED: 保护路由 ---
@login_required
def chart_page():
    """
    为当前用户渲染主图表页面。
    """
    # --- MODIFIED: 查询当前用户的设置 ---
    start_date_setting = Setting.query.filter_by(user_id=current_user.id, key='week_start_date').first()
    if not start_date_setting:
        return render_template('chart.html', setup_needed=True)

    start_date_setting_dt = date.fromisoformat(start_date_setting.value)

    # --- MODIFIED: 所有查询都必须过滤 user_id ---
    all_logs = LogEntry.query.filter_by(user_id=current_user.id).order_by(LogEntry.log_date.asc()).all()
    if not all_logs:
        empty_kpis = {'total_hours': 0, 'total_days': 0, 'avg_daily_minutes': 0}
        return render_template('chart.html', kpis=empty_kpis, setup_needed=False)

    # --- 1. 计算核心绩效指标 (KPIs) (查询已过滤) ---
    total_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).filter(LogEntry.user_id == current_user.id).scalar() or 0
    total_hours = round(total_duration_minutes / 60, 1)
    total_days_with_logs = db.session.query(func.count(func.distinct(LogEntry.log_date))).filter(LogEntry.user_id == current_user.id).scalar() or 0
    avg_daily_minutes = round(total_duration_minutes / total_days_with_logs, 1) if total_days_with_logs > 0 else 0
    kpis = {'total_hours': total_hours, 'total_days': total_days_with_logs, 'avg_daily_minutes': avg_daily_minutes}

    # --- 2. 准备周视图数据 (查询已过滤) ---
    weekly_efficiencies_map = {(w.year, w.week_num): w.efficiency for w in WeeklyData.query.filter_by(user_id=current_user.id).all()}
    weekly_data_agg = {}
    # all_logs 已经按用户过滤，这里无需再过滤
    for log in all_logs:
        year, week_num = get_custom_week_info(log.log_date, start_date_setting_dt)
        week_key = (year, week_num)
        weekly_data_agg.setdefault(week_key, {'duration': 0})['duration'] += log.actual_duration or 0

    sorted_weeks = sorted(weekly_data_agg.keys(), key=lambda x: (x[0], x[1]))

    weekly_durations_actual = [round(weekly_data_agg[w]['duration'] / 60, 2) for w in sorted_weeks]
    weekly_efficiencies_actual = [weekly_efficiencies_map.get(w) for w in sorted_weeks]

    weekly_duration_data = {
        'labels': [f"{w[0]}-W{w[1]:02d}" for w in sorted_weeks],
        'actuals': weekly_durations_actual,
        'trends': calculate_sma(weekly_durations_actual)
    }
    weekly_efficiency_data = {
        'labels': [f"{w[0]}-W{w[1]:02d}" for w in sorted_weeks],
        'actuals': weekly_efficiencies_actual,
        'trends': calculate_sma(weekly_efficiencies_actual)
    }

    # --- 3. 准备日视图数据 (带缺失日期填充) (查询已过滤) ---
    first_log_date = all_logs[0].log_date
    today = date.today()
    date_range = [first_log_date + timedelta(days=x) for x in range((today - first_log_date).days + 1)]

    daily_duration_map = {d[0]: d[1] for d in
                          db.session.query(LogEntry.log_date, func.sum(LogEntry.actual_duration))
                          .filter(LogEntry.user_id == current_user.id) # 过滤
                          .group_by(LogEntry.log_date).all()}
    daily_efficiency_map = {d.log_date: d.efficiency for d in DailyData.query.filter_by(user_id=current_user.id).all()}

    daily_durations_actual = [round(daily_duration_map.get(day, 0) / 60, 2) for day in date_range]
    daily_efficiencies_actual = [daily_efficiency_map.get(day) for day in date_range]

    daily_duration_data = {
        'labels': [d.isoformat() for d in date_range],
        'actuals': daily_durations_actual,
        'trends': calculate_sma(daily_durations_actual, window_size=7)
    }
    daily_efficiency_data = {
        'labels': [d.isoformat() for d in date_range],
        'actuals': daily_efficiencies_actual,
        'trends': calculate_sma(daily_efficiencies_actual, window_size=7)
    }

    return render_template(
        'chart.html',
        kpis=kpis,
        weekly_duration_data=weekly_duration_data,
        weekly_efficiency_data=weekly_efficiency_data,
        daily_duration_data=daily_duration_data,
        daily_efficiency_data=daily_efficiency_data,
        setup_needed=False
    )
