# learning_logger/services/record_service.py (Corrected)

from datetime import date, timedelta
from itertools import groupby
from flask import current_app
from .. import db
from ..models import Stage, LogEntry, WeeklyData, DailyData
from ..helpers import get_custom_week_info


def get_structured_logs_for_stage(stage, sort_order='desc'):
    """为指定的“阶段”获取结构化的学习记录。"""
    is_reverse = (sort_order == 'desc')
    stage_start_date = stage.start_date

    logs = stage.log_entries.order_by(LogEntry.log_date.asc(), LogEntry.id.asc()).all()

    logs_by_week = groupby(logs, key=lambda log: get_custom_week_info(log.log_date, stage_start_date))

    structured_logs = []
    week_data_map = {(w.year, w.week_num): w for w in stage.weekly_data.all()}
    day_data_map = {d.log_date: d for d in stage.daily_data.all()}

    for (year, week_num), week_logs_iter in logs_by_week:
        days_in_week = []
        week_logs_list = list(week_logs_iter)

        for day_date, day_logs_iter in groupby(week_logs_list, key=lambda log: log.log_date):
            day_data = day_data_map.get(day_date)
            days_in_week.append({
                'date': day_date,
                'day_id': day_data.id if day_data else None,
                'efficiency': day_data.efficiency if day_data else None,
                'logs': list(day_logs_iter)
            })

        week_data = week_data_map.get((year, week_num))
        structured_logs.append({
            'year': year,
            'week_num': week_num,
            'week_id': week_data.id if week_data else None,
            'efficiency': week_data.efficiency if week_data else None,
            'days': sorted(days_in_week, key=lambda d: d['date'], reverse=is_reverse)
        })

    return sorted(structured_logs, key=lambda w: (w['year'], w['week_num']), reverse=is_reverse)


def add_log_for_stage(stage_id, user, form_data):
    """为指定阶段添加一条新的学习记录。"""
    stage = Stage.query.filter_by(id=stage_id, user_id=user.id).first()
    if not stage:
        return False, "指定的阶段不存在或无权访问。"

    try:
        log_date = date.fromisoformat(form_data['log_date'])
        _get_or_create_week_and_day(stage, log_date)

        new_log = LogEntry(
            stage_id=stage.id,
            log_date=log_date,
            task=form_data.get('task'),
            time_slot=form_data.get('time_slot'),
            category=form_data.get('category'),
            notes=form_data.get('notes'),
            actual_duration=form_data.get('actual_duration', type=int),
            mood=form_data.get('mood', type=int)
        )
        db.session.add(new_log)
        db.session.commit()
        return True, '新纪录添加成功！'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add log error: {e}")
        return False, f'发生错误: {e}'


def update_log_for_user(log_id, user, form_data):
    """更新一条学习记录，并在内部进行权限检查。"""
    log = get_log_entry_for_user(log_id, user)
    if not log:
        return False, '未找到要编辑的记录或无权访问。'

    try:
        original_date = log.log_date
        new_date = date.fromisoformat(form_data.get('log_date'))

        if original_date != new_date:
            _get_or_create_week_and_day(log.stage, new_date)

        log.log_date = new_date
        log.task = form_data.get('task')
        log.time_slot = form_data.get('time_slot')
        log.category = form_data.get('category')
        log.notes = form_data.get('notes')
        log.actual_duration = form_data.get('actual_duration', type=int)
        log.mood = form_data.get('mood', type=int)
        db.session.commit()
        return True, '记录更新成功！'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update log error: {e}")
        return False, f'更新时发生错误: {e}'


def delete_log_for_user(log_id, user):
    """删除一条学习记录，并在内部进行权限检查。"""
    log = get_log_entry_for_user(log_id, user)
    if not log:
        return False, '未找到要删除的记录或无权访问。'
    try:
        db.session.delete(log)
        db.session.commit()
        return True, '记录已删除。'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete log error: {e}")
        return False, f'删除时发生错误: {e}'


def update_weekly_efficiency(week_id, user, efficiency):
    """更新周效率记录。"""
    weekly_data = get_weekly_data_for_user(week_id, user)
    if not weekly_data:
        return False, '未找到周记录或无权访问。'
    try:
        weekly_data.efficiency = efficiency
        db.session.commit()
        return True, f'第 {weekly_data.week_num} 周效率已更新！'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update week efficiency error: {e}")
        return False, f'更新周效率时发生错误: {e}'


def update_daily_efficiency(day_id, user, efficiency):
    """更新日效率记录。"""
    daily_data = get_daily_data_for_user(day_id, user)
    if not daily_data:
        return False, '未找到日记录或无权访问。'
    try:
        daily_data.efficiency = efficiency
        db.session.commit()
        return True, f'{daily_data.log_date.strftime("%Y-%m-%d")} 的效率已更新！'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update day efficiency error: {e}")
        return False, f'更新日效率时发生错误: {e}'


def get_log_entry_for_user(log_id, user):
    """获取单条 LogEntry 并验证其是否属于该用户。"""
    return LogEntry.query.join(Stage).filter(Stage.user_id == user.id, LogEntry.id == log_id).first()


def get_weekly_data_for_user(week_id, user):
    """获取单条 WeeklyData 并验证其是否属于该用户。"""
    return WeeklyData.query.join(Stage).filter(Stage.user_id == user.id, WeeklyData.id == week_id).first()


def get_daily_data_for_user(day_id, user):
    """获取单条 DailyData 并验证其是否属于该用户。"""
    return DailyData.query.join(Stage).filter(Stage.user_id == user.id, DailyData.id == day_id).first()


def _get_or_create_week_and_day(stage, log_date):
    """内部函数：确保给定日期的周和日记录存在，如果不存在则创建。"""
    daily_data = DailyData.query.filter_by(log_date=log_date, stage_id=stage.id).first()
    if not daily_data:
        daily_data = DailyData(log_date=log_date, stage_id=stage.id)
        db.session.add(daily_data)
        db.session.flush()

    # ============================================================================
    # 核心修正
    # ============================================================================
    year, week_num = get_custom_week_info(log_date, stage.start_date)

    weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num, stage_id=stage.id).first()
    if not weekly_data:
        weekly_data = WeeklyData(year=year, week_num=week_num, stage_id=stage.id)
        db.session.add(weekly_data)
        db.session.flush()

    return weekly_data, daily_data