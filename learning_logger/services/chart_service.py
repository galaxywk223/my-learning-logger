# learning_logger/services/chart_service.py (Final Corrected Version)

import collections
from datetime import date, timedelta
from sqlalchemy import func
from .. import db
from ..models import Stage, LogEntry, WeeklyData, DailyData
from ..helpers import get_custom_week_info


def _calculate_sma(data, window_size=7):
    """内部辅助函数：计算简单移动平均值 (SMA)，并处理空值。"""
    if not data or window_size <= 1:
        return [None] * len(data)

    sma_values = []
    window = collections.deque(maxlen=window_size)

    for i, value in enumerate(data):
        try:
            numeric_value = float(value) if value is not None else None
        except (ValueError, TypeError):
            numeric_value = None

        window.append(numeric_value)

        if i < window_size - 1:
            sma_values.append(None)
        else:
            valid_values = [v for v in window if v is not None]
            if valid_values:
                sma = sum(valid_values) / len(valid_values)
                sma_values.append(round(sma, 2))
            else:
                sma_values.append(None)
    return sma_values


def get_chart_data_for_user(user):
    """为指定用户准备所有图表所需的数据，支持全局周次轴和加权平均。"""
    all_stages = Stage.query.filter_by(user_id=user.id).order_by(Stage.start_date.asc()).all()
    if not all_stages:
        # 如果没有任何阶段，返回一个明确的空数据结构
        return {'kpis': {'total_hours': 0, 'total_days': 0, 'avg_daily_minutes': 0}, 'stage_annotations': []}, True

    stage_ids = [s.id for s in all_stages]
    all_logs = LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).order_by(LogEntry.log_date.asc()).all()
    if not all_logs:
        return {'kpis': {'total_hours': 0, 'total_days': 0, 'avg_daily_minutes': 0}, 'stage_annotations': []}, False

    # ============================================================================
    # 核心修正：重构KPIs计算顺序
    # ============================================================================
    total_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).filter(
        LogEntry.stage_id.in_(stage_ids)).scalar() or 0
    total_days_with_logs = db.session.query(func.count(func.distinct(LogEntry.log_date))).filter(
        LogEntry.stage_id.in_(stage_ids)).scalar() or 0

    kpis = {
        'total_hours': round(total_duration_minutes / 60, 1),
        'total_days': total_days_with_logs,
        'avg_daily_minutes': round(total_duration_minutes / total_days_with_logs, 1) if total_days_with_logs > 0 else 0
    }

    # --- 后续逻辑保持不变 ---
    global_start_date = all_stages[0].start_date
    first_log_date = all_logs[0].log_date
    last_log_date = date.today()

    daily_duration_map = {d[0]: d[1] for d in
                          db.session.query(LogEntry.log_date, func.sum(LogEntry.actual_duration)).filter(
                              LogEntry.stage_id.in_(stage_ids)).group_by(LogEntry.log_date).all()}
    weekly_efficiency_map = {(w.year, w.week_num, w.stage_id): float(w.efficiency) for w in
                             WeeklyData.query.filter(WeeklyData.stage_id.in_(stage_ids)).all() if
                             w.efficiency is not None and w.efficiency != ''}
    stage_start_map = {s.id: s.start_date for s in all_stages}

    global_weeks = collections.defaultdict(lambda: {'duration': 0, 'efficiency_data': []})

    current_date = first_log_date
    while current_date <= last_log_date:
        g_year, g_week_num = get_custom_week_info(current_date, global_start_date)
        week_key = (g_year, g_week_num)
        global_weeks[week_key]['duration'] += daily_duration_map.get(current_date, 0) or 0

        log_on_date = next((log for log in all_logs if log.log_date == current_date), None)
        if log_on_date:
            stage_id = log_on_date.stage_id
            stage_start = stage_start_map.get(stage_id)
            if stage_start:
                s_year, s_week_num = get_custom_week_info(current_date, stage_start)
                efficiency = weekly_efficiency_map.get((s_year, s_week_num, stage_id))
                if efficiency is not None:
                    global_weeks[week_key]['efficiency_data'].append(efficiency)
        current_date += timedelta(days=1)

    sorted_week_keys = sorted(global_weeks.keys())
    weekly_labels = [f"{k[0]}-W{k[1]:02}" for k in sorted_week_keys]
    weekly_durations = [round(global_weeks[k]['duration'] / 60, 2) for k in sorted_week_keys]

    weekly_efficiencies = []
    for k in sorted_week_keys:
        eff_data = global_weeks[k]['efficiency_data']
        if not eff_data:
            weekly_efficiencies.append(None)
        else:
            # 使用简单的日平均值作为该周的加权效率
            avg_eff = sum(eff_data) / len(eff_data)
            weekly_efficiencies.append(round(avg_eff, 2))

    stage_annotations = []
    for stage in all_stages:
        start_g_year, start_g_week = get_custom_week_info(stage.start_date, global_start_date)
        next_stage = next((s for s in all_stages if s.start_date > stage.start_date), None)
        end_date = (next_stage.start_date - timedelta(days=1)) if next_stage else last_log_date
        end_g_year, end_g_week = get_custom_week_info(end_date, global_start_date)
        stage_annotations.append({
            'name': stage.name,
            'start_week_label': f"{start_g_year}-W{start_g_week:02}",
            'end_week_label': f"{end_g_year}-W{end_g_week:02}"
        })

    date_range = [first_log_date + timedelta(days=x) for x in range((last_log_date - first_log_date).days + 1)]
    daily_labels = [d.isoformat() for d in date_range]
    daily_durations = [round((daily_duration_map.get(d, 0) or 0) / 60, 2) if d in daily_duration_map else None for d in
                       date_range]

    daily_efficiency_map = {d.log_date: float(d.efficiency) for d in
                            DailyData.query.filter(DailyData.stage_id.in_(stage_ids)).all() if
                            d.efficiency is not None and d.efficiency != ''}
    daily_efficiencies = [daily_efficiency_map.get(d) for d in date_range]

    return {
        'kpis': kpis,
        'stage_annotations': stage_annotations,
        'weekly_duration_data': {'labels': weekly_labels, 'actuals': weekly_durations,
                                 'trends': _calculate_sma(weekly_durations, 3)},
        'weekly_efficiency_data': {'labels': weekly_labels, 'actuals': weekly_efficiencies,
                                   'trends': _calculate_sma(weekly_efficiencies, 3)},
        'daily_duration_data': {'labels': daily_labels, 'actuals': daily_durations,
                                'trends': _calculate_sma(daily_durations, 7)},
        'daily_efficiency_data': {'labels': daily_labels, 'actuals': daily_efficiencies,
                                  'trends': _calculate_sma(daily_efficiencies, 7)}
    }, False