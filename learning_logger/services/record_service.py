# learning_logger/services/record_service.py

from datetime import date
from itertools import groupby
from .. import db
from ..models import LogEntry, WeeklyData, DailyData, Setting
from ..helpers import get_custom_week_info


def get_structured_logs_for_user(user, sort_order='desc'):
    """
    为指定用户获取结构化的学习记录。
    这是从原视图函数中抽离出来的核心业务逻辑。

    :param user: 用户对象 (通常是 current_user)
    :param sort_order: 排序顺序 ('asc' or 'desc')
    :return: 一个元组 (structured_logs, setup_needed_flag)
    """
    is_reverse = (sort_order == 'desc')

    # 1. 查询用户的周起始日设置
    start_date_setting = Setting.query.filter_by(user_id=user.id, key='week_start_date').first()
    if not start_date_setting:
        # 如果用户未设置，返回一个标志，让视图处理重定向或提示
        return [], True

    start_date = date.fromisoformat(start_date_setting.value)

    # 2. 查询该用户的所有相关数据
    logs = LogEntry.query.filter_by(user_id=user.id).order_by(LogEntry.log_date.asc(), LogEntry.id.asc()).all()
    weekly_efficiencies = {(w.year, w.week_num): w.efficiency for w in
                           WeeklyData.query.filter_by(user_id=user.id).all()}
    daily_efficiencies = {d.log_date: d.efficiency for d in DailyData.query.filter_by(user_id=user.id).all()}

    # 3. 按周和天组织数据（这部分逻辑与之前完全相同）
    logs_by_week = groupby(logs, key=lambda log: get_custom_week_info(log.log_date, start_date))

    structured_logs = []
    for (year, week_num), week_logs_iter in logs_by_week:
        days_in_week = []
        for day_date, day_logs_iter in groupby(list(week_logs_iter), key=lambda log: log.log_date):
            days_in_week.append({
                'date': day_date,
                'efficiency': daily_efficiencies.get(day_date),
                'logs': list(day_logs_iter)
            })

        structured_logs.append({
            'year': year,
            'week_num': week_num,
            'efficiency': weekly_efficiencies.get((year, week_num)),
            'days': sorted(days_in_week, key=lambda d: d['date'], reverse=is_reverse)
        })

    # 4. 根据排序顺序对周进行排序
    sorted_weeks = sorted(structured_logs, key=lambda w: (w['year'], w['week_num']), reverse=is_reverse)

    # 5. 为前端添加索引（如果需要）
    for week_idx, week in enumerate(sorted_weeks):
        week['week_index'] = week_idx
        for day_idx, day in enumerate(week['days']):
            day['day_index'] = day_idx

    # 6. 返回处理好的数据和设置完成的标志
    return sorted_weeks, False


# ===============================================================
#  请将以下代码追加到 record_service.py 文件的末尾
# ===============================================================

def add_log_for_user(user, form_data):
    """
    为指定用户添加一条新的学习记录。

    :param user: 用户对象
    :param form_data: 从请求表单中获取的数据 (e.g., request.form)
    :return: 一个元组 (success_boolean, message_string)
    """
    try:
        new_log = LogEntry(
            user_id=user.id,  # 关联用户
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
        return True, '新纪录添加成功！'
    except Exception as e:
        db.session.rollback()
        # 在实际应用中，这里应该记录更详细的错误日志
        return False, f'发生错误: {e}'


def update_log_for_user(log_id, user, form_data):
    """
    更新指定用户的一条学习记录。

    :param log_id: 要更新的记录ID
    :param user: 用户对象
    :param form_data: 从请求表单中获取的数据
    :return: 一个元组 (success_boolean, message_string)
    """
    # 查询时确保记录属于该用户，防止越权修改
    log = LogEntry.query.filter_by(id=log_id, user_id=user.id).first()

    if not log:
        return False, '未找到要编辑的记录。'

    try:
        log.log_date = date.fromisoformat(form_data.get('log_date'))
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
        return False, f'更新时发生错误: {e}'


def delete_log_for_user(log_id, user):
    """
    删除指定用户的一条学习记录。

    :param log_id: 要删除的记录ID
    :param user: 用户对象
    :return: 一个元组 (success_boolean, message_string)
    """
    # 查询时确保记录属于该用户，防止越权删除
    log = LogEntry.query.filter_by(id=log_id, user_id=user.id).first()

    if not log:
        return False, '未找到要删除的记录。'

    try:
        db.session.delete(log)
        db.session.commit()
        return True, '记录已删除。'
    except Exception as e:
        db.session.rollback()
        return False, f'删除时发生错误: {e}'


# ===============================================================
#  请将以下代码追加到 record_service.py 文件的末尾
# ===============================================================

def update_weekly_efficiency_for_user(user, year, week_num, efficiency):
    """
    为指定用户更新或创建周效率记录。

    :param user: 用户对象
    :param year: 年份
    :param week_num: 周数
    :param efficiency: 效率值
    :return: 一个元组 (success_boolean, message_string)
    """
    try:
        # merge 会根据主键 (user_id, year, week_num) 自动判断是插入还是更新
        weekly_data = WeeklyData(user_id=user.id, year=year, week_num=week_num, efficiency=efficiency)
        db.session.merge(weekly_data)
        db.session.commit()
        return True, f'第 {week_num} 周效率已更新！'
    except Exception as e:
        db.session.rollback()
        return False, f'更新周效率时发生错误: {e}'


def update_daily_efficiency_for_user(user, iso_date, efficiency):
    """
    为指定用户更新或创建日效率记录。

    :param user: 用户对象
    :param iso_date: ISO 格式的日期字符串 (e.g., "2023-10-27")
    :param efficiency: 效率值
    :return: 一个元组 (success_boolean, message_string)
    """
    try:
        log_date = date.fromisoformat(iso_date)

        # 先查询记录是否存在
        daily_data = DailyData.query.filter_by(log_date=log_date, user_id=user.id).first()

        if daily_data:
            # 如果存在，则更新
            daily_data.efficiency = efficiency
        else:
            # 如果不存在，则创建新记录
            daily_data = DailyData(log_date=log_date, efficiency=efficiency, user_id=user.id)
            db.session.add(daily_data)

        db.session.commit()
        return True, f'{log_date.strftime("%Y-%m-%d")} 的效率已更新！'
    except Exception as e:
        db.session.rollback()
        return False, f'更新日效率时发生错误: {e}'
