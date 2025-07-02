# learning_logger/services/chart_service.py (Corrected Return Value)

import collections
from datetime import date, timedelta
from sqlalchemy import func
from .. import db
from ..models import Stage, LogEntry, WeeklyData, DailyData, Category, SubCategory
from ..helpers import get_custom_week_info

# --- NEW: Import the record service to use its calculation engine ---
from . import record_service


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
    """
    为指定用户准备所有图表所需的数据。
    【核心改造】:不再独立计算效率，而是先调用 record_service 更新数据，然后直接读取。
    """
    all_stages = Stage.query.filter_by(user_id=user.id).order_by(Stage.start_date.asc()).all()
    if not all_stages:
        # --- FIXED: Return a tuple of two values ---
        return {'kpis': {'total_hours': 0, 'total_days': 0, 'avg_daily_minutes': 0}, 'stage_annotations': []}, False

    # ============================================================================
    # 1. TRIGGER CALCULATION: Run the record service's main function for its
    #    side effect of calculating and updating all efficiency data in the DB.
    # ============================================================================
    for stage in all_stages:
        record_service.get_structured_logs_for_stage(stage)

    # ============================================================================
    # 2. READ DATA: Now that data is fresh, query the DB for chart data.
    # ============================================================================
    stage_ids = [s.id for s in all_stages]
    all_logs = LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).order_by(LogEntry.log_date.asc()).all()
    if not all_logs:
        # --- FIXED: Return a tuple of two values ---
        return {'kpis': {'total_hours': 0, 'total_days': 0, 'avg_daily_minutes': 0}, 'stage_annotations': []}, False

    # --- KPI Calculation (remains the same) ---
    total_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).filter(
        LogEntry.stage_id.in_(stage_ids)).scalar() or 0
    total_days_with_logs = db.session.query(func.count(func.distinct(LogEntry.log_date))).filter(
        LogEntry.stage_id.in_(stage_ids)).scalar() or 0
    kpis = {
        'total_hours': round(total_duration_minutes / 60, 1),
        'total_days': total_days_with_logs,
        'avg_daily_minutes': round(total_duration_minutes / total_days_with_logs, 1) if total_days_with_logs > 0 else 0
    }

    # --- Data Aggregation for Charts ---
    first_log_date = all_logs[0].log_date
    last_log_date = date.today()
    global_start_date = all_stages[0].start_date

    # --- Daily Data ---
    date_range = [first_log_date + timedelta(days=x) for x in range((last_log_date - first_log_date).days + 1)]
    daily_labels = [d.isoformat() for d in date_range]

    daily_duration_map = {d[0]: d[1] for d in
                          db.session.query(LogEntry.log_date, func.sum(LogEntry.actual_duration)).filter(
                              LogEntry.stage_id.in_(stage_ids)).group_by(LogEntry.log_date).all()}
    daily_durations = [round((daily_duration_map.get(d, 0) or 0) / 60, 2) for d in date_range]

    daily_efficiency_map = {d.log_date: d.efficiency for d in
                            DailyData.query.join(Stage).filter(Stage.user_id == user.id).all()}
    daily_efficiencies = [daily_efficiency_map.get(d) for d in date_range]

    # --- Weekly Data ---
    # Create a continuous range of weeks from the first log to the last
    weekly_data = collections.defaultdict(lambda: {'duration': 0, 'efficiency': None})

    current_d = first_log_date
    while current_d <= last_log_date:
        year, week_num = get_custom_week_info(current_d, global_start_date)
        week_key = (year, week_num)
        weekly_data[week_key]['duration'] += daily_duration_map.get(current_d, 0)
        current_d += timedelta(days=1)

    # Get weekly efficiencies from DB
    weekly_efficiency_from_db = WeeklyData.query.join(Stage).filter(Stage.user_id == user.id).all()
    for w_eff in weekly_efficiency_from_db:
        # Find the corresponding week based on the stage's start date
        week_start_in_stage = w_eff.stage.start_date + timedelta(weeks=w_eff.week_num - 1)
        global_year, global_week_num = get_custom_week_info(week_start_in_stage, global_start_date)
        week_key = (global_year, global_week_num)
        if week_key in weekly_data:
            weekly_data[week_key]['efficiency'] = w_eff.efficiency

    sorted_week_keys = sorted(weekly_data.keys())
    weekly_labels = [f"{k[0]}-W{k[1]:02}" for k in sorted_week_keys]
    weekly_durations = [round(weekly_data[k]['duration'] / 60, 2) for k in sorted_week_keys]
    weekly_efficiencies = [weekly_data[k]['efficiency'] for k in sorted_week_keys]

    # --- Stage Annotations (remains the same) ---
    stage_annotations = []
    for stage in all_stages:
        start_g_year, start_g_week = get_custom_week_info(stage.start_date, global_start_date)
        next_stage_check = Stage.query.filter(Stage.user_id == user.id, Stage.start_date > stage.start_date).order_by(
            Stage.start_date.asc()).first()
        end_date = (next_stage_check.start_date - timedelta(days=1)) if next_stage_check else last_log_date
        end_g_year, end_g_week = get_custom_week_info(end_date, global_start_date)
        stage_annotations.append({
            'name': stage.name,
            'start_week_label': f"{start_g_year}-W{start_g_week:02}",
            'end_week_label': f"{end_g_year}-W{end_g_week:02}"
        })

    # --- FIXED: Return a tuple of two values ---
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


def get_category_chart_data(user, stage_id=None):
    """为分类饼图准备数据，支持按阶段筛选。"""
    query = db.session.query(
        Category.name,
        SubCategory.name,
        func.sum(LogEntry.actual_duration)
    ).join(SubCategory, LogEntry.subcategory_id == SubCategory.id) \
        .join(Category, SubCategory.category_id == Category.id) \
        .filter(Category.user_id == user.id) \
        .group_by(Category.name, SubCategory.name)

    if stage_id:
        query = query.filter(LogEntry.stage_id == stage_id)

    results = query.all()

    if not results:
        return None

    # Process data for drilldown
    category_data = collections.defaultdict(lambda: {'total': 0, 'subs': []})
    for cat_name, sub_name, duration in results:
        duration_hours = (duration or 0) / 60.0
        category_data[cat_name]['total'] += duration_hours
        category_data[cat_name]['subs'].append({'name': sub_name, 'duration': round(duration_hours, 2)})

    # Main category view
    main_labels = list(category_data.keys())
    main_data = [round(category_data[key]['total'], 2) for key in main_labels]

    # Subcategory (drilldown) view
    sub_data = {
        cat_name: {
            'labels': [sub['name'] for sub in sorted(cat_data['subs'], key=lambda x: x['duration'], reverse=True)],
            'data': [sub['duration'] for sub in sorted(cat_data['subs'], key=lambda x: x['duration'], reverse=True)]
        } for cat_name, cat_data in category_data.items()
    }

    return {
        'main': {'labels': main_labels, 'data': main_data},
        'drilldown': sub_data
    }