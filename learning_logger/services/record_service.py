# learning_logger/services/record_service.py (Ultimate Version with Stage-Boundary-Aware Calculation)

from datetime import date, timedelta
from itertools import groupby
from flask import current_app
from .. import db
from ..models import Stage, LogEntry, WeeklyData, DailyData
from ..helpers import get_custom_week_info


# ============================================================================
# 1. ULTIMATE: Core Efficiency Calculation Engine
# ============================================================================

def _calculate_and_update_daily_efficiency(log_date, stage):
    """
    计算指定日期的“生产力积分”并更新到数据库。
    公式: (Σ (单次学习时长(分钟) * 心情评分)) / 60
    """
    logs_for_day = LogEntry.query.filter_by(log_date=log_date, stage_id=stage.id).all()
    total_score = 0
    if logs_for_day:
        for log in logs_for_day:
            duration = log.actual_duration or 0
            mood = log.mood or 3
            total_score += duration * mood
    final_efficiency = total_score / 60.0
    daily_data = DailyData.query.filter_by(log_date=log_date, stage_id=stage.id).first()
    if not daily_data:
        daily_data = DailyData(log_date=log_date, stage_id=stage.id)
        db.session.add(daily_data)
    daily_data.efficiency = final_efficiency
    return final_efficiency


def _calculate_and_update_weekly_efficiency_final(year, week_num, stage, stage_end_date, daily_efficiencies_map):
    """
    【终极版】计算周平均效率，严格遵守阶段的起止边界。
    """
    # 1. 确定本周的理论起止日期 (周一到周日)
    #    注意：这里的 week_start_day 是基于阶段自定义的周次计算得出的
    theoretical_week_start = stage.start_date + timedelta(weeks=week_num - 1)
    theoretical_week_end = theoretical_week_start + timedelta(days=6)

    # 2. 根据阶段起止日期，确定本周的“有效”计算范围
    #    有效起始日 = max(本周理论起始日, 阶段开始日)
    effective_start_date = max(theoretical_week_start, stage.start_date)
    #    有效结束日 = min(本周理论结束日, 阶段结束日, 今天)
    effective_end_date = min(theoretical_week_end, stage_end_date, date.today())

    # 3. 计算有效天数（除数）
    #    如果有效结束日小于起始日，说明这一周完全不在计算范围内 (例如，当前周还没开始)
    if effective_end_date < effective_start_date:
        days_in_week = 0
    else:
        days_in_week = (effective_end_date - effective_start_date).days + 1

    # 4. 累加有效范围内的每日效率
    total_weekly_efficiency = 0
    current_day = effective_start_date
    while current_day <= effective_end_date:
        total_weekly_efficiency += daily_efficiencies_map.get(current_day, 0)
        current_day += timedelta(days=1)

    final_average = total_weekly_efficiency / days_in_week if days_in_week > 0 else 0

    # 5. 更新数据库
    weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num, stage_id=stage.id).first()
    if not weekly_data:
        weekly_data = WeeklyData(year=year, week_num=week_num, stage_id=stage.id)
        db.session.add(weekly_data)

    weekly_data.efficiency = final_average
    return final_average


# ============================================================================
# 2. OVERHAULED: Main Data Fetching and Orchestration
# ============================================================================
def get_structured_logs_for_stage(stage, sort_order='desc'):
    """
    为指定阶段获取结构化学习记录，并在获取前自动计算所有效率。
    """
    try:
        # --- 计算阶段 ---
        all_logs = stage.log_entries.order_by(LogEntry.log_date.asc()).all()
        if not all_logs:
            return []

        # 1. 确定此阶段的有效结束日期
        next_stage = Stage.query.filter(Stage.user_id == stage.user_id, Stage.start_date > stage.start_date).order_by(
            Stage.start_date.asc()).first()
        stage_end_date = (next_stage.start_date - timedelta(days=1)) if next_stage else date.today()

        # 2. 批量计算所有涉及日期的“日效率”
        unique_log_dates = sorted(list(set(log.log_date for log in all_logs)))
        daily_efficiencies_map = {}
        for log_date in unique_log_dates:
            daily_efficiencies_map[log_date] = _calculate_and_update_daily_efficiency(log_date, stage)

        # 3. 批量计算所有涉及周的“周效率”
        unique_weeks = sorted(list(set(get_custom_week_info(d, stage.start_date) for d in unique_log_dates)))
        for year, week_num in unique_weeks:
            _calculate_and_update_weekly_efficiency_final(year, week_num, stage, stage_end_date, daily_efficiencies_map)

        db.session.commit()

        # --- 数据组织阶段 ---
        is_reverse = (sort_order == 'desc')
        all_logs_refreshed = stage.log_entries.order_by(LogEntry.log_date.asc(), LogEntry.id.asc()).all()
        logs_by_week = groupby(all_logs_refreshed, key=lambda log: get_custom_week_info(log.log_date, stage.start_date))

        structured_logs = []
        week_data_map = {(w.year, w.week_num): w for w in stage.weekly_data.all()}
        day_data_map = {d.log_date: d for d in stage.daily_data.all()}

        for (year, week_num), week_logs_iter in logs_by_week:
            days_in_week = []
            for day_date, day_logs_iter in groupby(list(week_logs_iter), key=lambda log: log.log_date):
                day_data = day_data_map.get(day_date)
                days_in_week.append({
                    'date': day_date,
                    'efficiency': day_data.efficiency if day_data else 0,
                    'logs': list(day_logs_iter)
                })

            week_data = week_data_map.get((year, week_num))
            structured_logs.append({
                'year': year,
                'week_num': week_num,
                'efficiency': week_data.efficiency if week_data else 0,
                'days': sorted(days_in_week, key=lambda d: d['date'], reverse=is_reverse)
            })

        return sorted(structured_logs, key=lambda w: (w['year'], w['week_num']), reverse=is_reverse)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in get_structured_logs_for_stage: {e}")
        return []


# ============================================================================
# 3. SIMPLIFIED: Data Modification Functions
# ============================================================================
def add_log_for_stage(stage_id, user, form_data):
    """为指定阶段添加一条新的学习记录。不再需要手动处理周/日数据。"""
    stage = Stage.query.filter_by(id=stage_id, user_id=user.id).first()
    if not stage:
        return False, "指定的阶段不存在或无权访问。"
    try:
        new_log = LogEntry(
            stage_id=stage.id,
            log_date=date.fromisoformat(form_data['log_date']),
            task=form_data.get('task'),
            time_slot=form_data.get('time_slot'),
            category=form_data.get('category'),
            notes=form_data.get('notes'),
            actual_duration=form_data.get('actual_duration', type=int),
            mood=form_data.get('mood', type=int)
        )
        db.session.add(new_log)
        db.session.commit()
        return True, '新纪录添加成功！效率将在下次刷新时更新。'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add log error: {e}")
        return False, f'发生错误: {e}'


def update_log_for_user(log_id, user, form_data):
    """更新一条学习记录。"""
    log = get_log_entry_for_user(log_id, user)
    if not log:
        return False, '未找到要编辑的记录或无权访问。'
    try:
        log.log_date = date.fromisoformat(form_data.get('log_date'))
        log.task = form_data.get('task')
        log.time_slot = form_data.get('time_slot')
        log.category = form_data.get('category')
        log.notes = form_data.get('notes')
        log.actual_duration = form_data.get('actual_duration', type=int)
        log.mood = form_data.get('mood', type=int)
        db.session.commit()
        return True, '记录更新成功！效率将在下次刷新时更新。'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update log error: {e}")
        return False, f'更新时发生错误: {e}'


def delete_log_for_user(log_id, user):
    """删除一条学习记录。"""
    log = get_log_entry_for_user(log_id, user)
    if not log:
        return False, '未找到要删除的记录或无权访问。'
    try:
        db.session.delete(log)
        db.session.commit()
        return True, '记录已删除。效率将在下次刷新时更新。'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete log error: {e}")
        return False, f'删除时发生错误: {e}'


# ============================================================================
# 4. UNCHANGED: Helper Functions for Authorization
# ============================================================================
def get_log_entry_for_user(log_id, user):
    return LogEntry.query.join(Stage).filter(Stage.user_id == user.id, LogEntry.id == log_id).first()


def get_weekly_data_for_user(week_id, user):
    return WeeklyData.query.join(Stage).filter(Stage.user_id == user.id, WeeklyData.id == week_id).first()


def get_daily_data_for_user(day_id, user):
    return DailyData.query.join(Stage).filter(Stage.user_id == user.id, DailyData.id == day_id).first()