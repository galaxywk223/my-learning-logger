# learning_logger/blueprints/records.py (导入/导出功能重构后)

from datetime import date, datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, Response, jsonify, current_app)
from flask_login import login_required, current_user

from .. import db
# --- 新增: 导入两个服务 ---
from ..services import record_service, data_service
from ..models import Setting, WeeklyData, DailyData, LogEntry

# 注意：此文件中不再直接使用 CountdownEvent 和 get_custom_week_info
# 但为了避免潜在的依赖问题，暂时保留

records_bp = Blueprint('records', __name__, url_prefix='/records')


# --- CRUD 和列表路由 (无变化) ---

@records_bp.route('/')
@login_required
def list_records():
    sort_order = request.args.get('sort', 'desc')
    structured_logs, setup_needed = record_service.get_structured_logs_for_user(current_user, sort_order)
    if setup_needed:
        flash('请首先在设置页面中指定每周的起始日期。', 'warning')
        return render_template('index.html', setup_needed=True, structured_logs=[], current_sort=sort_order)
    return render_template('index.html', structured_logs=structured_logs, current_sort=sort_order, setup_needed=False)


@records_bp.route('/form/add')
@login_required
def get_add_form():
    return render_template('_form_record.html', log=None, default_date=date.today(), action_url=url_for('records.add'),
                           submit_button_text='添加记录')


@records_bp.route('/form/edit/<int:log_id>')
@login_required
def get_edit_form(log_id):
    log = LogEntry.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    return render_template('_form_record.html', log=log, default_date=log.log_date,
                           action_url=url_for('records.edit', log_id=log.id), submit_button_text='更新记录')


@records_bp.route('/form/edit_week/<int:year>/<int:week_num>')
@login_required
def get_edit_week_form(year, week_num):
    weekly_data = WeeklyData.query.filter_by(year=year, week_num=week_num, user_id=current_user.id).first()
    return render_template('_form_edit_week.html', year=year, week_num=week_num, weekly_data=weekly_data)


@records_bp.route('/form/edit_day/<iso_date>')
@login_required
def get_edit_day_form(iso_date):
    log_date = date.fromisoformat(iso_date)
    daily_data = DailyData.query.filter_by(log_date=log_date, user_id=current_user.id).first()
    return render_template('_form_edit_day.html', log_date=log_date, daily_data=daily_data)


@records_bp.route('/add', methods=['POST'])
@login_required
def add():
    success, message = record_service.add_log_for_user(current_user, request.form)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'success')
    else:
        current_app.logger.error(f"为用户 {current_user.id} 添加记录时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/edit/<int:log_id>', methods=['POST'])
@login_required
def edit(log_id):
    success, message = record_service.update_log_for_user(log_id, current_user, request.form)
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
    success, message = record_service.delete_log_for_user(log_id, current_user)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'info')
    else:
        current_app.logger.error(f"为用户 {current_user.id} 删除记录 {log_id} 时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/edit_week/<int:year>/<int:week_num>', methods=['POST'])
@login_required
def edit_week(year, week_num):
    efficiency = request.form.get('efficiency')
    success, message = record_service.update_weekly_efficiency_for_user(current_user, year, week_num, efficiency)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify({'success': True, 'message': message})
        flash(message, 'success')
    else:
        current_app.logger.error(f"更新周 {year}-{week_num} 效率时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


@records_bp.route('/edit_day/<iso_date>', methods=['POST'])
@login_required
def edit_day(iso_date):
    efficiency = request.form.get('efficiency')
    success, message = record_service.update_daily_efficiency_for_user(current_user, iso_date, efficiency)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if success:
        if is_ajax: return jsonify(
            {'success': True, 'message': f'{date.fromisoformat(iso_date).strftime("%Y-%m-%d")} 的效率已更新！'})
        flash(message, 'success')
    else:
        current_app.logger.error(f"更新日期 {iso_date} 效率时: {message}")
        if is_ajax: return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
    return redirect(url_for('records.list_records'))


# --- 数据导入/导出 (已重构) ---

@records_bp.route('/export/json')
@login_required
def export_json():
    """将当前用户的所有数据导出为 JSON 文件，调用服务层。"""
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
    """从 JSON 文件为当前用户导入数据，调用服务层。"""
    file = request.files.get('file')

    if not file or not file.filename.endswith('.json'):
        flash('请选择一个有效的 .json 备份文件。', 'error')
        # 导入功能通常在设置页面，重定向到那里更合适
        return redirect(url_for('main.settings'))

    success, message = data_service.import_data_for_user(current_user, file.stream)

    if success:
        flash(message, 'success')
        # 导入成功后，最好跳转到主页以查看新数据
        return redirect(url_for('main.index'))
    else:
        current_app.logger.error(message)
        flash(message, 'error')
        return redirect(url_for('main.settings'))