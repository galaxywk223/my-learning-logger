import json
from datetime import date, datetime
from itertools import groupby

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, Response, jsonify, current_app)
# --- MODIFIED: 导入登录管理工具 ---
from flask_login import login_required, current_user

from .. import db
# 统一管理模型导入
from ..models import Setting, WeeklyData, DailyData, LogEntry, CountdownEvent
from ..helpers import get_custom_week_info  # get_setting 助手不再适用

records_bp = Blueprint('records', __name__, url_prefix='/records')


@records_bp.route('/')
# --- MODIFIED: 保护路由 ---
@login_required
def list_records():
    """
    显示当前用户的记录列表。
    """
    sort_order = request.args.get('sort', 'desc')
    is_reverse = (sort_order == 'desc')

    # --- MODIFIED: 直接查询当前用户的设置 ---
    start_date_setting = Setting.query.filter_by(user_id=current_user.id, key='week_start_date').first()
    if not start_date_setting:
        flash('请首先在设置页面中指定每周的起始日期。', 'warning')
        return render_template('index.html', setup_needed=True, structured_logs=[], current_sort=sort_order)

    start_date = date.fromisoformat(start_date_setting.value)

    # --- MODIFIED: 所有查询都必须过滤 user_id ---
    logs = LogEntry.query.filter_by(user_id=current_user.id).order_by(LogEntry.log_date.asc(), LogEntry.id.asc()).all()
    weekly_efficiencies = {(w.year, w.week_num): w.efficiency for w in
                           WeeklyData.query.filter_by(user_id=current_user.id).all()}
    daily_efficiencies = {d.log_date: d.efficiency for d in DailyData.query.filter_by(user_id=current_user.id).all()}

    # 按周和天组织数据
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

    sorted_weeks = sorted(structured_logs, key=lambda w: (w['year'], w['week_num']), reverse=is_reverse)

    # 为前端添加索引（如果需要）
    for week_idx, week in enumerate(sorted_weeks):
        week['week_index'] = week_idx
        for day_idx, day in enumerate(week['days']):
            day['day_index'] = day_idx

    return render_template('index.html', structured_logs=sorted_weeks, current_sort=sort_order, setup_needed=False)


# --- 用于加载模态框表单的路由 ---
@records_bp.route('/form/add')
@login_required
def get_add_form():
    """提供空白的记录添加表单。"""
    return render_template('_form_record.html', log=None, default_date=date.today(), action_url=url_for('records.add'),
                           submit_button_text='添加记录')


@records_bp.route('/form/edit/<int:log_id>')
@login_required
def get_edit_form(log_id):
    """提供带有数据的记录编辑表单。"""
    # --- MODIFIED: 安全地获取记录，确保是当前用户的 ---
    log = LogEntry.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    return render_template('_form_record.html', log=log, default_date=log.log_date,
                           action_url=url_for('records.edit', log_id=log.id), submit_button_text='更新记录')


@records_bp.route('/form/edit_week/<int:year>/<int:week_num>')
@login_required
def get_edit_week_form(year, week_num):
    """提供周效率编辑表单。"""
    # --- MODIFIED: 安全地获取周数据 ---
    weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num, user_id=current_user.id).first()
    return render_template('_form_edit_week.html', year=year, week_num=week_num, weekly_data=weekly_data)


@records_bp.route('/form/edit_day/<iso_date>')
@login_required
def get_edit_day_form(iso_date):
    """提供日效率编辑表单。"""
    log_date = date.fromisoformat(iso_date)
    # --- MODIFIED: 安全地获取日数据 ---
    daily_data = DailyData.query.filter_by(log_date=log_date, user_id=current_user.id).first()
    return render_template('_form_edit_day.html', log_date=log_date, daily_data=daily_data)


# --- 用于处理表单提交的路由 ---
@records_bp.route('/add', methods=['POST'])
@login_required
def add():
    """处理新记录的添加。"""
    try:
        new_log = LogEntry(
            log_date=date.fromisoformat(request.form['log_date']),
            task=request.form.get('task'),
            time_slot=request.form.get('time_slot'),
            category=request.form.get('category'),
            notes=request.form.get('notes'),
            actual_duration=request.form.get('actual_duration', type=int),
            mood=request.form.get('mood', type=int),
            # --- MODIFIED: 必须关联当前用户 ---
            user_id=current_user.id
        )
        db.session.add(new_log)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '新纪录添加成功！'})
        flash('新纪录添加成功！', 'success')
        return redirect(url_for('records.list_records'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"添加记录时出错: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'发生错误: {e}'}), 400
        flash(f'发生错误: {e}', 'error')
        return redirect(url_for('records.list_records'))


@records_bp.route('/edit/<int:log_id>', methods=['POST'])
@login_required
def edit(log_id):
    """处理记录的编辑。"""
    # --- MODIFIED: 安全地获取记录 ---
    log = LogEntry.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    try:
        log.log_date = date.fromisoformat(request.form.get('log_date'))
        log.task = request.form.get('task')
        log.time_slot = request.form.get('time_slot')
        log.category = request.form.get('category')
        log.notes = request.form.get('notes')
        log.actual_duration = request.form.get('actual_duration', type=int)
        log.mood = request.form.get('mood', type=int)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '记录更新成功！'})
        flash('记录更新成功！', 'success')
        return redirect(url_for('records.list_records'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"编辑记录 {log_id} 时出错: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'更新时发生错误: {e}'}), 400
        flash(f'更新时发生错误: {e}', 'error')
        return redirect(url_for('records.list_records'))


@records_bp.route('/delete/<int:log_id>', methods=['POST'])
@login_required
def delete(log_id):
    """处理记录的删除。"""
    # --- MODIFIED: 安全地获取记录 ---
    log = LogEntry.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(log)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': '记录已删除。'})
        flash('记录已删除。', 'info')
        return redirect(url_for('records.list_records'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除记录 {log_id} 时出错: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'删除时发生错误: {e}'}), 400
        flash(f'删除时发生错误: {e}', 'error')
        return redirect(url_for('records.list_records'))


@records_bp.route('/edit_week/<int:year>/<int:week_num>', methods=['POST'])
@login_required
def edit_week(year, week_num):
    """处理周效率的更新。"""
    try:
        efficiency = request.form['efficiency']
        # --- MODIFIED: merge 前必须指定 user_id ---
        # merge 会根据主键自动判断是插入还是更新
        weekly_data = WeeklyData(year=year, week_num=week_num, efficiency=efficiency, user_id=current_user.id)
        db.session.merge(weekly_data)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'第 {week_num} 周效率已更新！'})
        flash(f'第 {week_num} 周效率已更新！', 'success')
        return redirect(url_for('records.list_records'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新周 {year}-{week_num} 效率时出错: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'发生错误: {e}'}), 400
        flash(f'发生错误: {e}', 'error')
        return redirect(url_for('records.list_records'))


@records_bp.route('/edit_day/<iso_date>', methods=['POST'])
@login_required
def edit_day(iso_date):
    """处理日效率的更新。"""
    try:
        log_date = date.fromisoformat(iso_date)
        efficiency = request.form['efficiency']

        # --- MODIFIED: 显式地查询-更新或创建，而不是依赖 merge ---
        daily_data = DailyData.query.filter_by(log_date=log_date, user_id=current_user.id).first()
        if daily_data:
            daily_data.efficiency = efficiency
        else:
            daily_data = DailyData(log_date=log_date, efficiency=efficiency, user_id=current_user.id)
            db.session.add(daily_data)

        db.session.commit()

        if request.headers.get('X-Requested-with') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{log_date.strftime("%Y-%m-%d")} 的效率已更新！'})
        flash(f'{log_date.strftime("%Y-%m-%d")} 的效率已更新！', 'success')
        return redirect(url_for('records.list_records'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新日期 {iso_date} 效率时出错: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'发生错误: {e}'}), 400
        flash(f'发生错误: {e}', 'error')
        return redirect(url_for('records.list_records'))


# --- 数据导入/导出 ---
@records_bp.route('/export/json')
@login_required
def export_json():
    """将当前用户的所有数据导出为 JSON 文件。"""

    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    # --- MODIFIED: 所有查询都只针对当前用户 ---
    all_data = {
        'settings': [s.to_dict() for s in Setting.query.filter_by(user_id=current_user.id).all()],
        'weekly_data': [w.to_dict() for w in WeeklyData.query.filter_by(user_id=current_user.id).all()],
        'daily_data': [d.to_dict() for d in DailyData.query.filter_by(user_id=current_user.id).all()],
        'log_entries': [l.to_dict() for l in LogEntry.query.filter_by(user_id=current_user.id).all()],
        'countdown_events': [c.to_dict() for c in CountdownEvent.query.filter_by(user_id=current_user.id).all()],
    }
    json_output = json.dumps(all_data, default=json_serializer, indent=4, ensure_ascii=False)
    # --- MODIFIED: 文件名包含用户名 ---
    filename = f"{current_user.username}_backup_{date.today().isoformat()}.json"
    return Response(json_output, mimetype="application/json",
                    headers={"Content-Disposition": f"attachment;filename={filename}"})


@records_bp.route('/import/json', methods=['POST'])
@login_required
def import_json():
    """
    从 JSON 文件为当前用户导入数据。
    会先清空该用户的旧数据，然后导入新数据。
    """
    file = request.files.get('file')
    if not file or not file.filename.endswith('.json'):
        flash('请选择一个有效的 .json 备份文件。', 'error')
        return redirect(url_for('main.settings'))

    try:
        # --- MODIFIED: 事务性地清空当前用户的旧数据 ---
        LogEntry.query.filter_by(user_id=current_user.id).delete()
        DailyData.query.filter_by(user_id=current_user.id).delete()
        WeeklyData.query.filter_by(user_id=current_user.id).delete()
        CountdownEvent.query.filter_by(user_id=current_user.id).delete()
        Setting.query.filter_by(user_id=current_user.id).delete()

        # 解析并加载新数据
        data = json.load(file.stream)
        model_map = {
            'settings': Setting, 'countdown_events': CountdownEvent,
            'weekly_data': WeeklyData, 'daily_data': DailyData, 'log_entries': LogEntry,
        }

        date_fields = {'log_date'}
        datetime_fields = {'target_datetime_utc'}

        for key, model in model_map.items():
            if key in data:
                for item in data[key]:
                    # 自动处理日期和时间字符串的转换
                    for field in date_fields:
                        if field in item and isinstance(item[field], str): item[field] = date.fromisoformat(item[field])
                    for field in datetime_fields:
                        if field in item and isinstance(item[field], str): item[field] = datetime.fromisoformat(
                            item[field].replace('Z', '+00:00'))

                    # --- MODIFIED: 为每一条导入的记录强制设置当前 user_id ---
                    item['user_id'] = current_user.id
                    # 移除可能存在的旧 id，让数据库自动生成
                    item.pop('id', None)

                    # --- HOTFIX: 修正此处的逻辑 ---
                    # 对于 Setting 模型，它的主键是 (key, user_id) 复合主键。
                    # 'key' 是必须的，不能移除。
                    # if model == Setting:
                    #     item.pop('key', None) # <--- 这行是错误的，已移除

                    db.session.add(model(**item))

        db.session.commit()
        flash('数据恢复成功！您的所有数据已从备份文件加载。', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"为用户 {current_user.id} 导入JSON时出错: {e}")
        flash(f'导入过程中发生严重错误，操作已回滚: {e}', 'error')
        return redirect(url_for('main.settings'))
