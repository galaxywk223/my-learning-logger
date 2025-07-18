# learning_logger/blueprints/category.py (REVISED)

from flask import (Blueprint, request, redirect, url_for,
                   flash, render_template)
from flask_login import login_required, current_user
from .. import db
from ..models import Category, SubCategory

category_management_bp = Blueprint('category_management', __name__, url_prefix='/categories')


@category_management_bp.route('/')
@login_required
def manage_categories():
    """Renders the main category management page."""
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return render_template('category_management.html', categories=categories)


@category_management_bp.route('/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if not name or not name.strip():
        flash('分类名称不能为空。', 'error')
    else:
        new_category = Category(name=name, user_id=current_user.id)
        db.session.add(new_category)
        db.session.commit()
        flash(f'分类 "{name}" 已成功添加！', 'success')
    return redirect(url_for('category_management.manage_categories'))


@category_management_bp.route('/edit/<int:category_id>', methods=['POST'])
@login_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    name = request.form.get('name')
    if not name or not name.strip():
        flash('分类名称不能为空。', 'error')
    else:
        category.name = name
        db.session.commit()
        flash('分类已更新。', 'success')
    return redirect(url_for('category_management.manage_categories'))


@category_management_bp.route('/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    if category.subcategories.count() > 0:
        flash('无法删除，请先移除此分类下的所有标签。', 'error')
    else:
        db.session.delete(category)
        db.session.commit()
        flash(f'分类 “{category.name}” 已删除。', 'info')
    return redirect(url_for('category_management.manage_categories'))


@category_management_bp.route('/subcategory/add', methods=['POST'])
@login_required
def add_subcategory():
    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)

    # MODIFIED: Simplified the validation logic.
    # We can trust that category_id is provided correctly by the hidden input in our new form.
    if not name or not name.strip():
        flash('标签名称不能为空。', 'error')
    else:
        # We still check if the category belongs to the current user for security.
        parent_category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not parent_category:
            flash('无效的分类或无权操作。', 'error')
        else:
            new_subcategory = SubCategory(name=name, category_id=category_id)
            db.session.add(new_subcategory)
            db.session.commit()
            flash(f'标签 “{name}” 已成功添加到 “{parent_category.name}”！', 'success')

    return redirect(url_for('category_management.manage_categories'))


@category_management_bp.route('/subcategory/edit/<int:subcategory_id>', methods=['POST'])
@login_required
def edit_subcategory(subcategory_id):
    subcategory = SubCategory.query.get_or_404(subcategory_id)
    if subcategory.category.user_id != current_user.id:
        flash('无权操作。', 'error')
        return redirect(url_for('category_management.manage_categories'))

    name = request.form.get('name')
    category_id = request.form.get('category_id', type=int)

    if not name or not name.strip() or not category_id:
        flash('标签名称和所属分类都不能为空。', 'error')
    else:
        new_parent_category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not new_parent_category:
            flash('无效的分类选择。', 'error')
        else:
            subcategory.name = name
            subcategory.category_id = category_id
            db.session.commit()
            flash('标签已更新。', 'success')
    return redirect(url_for('category_management.manage_categories'))


@category_management_bp.route('/subcategory/delete/<int:subcategory_id>', methods=['POST'])
@login_required
def delete_subcategory(subcategory_id):
    subcategory = SubCategory.query.get_or_404(subcategory_id)
    if subcategory.category.user_id != current_user.id:
        flash('无权操作。', 'error')
        return redirect(url_for('category_management.manage_categories'))

    if subcategory.log_entries.count() > 0:
        flash(f'无法删除标签 “{subcategory.name}”，因为它已关联了学习记录。', 'error')
    else:
        db.session.delete(subcategory)
        db.session.commit()
        flash(f'标签 “{subcategory.name}” 已删除。', 'info')
    return redirect(url_for('category_management.manage_categories'))