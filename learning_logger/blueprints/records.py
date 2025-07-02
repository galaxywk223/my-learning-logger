# learning_logger/blueprints/records.py

from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, Response, jsonify, current_app, session)
from flask_login import login_required, current_user

from ..services import record_service, data_service
from ..models import Stage, LogEntry, WeeklyData, DailyData  # 新增导入 Stage

records_bp = Blueprint('records', __name__)  # URL prefix 将在主 __init__.py 中定义


# ============================================================================
# 主视图：阶段化改造
# ============================================================================
@records_bp.route('/')
@login_required
def list_records():
    """
    主视图，显示当前选定阶段的学习记录。
    处理阶段的选择逻辑，并获取相应数据。
    """
    # 1. 获取用户的所有阶段
    all_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()

    # 2. 确定当前要显示的活动阶段 (active_stage)
    active_stage = None
    stage_id = request.args.get('stage_id', type=int)  # 优先从 URL 参数获取

    if stage_id:
        active_stage = next((s for s in all_stages if s.id == stage_id), None)
        if active_stage:
            session['active_stage_id'] = active_stage.id  # 存入 session
        else:
            flash('指定的阶段不存在。', 'error')
            return redirect(url_for('records.list_records'))
    else:
        active_stage_id = session.get('active_stage_id')  # 其次从 session 获取
        if active_stage_id:
            active_stage = next((s for s in all_stages if s.id == active_stage_id), None)

        if not active_stage and all_stages:
            active_stage = all_stages[0]  # 默认用最新创建的
            session['active_stage_id'] = active_stage.id

    # 3. 如果没有任何阶段，提示用户创建
    if not active_stage:
        flash('欢迎使用！请先创建一个新的学习阶段以开始记录。', 'info')
        return render_template('settings.html', user_stages=[])  # 假设 settings.html 用于阶段管理

    # 4. 获取该阶段的结构化日志
    sort_order = request.args.get('sort', 'desc')
    # 注意：record_service 也需要相应修改
    structured_logs = record_service.get_structured_logs_for_stage(active_stage, sort_order)

    return render_template(
        'index.html',
        structured_logs=structured_logs,
        current_sort=sort_order,
        all_stages=all_stages,
        active_stage=active_stage
    )


# ============================================================================
# 表单获取：基本无变化，但添加/编辑的后端逻辑需要知道当前阶段
# ============================================================================

@records_bp.route('/form/add')
@login_required
def get_add_form():
    active_stage_id = session.get('active_stage_id')
    if not active_stage_id:
        flash('请先选择一个有效的学习阶段。', 'error')
        return redirect(url_for('records.list_records'))
    return render_template('_form_record.html', log=None, default_date=date.today(), action_url=url_for('records.add'),
                           submit_button_text='添加记录')


@records_bp.route('/form/edit/<int:log_id>')
@login_required
def get_edit_form(log_id):
    # 授权检查将移至 service 层，确保 log 属于当前用户的某个阶段
    log = record_service.get_log_entry_for_user(log_id, current_user)
    if not log:
        flash('记录不存在或无权访问。', 'error')
        return redirect(url_for('records.list_records'))

    return render_template('_form_record.html', log=log, default_date=log.log_date,
                           action_url=url_for('records.edit', log_id=log.id), submit_button_text='更新记录')


@records_bp.route('/form/edit_week/<int:week_id>')
@login_required
def get_edit_week_form(week_id):
    # 授权检查将移至 service 层
    weekly_data = record_service.get_weekly_data_for_user(week_id, current_user)
    if not weekly_data:
        flash('周记录不存在或无权访问。', 'error')
        return redirect(url_for('records.list_records'))

    return render_template('_form_edit_week.html', weekly_data=weekly_data)


@records_bp.route('/form/edit_day/<int:day_id>')
@login_required
def get_edit_day_form(day_id):
    # 授权检查将移至 service 层
    daily_data = record_service.get_daily_data_for_user(day_id, current_user)
    if not daily_data:
        flash('日记录不存在或无权访问。', 'error')
        return redirect(url_for('records.list_records'))

    return render_template('_form_edit_day.html', daily_data=daily_data)


# ============================================================================
# 数据操作：与当前活动阶段关联
# ============================================================================

@records_bp.route('/add', methods=['POST'])
@login_required
def add():
    active_stage_id = session.get('active_stage_id')
    if not active_stage_id:
        flash('无法添加记录，未找到当前活动阶段。', 'error')
        return redirect(url_for('records.list_records'))

    # 注意：record_service.add_log_for_user 将更新为需要 stage_id
    success, message = record_service.add_log_for_stage(active_stage_id, current_user, request.form)

    # ... AJAX 和 flash 消息处理保持不变 ...
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'success')
    else:
        current_app.logger.error(f"为阶段 {active_stage_id} 添加记录时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/edit/<int:log_id>', methods=['POST'])
@login_required
def edit(log_id):
    # 注意：record_service.update_log_for_user 会在内部处理权限验证
    success, message = record_service.update_log_for_user(log_id, current_user, request.form)
    # ... AJAX 和 flash 消息处理保持不变 ...
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'success')
    else:
        current_app.logger.error(f"为用户 {current_user.id} 编辑记录 {log_id} 时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/delete/<int:log_id>', methods=['POST'])
@login_required
def delete(log_id):
    # 注意：record_service.delete_log_for_user 会在内部处理权限验证
    success, message = record_service.delete_log_for_user(log_id, current_user)
    # ... AJAX 和 flash 消息处理保持不变 ...
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'info')
    else:
        current_app.logger.error(f"为用户 {current_user.id} 删除记录 {log_id} 时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/edit_week/<int:week_id>', methods=['POST'])
@login_required
def edit_week(week_id):
    efficiency = request.form.get('efficiency')
    # 注意：service 层方法会更新
    success, message = record_service.update_weekly_efficiency(week_id, current_user, efficiency)
    # ... AJAX 和 flash 消息处理保持不变 ...
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'success')
    else:
        current_app.logger.error(f"更新周 {week_id} 效率时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/edit_day/<int:day_id>', methods=['POST'])
@login_required
def edit_day(day_id):
    efficiency = request.form.get('efficiency')
    # 注意：service 层方法会更新
    success, message = record_service.update_daily_efficiency(day_id, current_user, efficiency)
    # ... AJAX 和 flash 消息处理保持不变 ...
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': f'效率已更新！'})
        flash(message, 'success')
    else:
        current_app.logger.error(f"更新日 {day_id} 效率时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


# ============================================================================
# 数据导入/导出: 保持不变，逻辑将在 data_service 中处理
# ============================================================================
@records_bp.route('/export/json')
@login_required
def export_json():
    json_output = data_service.export_data_for_user(current_user)
    filename = f"{current_user.username}_backup_{date.today().isoformat()}.json"
    return Response(
        json_output,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@records_bp.route('/import/json', methods=['POST'])
@login_required
def import_json():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.json'):
        flash('请选择一个有效的 .json 备份文件。', 'error')
        return redirect(url_for('main.settings'))  # 假设设置页是 main.settings

    # 注意：data_service.import_data_for_user 将重写以支持阶段
    success, message = data_service.import_data_for_user(current_user, file.stream)
    if success:
        flash(message, 'success')
        return redirect(url_for('records.list_records'))  # 导入成功后，跳转到主记录页
    else:
        current_app.logger.error(message)
        flash(message, 'error')
        return redirect(url_for('main.settings'))
