# learning_logger/blueprints/main.py

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, session)
from flask_login import login_required, current_user
from datetime import date

from .. import db
from ..models import Stage, Setting, CountdownEvent, LogEntry, DailyData, WeeklyData

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """新的主页，作为功能导航仪表盘。"""
    return render_template('dashboard.html')

@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """处理应用设置，并新增了阶段管理功能。"""
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    all_settings = Setting.query.filter_by(user_id=current_user.id).all()
    settings_dict = {setting.key: setting.value for setting in all_settings}
    return render_template('settings.html', settings=settings_dict, user_stages=user_stages)

# ============================================================================
# 阶段管理的路由
# ============================================================================

@main_bp.route('/stages/add', methods=['POST'])
@login_required
def add_stage():
    """处理添加新阶段的请求。"""
    name = request.form.get('name')
    start_date_str = request.form.get('start_date')
    if not name or not start_date_str:
        flash('阶段名称和起始日期均不能为空。', 'error')
        return redirect(url_for('main.settings'))
    try:
        start_date = date.fromisoformat(start_date_str)
        new_stage = Stage(name=name, start_date=start_date, user_id=current_user.id)
        db.session.add(new_stage)
        db.session.commit()
        flash(f'新阶段 "{name}" 已成功创建！', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创建阶段时出错: {e}")
        flash('创建阶段时发生错误。', 'error')
    return redirect(url_for('main.settings'))

@main_bp.route('/stages/edit/<int:stage_id>', methods=['POST'])
@login_required
def edit_stage(stage_id):
    """处理编辑阶段名称的请求。"""
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    new_name = request.form.get('name')
    if not new_name:
        flash('阶段名称不能为空。', 'error')
        return redirect(url_for('main.settings'))
    try:
        stage.name = new_name
        db.session.commit()
        flash('阶段名称已更新。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"编辑阶段 {stage_id} 时出错: {e}")
        flash('更新阶段名称时发生错误。', 'error')
    return redirect(url_for('main.settings'))

@main_bp.route('/stages/delete/<int:stage_id>', methods=['POST'])
@login_required
def delete_stage(stage_id):
    """处理删除阶段的请求。"""
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(stage)
        db.session.commit()
        flash(f'阶段 "{stage.name}" 及其所有相关记录已被永久删除。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除阶段 {stage_id} 时出错: {e}")
        flash('删除阶段时发生错误。', 'error')
    return redirect(url_for('main.settings'))

@main_bp.route('/stages/apply/<int:stage_id>', methods=['POST'])
@login_required
def apply_stage(stage_id):
    """处理应用（切换）阶段的请求。"""
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    session['active_stage_id'] = stage.id
    flash(f'已切换到阶段：“{stage.name}”', 'success')
    return redirect(url_for('records.list_records'))

# ============================================================================
# 数据清理路由
# ============================================================================

@main_bp.route('/clear_my_data', methods=['POST'])
@login_required
def clear_my_data():
    """清空当前用户的所有数据。"""
    try:
        Stage.query.filter_by(user_id=current_user.id).delete()
        CountdownEvent.query.filter_by(user_id=current_user.id).delete()
        Setting.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('您的所有个人数据已被成功清空！', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'为用户 {current_user.id} 清空数据时出错: {e}')
        flash(f'清空数据时发生严重错误: {e}', 'error')
    return redirect(url_for('main.settings'))