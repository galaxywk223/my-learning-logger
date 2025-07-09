# learning_logger/blueprints/milestone.py (MODIFIED FOR BEAUTIFICATION AND SECURITY)

import os
import bleach  # <-- NEW: Import the bleach library
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app, send_from_directory)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import date, datetime

from .. import db
from ..models import Milestone, MilestoneCategory, MilestoneAttachment

milestone_bp = Blueprint('milestone', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# --- NEW: Define allowed HTML tags for the description ---
ALLOWED_TAGS = ['p', 'b', 'i', 'em', 'strong', 'ul', 'ol', 'li', 'br']


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# Milestone Main Routes
# ============================================================================

@milestone_bp.route('/')
@login_required
def list_milestones():
    """显示成就时刻时间线主页面。"""
    page = request.args.get('page', 1, type=int)
    categories = MilestoneCategory.query.filter_by(user_id=current_user.id).order_by(MilestoneCategory.name).all()
    selected_category_id = request.args.get('category_id', type=int)

    query = Milestone.query.filter_by(user_id=current_user.id)
    if selected_category_id:
        query = query.filter_by(category_id=selected_category_id)

    milestones_pagination = query.order_by(Milestone.event_date.desc(), Milestone.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template(
        'milestones.html',
        pagination=milestones_pagination,
        categories=categories,
        selected_category_id=selected_category_id
    )


@milestone_bp.route('/add', methods=['POST'])
@login_required
def add_milestone():
    """处理添加新成就的请求。"""
    if 'MILESTONE_UPLOADS' not in current_app.config or not current_app.config['MILESTONE_UPLOADS']:
        flash('文件上传路径未配置，无法添加附件。', 'error')
        return redirect(url_for('milestone.list_milestones'))

    try:
        title = request.form.get('title')
        event_date_str = request.form.get('event_date')

        # --- MODIFIED: Sanitize the description using bleach ---
        raw_description = request.form.get('description')
        description = bleach.clean(raw_description, tags=ALLOWED_TAGS) if raw_description else None

        category_id = request.form.get('category_id', type=int)

        if not title or not event_date_str:
            flash('标题和事件日期是必填项。', 'error')
            return redirect(url_for('milestone.list_milestones'))

        event_date = date.fromisoformat(event_date_str)

        new_milestone = Milestone(
            title=title,
            event_date=event_date,
            description=description,
            category_id=category_id if category_id else None,
            user_id=current_user.id
        )
        db.session.add(new_milestone)
        db.session.flush()

        files = request.files.getlist('attachments')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                user_upload_folder = os.path.join(current_app.config['MILESTONE_UPLOADS'], str(current_user.id))
                os.makedirs(user_upload_folder, exist_ok=True)
                unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
                file_path = os.path.join(user_upload_folder, unique_filename)
                file.save(file_path)
                relative_path = os.path.join(str(current_user.id), unique_filename)
                attachment = MilestoneAttachment(
                    milestone_id=new_milestone.id,
                    file_path=relative_path,
                    original_filename=filename
                )
                db.session.add(attachment)

        db.session.commit()
        flash('新的成就时刻已成功记录！', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding milestone: {e}")
        flash(f'添加成就时发生错误: {str(e)}', 'error')

    return redirect(url_for('milestone.list_milestones'))


@milestone_bp.route('/edit/<int:milestone_id>', methods=['POST'])
@login_required
def edit_milestone(milestone_id):
    """处理编辑成就的请求。"""
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first_or_404()

    try:
        milestone.title = request.form.get('title')
        milestone.event_date = date.fromisoformat(request.form.get('event_date'))

        # --- MODIFIED: Sanitize the description using bleach ---
        raw_description = request.form.get('description')
        milestone.description = bleach.clean(raw_description, tags=ALLOWED_TAGS) if raw_description else None

        category_id = request.form.get('category_id', type=int)
        milestone.category_id = category_id if category_id else None

        db.session.commit()
        flash('成就时刻已更新。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing milestone {milestone_id}: {e}")
        flash(f'编辑成就时发生错误: {str(e)}', 'error')

    return redirect(url_for('milestone.list_milestones'))


# ... (The rest of the file remains unchanged) ...

@milestone_bp.route('/delete/<int:milestone_id>', methods=['POST'])
@login_required
def delete_milestone(milestone_id):
    milestone = Milestone.query.filter_by(id=milestone_id, user_id=current_user.id).first_or_404()
    try:
        for attachment in milestone.attachments:
            if current_app.config.get('MILESTONE_UPLOADS'):
                full_path = os.path.join(current_app.config['MILESTONE_UPLOADS'], attachment.file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
        db.session.delete(milestone)
        db.session.commit()
        flash(f'成就 “{milestone.title}” 已被永久删除。', 'info')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting milestone {milestone_id}: {e}")
        flash(f'删除成就时发生错误: {str(e)}', 'error')
    return redirect(url_for('milestone.list_milestones'))


@milestone_bp.route('/attachments/<path:filepath>')
@login_required
def get_attachment(filepath):
    user_id_from_path = filepath.split(os.path.sep)[0]
    if str(current_user.id) != user_id_from_path:
        return "Forbidden", 403
    upload_dir = current_app.config.get('MILESTONE_UPLOADS')
    if not upload_dir:
        return "File storage not configured", 500
    return send_from_directory(upload_dir, filepath, as_attachment=True)


@milestone_bp.route('/categories')
@login_required
def manage_categories():
    categories = MilestoneCategory.query.filter_by(user_id=current_user.id).order_by(MilestoneCategory.name).all()
    return render_template('milestone_category_management.html', categories=categories)


@milestone_bp.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if name and name.strip():
        new_category = MilestoneCategory(name=name, user_id=current_user.id)
        db.session.add(new_category)
        db.session.commit()
        flash(f'新分类 “{name}” 已添加。', 'success')
    else:
        flash('分类名称不能为空。', 'error')
    return redirect(url_for('milestone.manage_categories'))


@milestone_bp.route('/categories/edit/<int:category_id>', methods=['POST'])
@login_required
def edit_category(category_id):
    category = MilestoneCategory.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    name = request.form.get('name')
    if name and name.strip():
        category.name = name
        db.session.commit()
        flash('分类已更新。', 'success')
    else:
        flash('分类名称不能为空。', 'error')
    return redirect(url_for('milestone.manage_categories'))


@milestone_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = MilestoneCategory.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    if category.milestones.count() > 0:
        flash(f'无法删除分类 “{category.name}”，因为它已关联了成就记录。请先将相关记录的分类修改或移除。', 'error')
    else:
        db.session.delete(category)
        db.session.commit()
        flash(f'分类 “{category.name}” 已删除。', 'info')
    return redirect(url_for('milestone.manage_categories'))