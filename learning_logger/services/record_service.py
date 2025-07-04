# learning_logger/services/record_service.py (MODIFIED FOR LOGARITHMIC EFFICIENCY)
import math  # <-- 1. 新增导入 math 库
from datetime import date, timedelta
from itertools import groupby
from flask import current_app
from .. import db
from ..models import Stage, LogEntry, WeeklyData, DailyData, Category, SubCategory
from ..helpers import get_custom_week_info


# --- Private Calculation Engine (已按方案C修改) ---
def _calculate_daily_efficiency_score(log_date, stage_id):
    """
    按“方案C：对数加权模型”计算每日效率分。
    公式: 每日效率 = (加权平均心情) × log(1 + 总学习小时数)
    """
    logs_for_day = LogEntry.query.filter_by(log_date=log_date, stage_id=stage_id).all()

    if not logs_for_day:
        return 0.0

    total_duration_minutes = sum(log.actual_duration or 0 for log in logs_for_day)

    # 如果当天没有学习时长，则效率为0
    if total_duration_minutes == 0:
        return 0.0

    # 2. 计算加权心情总分 和 总时长
    weighted_mood_duration_sum = sum((log.actual_duration or 0) * (log.mood or 3) for log in logs_for_day)

    # 3. 计算“加权平均心情”（1-5分）
    # 这是当天的学习“质量”分
    average_mood = weighted_mood_duration_sum / total_duration_minutes

    # 4. 计算总学习小时数
    # 这是当天的学习“数量”
    total_hours = total_duration_minutes / 60.0

    # 5. 应用最终的对数加权公式
    # 使用 log1p(x) 等同于 log(1+x)，可以更精确地处理非常小的 x 值
    final_score = average_mood * math.log1p(total_hours)

    return final_score


def _get_or_create_daily_data(log_date, stage_id, score):
    daily_data = DailyData.query.filter_by(log_date=log_date, stage_id=stage_id).first()
    if not daily_data:
        daily_data = DailyData(log_date=log_date, stage_id=stage_id)
        db.session.add(daily_data)
    daily_data.efficiency = score


def _get_or_create_weekly_data(year, week_num, stage_id, score):
    weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num, stage_id=stage_id).first()
    if not weekly_data:
        weekly_data = WeeklyData(year=year, week_num=week_num, stage_id=stage_id)
        db.session.add(weekly_data)
    weekly_data.efficiency = score


# --- Public Calculation Trigger ---
def recalculate_efficiency_for_stage(stage):
    try:
        all_logs = stage.log_entries.all()
        DailyData.query.filter_by(stage_id=stage.id).delete()
        WeeklyData.query.filter_by(stage_id=stage.id).delete()
        db.session.commit()

        if not all_logs:
            return

        unique_log_dates = sorted(list(set(log.log_date for log in all_logs)))
        daily_efficiencies_map = {}
        for log_date in unique_log_dates:
            score = _calculate_daily_efficiency_score(log_date, stage.id)
            _get_or_create_daily_data(log_date, stage.id, score)
            daily_efficiencies_map[log_date] = score

        db.session.commit()

        next_stage = Stage.query.filter(Stage.user_id == stage.user_id, Stage.start_date > stage.start_date).order_by(
            Stage.start_date.asc()).first()
        stage_end_date = (next_stage.start_date - timedelta(days=1)) if next_stage else date.today()

        unique_weeks = sorted(list(set(get_custom_week_info(d, stage.start_date) for d in unique_log_dates)))
        for year, week_num in unique_weeks:
            theoretical_week_start = stage.start_date + timedelta(weeks=week_num - 1)
            theoretical_week_end = theoretical_week_start + timedelta(days=6)
            effective_start = max(theoretical_week_start, stage.start_date)
            effective_end = min(theoretical_week_end, stage_end_date, date.today())
            days_in_week = (effective_end - effective_start).days + 1 if effective_end >= effective_start else 0

            # 周效率分现在是每日新效率分的平均值
            total_score = sum(
                daily_efficiencies_map.get(effective_start + timedelta(days=i), 0) for i in range(days_in_week))
            average_score = total_score / days_in_week if days_in_week > 0 else 0
            _get_or_create_weekly_data(year, week_num, stage.id, average_score)

        db.session.commit()
        current_app.logger.info(f"Successfully recalculated efficiency for stage '{stage.name}'.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in recalculate_efficiency_for_stage for stage '{stage.name}': {e}",
                                 exc_info=True)


# --- Read-Only Display Service ---
def get_structured_logs_for_stage(stage, sort_order='desc'):
    is_reverse = (sort_order == 'desc')
    all_logs = stage.log_entries.order_by(LogEntry.log_date.asc(), LogEntry.id.asc()).all()
    day_data_map = {d.log_date: d for d in stage.daily_data.all()}
    week_data_map = {(w.year, w.week_num): w for w in stage.weekly_data.all()}
    structured_logs = []
    if not all_logs:
        return structured_logs
    logs_by_week_iter = groupby(all_logs, key=lambda log: get_custom_week_info(log.log_date, stage.start_date))
    for (year, week_num), week_logs in logs_by_week_iter:
        days_in_week = []
        logs_by_day_iter = groupby(list(week_logs), key=lambda log: log.log_date)
        for day_date, day_logs in logs_by_day_iter:
            day_data = day_data_map.get(day_date)
            days_in_week.append(
                {'date': day_date, 'efficiency': day_data.efficiency if day_data else 0, 'logs': list(day_logs)})
        week_data = week_data_map.get((year, week_num))
        structured_logs.append(
            {'year': year, 'week_num': week_num, 'efficiency': week_data.efficiency if week_data else 0,
             'days': sorted(days_in_week, key=lambda d: d['date'], reverse=is_reverse)})
    return sorted(structured_logs, key=lambda w: (w['year'], w['week_num']), reverse=is_reverse)


# --- Data Modification Functions (这部分代码保持不变) ---
def add_log_for_stage(stage_id, user, form_data):
    stage = Stage.query.filter_by(id=stage_id, user_id=user.id).first()
    if not stage: return False, "指定的阶段不存在或无权访问。"
    try:
        subcategory_id = form_data.get('subcategory_id', type=int)
        if subcategory_id:
            subcategory = SubCategory.query.join(Category).filter(SubCategory.id == subcategory_id,
                                                                  Category.user_id == user.id).first()
            if not subcategory: return False, "选择了无效的分类。"

        hours_str = form_data.get('duration_hours', '0')
        minutes_str = form_data.get('duration_minutes', '0')
        hours = int(hours_str) if hours_str and hours_str.strip() else 0
        minutes = int(minutes_str) if minutes_str and minutes_str.strip() else 0
        total_duration = (hours * 60) + minutes

        new_log = LogEntry(stage_id=stage.id, log_date=date.fromisoformat(form_data['log_date']),
                           task=form_data.get('task'), time_slot=form_data.get('time_slot'),
                           notes=form_data.get('notes'),
                           actual_duration=total_duration,
                           mood=form_data.get('mood', type=int),
                           subcategory_id=subcategory_id)
        db.session.add(new_log)
        db.session.commit()
        recalculate_efficiency_for_stage(stage)
        return True, '新纪录添加成功！'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add log error: {e}", exc_info=True)
        return False, f'发生错误: {e}'


def update_log_for_user(log_id, user, form_data):
    log = get_log_entry_for_user(log_id, user)
    if not log: return False, '未找到要编辑的记录或无权访问。'
    try:
        stage = log.stage
        subcategory_id = form_data.get('subcategory_id', type=int)
        if subcategory_id:
            subcategory = SubCategory.query.join(Category).filter(SubCategory.id == subcategory_id,
                                                                  Category.user_id == user.id).first()
            if not subcategory: return False, "选择了无效的分类。"

        hours_str = form_data.get('duration_hours', '0')
        minutes_str = form_data.get('duration_minutes', '0')
        hours = int(hours_str) if hours_str and hours_str.strip() else 0
        minutes = int(minutes_str) if minutes_str and minutes_str.strip() else 0
        total_duration = (hours * 60) + minutes

        log.log_date = date.fromisoformat(form_data.get('log_date'))
        log.task = form_data.get('task')
        log.time_slot = form_data.get('time_slot')
        log.notes = form_data.get('notes')
        log.actual_duration = total_duration
        log.mood = form_data.get('mood', type=int)
        log.subcategory_id = subcategory_id

        db.session.commit()
        recalculate_efficiency_for_stage(stage)
        return True, '记录更新成功！'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update log error: {e}", exc_info=True)
        return False, f'更新时发生错误: {e}'


def delete_log_for_user(log_id, user):
    log = get_log_entry_for_user(log_id, user)
    if not log: return False, '未找到要删除的记录或无权访问。'
    try:
        stage = log.stage
        db.session.delete(log)
        db.session.commit()
        recalculate_efficiency_for_stage(stage)
        return True, '记录已删除。'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete log error: {e}", exc_info=True)
        return False, f'删除时发生错误: {e}'


def get_log_entry_for_user(log_id, user):
    return LogEntry.query.join(Stage).filter(Stage.user_id == user.id, LogEntry.id == log_id).first()