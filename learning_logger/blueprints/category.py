# learning_logger/blueprints/category.py

from flask import (Blueprint, request, redirect, url_for,
                   flash)
from flask_login import login_required, current_user
from .. import db
from ..models import Category, SubCategory

category_bp = Blueprint('category', __name__)


# --- REMOVED: management() view function is no longer needed ---


# --- 大分类 (Category) 操作 ---

@category_bp.route('/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if not name or not name.strip():
        flash('大分类名称不能为空。', 'error')
    else:
        new_category = Category(name=name, user_id=current_user.id)
        db.session.add(new_category)
        db.session.commit()
        flash(f'大分类 “{name}” 已成功添加！', 'success')
    # MODIFIED: Redirect to the settings page, category tab
    return redirect(url_for('main.settings_content') + '#headingCategories')


@category_bp.route('/category/edit/<int:category_id>', methods=['POST'])
@login_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    name = request.form.get('name')
    if not name or not name.strip():
        flash('大分类名称不能为空。', 'error')
    else:
        category.name = name
        db.session.commit()
        flash('大分类已更新。', 'success')
    # MODIFIED: Redirect to the settings page, category tab
    return redirect(url_for('main.settings_content') + '#headingCategories')


@category_bp.route('/category/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    # 检查是否有子分类关联
    if category.subcategories.count() > 0:
        flash('无法删除，请先移除或删除此大分类下的所有小分类。', 'error')
    else:
        db.session.delete(category)
        db.session.commit()
        flash(f'大分类 “{category.name}” 已删除。', 'info')
    # MODIFIED: Redirect to the settings page, category tab
    return redirect(url_for('main.settings_content') + '#headingCategories')


# --- 小分类 (SubCategory) 操作 ---

@category_bp.route('/subcategory/add', methods=['POST'])
@login_required
def add_subcategory():
    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)

    if not name or not name.strip() or not category_id:
        flash('小分类名称和所属大分类均不能为空。', 'error')
    else:
        # 确保所选的大分类属于当前用户
        parent_category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not parent_category:
            flash('无效的大分类选择。', 'error')
        else:
            new_subcategory = SubCategory(name=name, category_id=category_id)
            db.session.add(new_subcategory)
            db.session.commit()
            flash(f'小分类 “{name}” 已成功添加到 “{parent_category.name}”！', 'success')
    # MODIFIED: Redirect to the settings page, category tab
    return redirect(url_for('main.settings_content') + '#headingCategories')


@category_bp.route('/subcategory/edit/<int:subcategory_id>', methods=['POST'])
@login_required
def edit_subcategory(subcategory_id):
    subcategory = SubCategory.query.get_or_404(subcategory_id)
    # 通过 subcategory.category 访问父分类，并验证用户权限
    if subcategory.category.user_id != current_user.id:
        return "Unauthorized", 403

    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)

    if not name or not name.strip() or not category_id:
        flash('小分类名称和所属大分类均不能为空。', 'error')
    else:
        # 确保新选择的大分类也属于当前用户
        new_parent_category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not new_parent_category:
            flash('无效的大分类选择。', 'error')
        else:
            subcategory.name = name
            subcategory.category_id = category_id  # 实现移动到新的大分类
            db.session.commit()
            flash('小分类已更新。', 'success')

    # MODIFIED: Redirect to the settings page, category tab
    return redirect(url_for('main.settings_content') + '#headingCategories')


@category_bp.route('/subcategory/delete/<int:subcategory_id>', methods=['POST'])
@login_required
def delete_subcategory(subcategory_id):
    subcategory = SubCategory.query.get_or_404(subcategory_id)
    if subcategory.category.user_id != current_user.id:
        return "Unauthorized", 403

    # 检查是否有日志条目关联
    if subcategory.log_entries.count() > 0:
        flash(f'无法删除小分类 “{subcategory.name}”，因为它已关联了学习记录。请先将相关记录的分类修改或移除。', 'error')
    else:
        db.session.delete(subcategory)
        db.session.commit()
        flash(f'小分类 “{subcategory.name}” 已删除。', 'info')

    # MODIFIED: Redirect to the settings page, category tab
    return redirect(url_for('main.settings_content') + '#headingCategories')