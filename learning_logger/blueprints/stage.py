# learning_logger/blueprints/stage.py (NEW FILE)

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app)
from flask_login import login_required, current_user
from datetime import date
from .. import db
from ..models import Stage

# 1. 创建一个新的蓝图
stage_bp = Blueprint('stage', __name__, url_prefix='/stages')

# 2. 创建阶段管理页面的主路由
@stage_bp.route('/')
@login_required
def manage_stages():
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    return render_template('stage_management.html', user_stages=user_stages)

# 3. 将所有与 stage 相关的路由从 main.py 移动到这里
@stage_bp.route('/add', methods=['POST'])
@login_required
def add_stage():
    name = request.form.get('name')
    start_date_str = request.form.get('start_date')
    if not name or not start_date_str:
        flash('阶段名称和起始日期均不能为空。', 'error')
    else:
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
    return redirect(url_for('stage.manage_stages'))


@stage_bp.route('/edit/<int:stage_id>', methods=['POST'])
@login_required
def edit_stage(stage_id):
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    new_name = request.form.get('name')
    if not new_name:
        flash('阶段名称不能为空。', 'error')
    else:
        try:
            stage.name = new_name
            db.session.commit()
            flash('阶段名称已更新。', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"编辑阶段 {stage_id} 时出错: {e}")
            flash('更新阶段名称时发生错误。', 'error')
    return redirect(url_for('stage.manage_stages'))


@stage_bp.route('/delete/<int:stage_id>', methods=['POST'])
@login_required
def delete_stage(stage_id):
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(stage)
        db.session.commit()
        flash(f'阶段 "{stage.name}" 及其所有相关记录已被永久删除。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除阶段 {stage_id} 时出错: {e}")
        flash('删除阶段时发生错误。', 'error')
    return redirect(url_for('stage.manage_stages'))


@stage_bp.route('/apply/<int:stage_id>', methods=['POST'])
@login_required
def apply_stage(stage_id):
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    session['active_stage_id'] = stage.id
    flash(f'已切换到阶段：“{stage.name}”', 'success')
    # 应用后跳转回记录列表页
    return redirect(url_for('records.list_records'))