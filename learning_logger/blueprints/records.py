# learning_logger/blueprints/records.py

from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, Response, jsonify, current_app, session)
from flask_login import login_required, current_user

from ..services import record_service, data_service
from ..models import Stage, Category, SubCategory
# 新增: 导入 DataImportForm
from ..forms import DataImportForm

records_bp = Blueprint('records', __name__)


def _get_category_data_for_form():
    # ... (此函数内容不变) ...
    """Helper to fetch and structure category data for the form."""
    all_categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    all_subcategories = {}
    for cat in all_categories:
        all_subcategories[cat.id] = [{'id': sub.id, 'name': sub.name} for sub in
                                     cat.subcategories.order_by(SubCategory.name).all()]
    return all_categories, all_subcategories


@records_bp.route('/')
@login_required
def list_records():
    # ... (此函数内容不变) ...
    all_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    active_stage = None
    stage_id = request.args.get('stage_id', type=int)
    if stage_id:
        active_stage = next((s for s in all_stages if s.id == stage_id), None)
        if active_stage:
            session['active_stage_id'] = active_stage.id
        else:
            flash('指定的阶段不存在。', 'error')
            return redirect(url_for('records.list_records'))
    else:
        active_stage_id = session.get('active_stage_id')
        if active_stage_id: active_stage = next((s for s in all_stages if s.id == active_stage_id), None)
        if not active_stage and all_stages:
            active_stage = all_stages[0]
            session['active_stage_id'] = active_stage.id
    if not active_stage:
        flash('欢迎使用！请先创建一个新的学习阶段以开始记录。', 'info')
        return redirect(url_for('main.settings_content'))

    sort_order = request.args.get('sort', 'desc')
    structured_logs = record_service.get_structured_logs_for_stage(active_stage, sort_order)

    for week in structured_logs:
        for day in week['days']:
            total_duration_for_day = sum(log.actual_duration for log in day['logs'] if log.actual_duration)
            day['total_duration'] = total_duration_for_day

    return render_template('index.html', structured_logs=structured_logs, current_sort=sort_order,
                           all_stages=all_stages, active_stage=active_stage)


@records_bp.route('/form/add')
@login_required
def get_add_form():
    # ... (此函数内容不变) ...
    active_stage_id = session.get('active_stage_id')
    if not active_stage_id:
        return jsonify({'success': False, 'message': '请先选择一个有效的学习阶段。'})

    default_date_str = request.args.get('default_date')
    default_date_obj = date.fromisoformat(default_date_str) if default_date_str else date.today()

    all_categories, all_subcategories = _get_category_data_for_form()

    return render_template('_form_record.html', log=None, default_date=default_date_obj,
                           action_url=url_for('records.add'),
                           submit_button_text='添加记录', all_categories=all_categories,
                           all_subcategories=all_subcategories)


@records_bp.route('/form/edit/<int:log_id>')
@login_required
def get_edit_form(log_id):
    # ... (此函数内容不变) ...
    log = record_service.get_log_entry_for_user(log_id, current_user)
    if not log:
        return jsonify({'success': False, 'message': '记录不存在或无权访问。'})
    all_categories, all_subcategories = _get_category_data_for_form()
    return render_template('_form_record.html', log=log, default_date=log.log_date,
                           action_url=url_for('records.edit', log_id=log.id), submit_button_text='更新记录',
                           all_categories=all_categories, all_subcategories=all_subcategories)


@records_bp.route('/add', methods=['POST'])
@login_required
def add():
    # ... (此函数内容不变) ...
    active_stage_id = session.get('active_stage_id')
    if not active_stage_id:
        return jsonify({'success': False, 'message': '无法添加记录，未找到当前活动阶段。'}), 400
    success, message = record_service.add_log_for_stage(active_stage_id, current_user, request.form)
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        current_app.logger.error(f"为阶段 {active_stage_id} 添加记录时: {message}")
        return jsonify({'success': False, 'message': message}), 400


@records_bp.route('/edit/<int:log_id>', methods=['POST'])
@login_required
def edit(log_id):
    # ... (此函数内容不变) ...
    success, message = record_service.update_log_for_user(log_id, current_user, request.form)
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        current_app.logger.error(f"为用户 {current_user.id} 编辑记录 {log_id} 时: {message}")
        return jsonify({'success': False, 'message': message}), 400


@records_bp.route('/delete/<int:log_id>', methods=['POST'])
@login_required
def delete(log_id):
    # ... (此函数内容不变) ...
    success, message = record_service.delete_log_for_user(log_id, current_user)
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        current_app.logger.error(f"为用户 {current_user.id} 删除记录 {log_id} 时: {message}")
        return jsonify({'success': False, 'message': message}), 400


@records_bp.route('/export/zip')
@login_required
def export_zip():
    # ... (此函数内容不变) ...
    zip_buffer = data_service.export_data_for_user(current_user)
    username = current_user.username.replace(" ", "_")
    filename = f"{username}_backup_{date.today().isoformat()}.zip"
    return Response(
        zip_buffer,
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@records_bp.route('/import/zip', methods=['POST'])
@login_required
def import_zip():
    # 修改: 使用 DataImportForm 来验证提交
    form = DataImportForm()
    if form.validate_on_submit():
        # 验证通过，从表单对象中获取文件
        file_storage = form.file.data
        success, message = data_service.import_data_for_user(current_user, file_storage.stream)

        if success:
            current_app.logger.info("Import successful. Triggering efficiency recalculation for all stages.")
            all_user_stages = Stage.query.filter_by(user_id=current_user.id).all()
            for stage in all_user_stages:
                record_service.recalculate_efficiency_for_stage(stage)
            current_app.logger.info("Efficiency recalculation finished.")
            flash(message, 'success')
            return redirect(url_for('records.list_records'))
        else:
            current_app.logger.error(f"Import failed for user {current_user.id}: {message}")
            flash(message, 'error')
            return redirect(url_for('main.settings_data'))
    else:
        # 验证失败，闪现表单中的错误信息
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
        return redirect(url_for('main.settings_data'))