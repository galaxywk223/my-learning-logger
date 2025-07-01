# learning_logger/services/chart_service.py

import collections
from datetime import date, timedelta
from sqlalchemy import func
from .. import db
from ..models import LogEntry, WeeklyData, DailyData, Setting
from ..helpers import get_custom_week_info


def _calculate_sma(data, window_size=3):
    """
    计算简单移动平均值 (SMA)。
    此为内部辅助函数，不对外暴露。
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

        # 仅将有效数字加入窗口用于计算，但窗口本身长度仍增加
        window.append(numeric_value)

        # 只有当窗口已满时才开始计算
        if len(window) == window_size:
            valid_values = [v for v in window if v is not None]
            # 只有在有有效值的情况下才计算平均值，避免除以零
            if valid_values:
                sma = sum(valid_values) / len(valid_values)
                # 仅为当前有实际值的点附加SMA值
                if numeric_value is not None:
                    sma_values.append(round(sma, 2))
                else:
                    sma_values.append(None)
            else:
                sma_values.append(None)
        else:
            # 在窗口未满时，不计算SMA
            sma_values.append(None)

    return sma_values


def get_chart_data_for_user(user):
    """
    为指定用户准备所有图表所需的数据。

    :param user: 用户对象
    :return: 一个元组 (chart_data_dict, setup_needed_flag)
    """
    # 1. 检查用户的周起始日设置
    start_date_setting = Setting.query.filter_by(user_id=user.id, key='week_start_date').first()
    if not start_date_setting:
        return None, True

    start_date_dt = date.fromisoformat(start_date_setting.value)

    # 2. 获取基础数据
    all_logs = LogEntry.query.filter_by(user_id=user.id).order_by(LogEntry.log_date.asc()).all()
    if not all_logs:
        empty_kpis = {'total_hours': 0, 'total_days': 0, 'avg_daily_minutes': 0}
        return {'kpis': empty_kpis}, False

    # 3. 计算核心绩效指标 (KPIs)
    total_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).filter(
        LogEntry.user_id == user.id).scalar() or 0
    total_hours = round(total_duration_minutes / 60, 1)
    total_days_with_logs = db.session.query(func.count(func.distinct(LogEntry.log_date))).filter(
        LogEntry.user_id == user.id).scalar() or 0
    avg_daily_minutes = round(total_duration_minutes / total_days_with_logs, 1) if total_days_with_logs > 0 else 0
    kpis = {'total_hours': total_hours, 'total_days': total_days_with_logs, 'avg_daily_minutes': avg_daily_minutes}

    # 4. 准备周视图数据
    weekly_efficiencies_map = {(w.year, w.week_num): w.efficiency for w in
                               WeeklyData.query.filter_by(user_id=user.id).all()}
    weekly_data_agg = {}
    for log in all_logs:
        year, week_num = get_custom_week_info(log.log_date, start_date_dt)
        week_key = (year, week_num)
        weekly_data_agg.setdefault(week_key, {'duration': 0})['duration'] += log.actual_duration or 0

    sorted_weeks = sorted(weekly_data_agg.keys(), key=lambda x: (x[0], x[1]))
    weekly_labels = [f"{w[0]}-W{w[1]:02d}" for w in sorted_weeks]
    weekly_durations_actual = [round(weekly_data_agg[w]['duration'] / 60, 2) for w in sorted_weeks]
    weekly_efficiencies_actual = [weekly_efficiencies_map.get(w) for w in sorted_weeks]

    weekly_duration_data = {
        'labels': weekly_labels,
        'actuals': weekly_durations_actual,
        'trends': _calculate_sma(weekly_durations_actual)
    }
    weekly_efficiency_data = {
        'labels': weekly_labels,
        'actuals': weekly_efficiencies_actual,
        'trends': _calculate_sma(weekly_efficiencies_actual)
    }

    # 5. 准备日视图数据 (带缺失日期填充)
    first_log_date = all_logs[0].log_date
    date_range = [first_log_date + timedelta(days=x) for x in range((date.today() - first_log_date).days + 1)]

    daily_duration_map = {d[0]: d[1] for d in db.session.query(LogEntry.log_date, func.sum(LogEntry.actual_duration))
    .filter(LogEntry.user_id == user.id).group_by(LogEntry.log_date).all()}
    daily_efficiency_map = {d.log_date: d.efficiency for d in DailyData.query.filter_by(user_id=user.id).all()}

    daily_labels = [d.isoformat() for d in date_range]
    daily_durations_actual = [round(daily_duration_map.get(day, 0) / 60, 2) for day in date_range]
    daily_efficiencies_actual = [daily_efficiency_map.get(day) for day in date_range]

    daily_duration_data = {
        'labels': daily_labels,
        'actuals': daily_durations_actual,
        'trends': _calculate_sma(daily_durations_actual, window_size=7)
    }
    daily_efficiency_data = {
        'labels': daily_labels,
        'actuals': daily_efficiencies_actual,
        'trends': _calculate_sma(daily_efficiencies_actual, window_size=7)
    }

    # 6. 将所有数据打包返回
    chart_data = {
        'kpis': kpis,
        'weekly_duration_data': weekly_duration_data,
        'weekly_efficiency_data': weekly_efficiency_data,
        'daily_duration_data': daily_duration_data,
        'daily_efficiency_data': daily_efficiency_data,
    }

    return chart_data, False