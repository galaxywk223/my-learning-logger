# 文件路径: learning_logger/blueprints/daily_plan.py
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app)
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, datetime

from .. import db
from ..models import DailyPlanItem

daily_plan_bp = Blueprint('daily_plan', __name__)


@daily_plan_bp.route('/', methods=['GET'])
@login_required
def view_plan():
    """显示指定日期的每日计划页面。"""

    date_str = request.args.get('plan_date', default=date.today().isoformat())
    try:
        selected_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        selected_date = date.today()

    plan_items_query = DailyPlanItem.query.filter_by(
        user_id=current_user.id,
        plan_date=selected_date
    ).order_by(DailyPlanItem.id.asc())

    morning_items = plan_items_query.filter(DailyPlanItem.time_slot == '上午').all()
    afternoon_items = plan_items_query.filter(DailyPlanItem.time_slot == '下午').all()
    evening_items = plan_items_query.filter(DailyPlanItem.time_slot == '晚上').all()
    other_items = plan_items_query.filter(
        (DailyPlanItem.time_slot == None) |
        (DailyPlanItem.time_slot.notin_(['上午', '下午', '晚上']))
    ).all()

    total_count = len(morning_items) + len(afternoon_items) + len(evening_items) + len(other_items)
    completed_count = sum(
        1 for item in morning_items + afternoon_items + evening_items + other_items if item.is_completed)

    return render_template(
        'daily_plan.html',
        selected_date=selected_date,
        morning_items=morning_items,
        afternoon_items=afternoon_items,
        evening_items=evening_items,
        other_items=other_items,
        total_count=total_count,
        completed_count=completed_count
    )


@daily_plan_bp.route('/add', methods=['POST'])
@login_required
def add_item():
    """处理添加新计划项的请求。"""
    content = request.form.get('content')
    plan_date_str = request.form.get('plan_date')
    time_slot = request.form.get('time_slot')

    if not content or not content.strip() or not plan_date_str:
        flash('计划内容和日期不能为空。', 'error')
    else:
        try:
            plan_date = date.fromisoformat(plan_date_str)
            new_item = DailyPlanItem(
                content=content,
                plan_date=plan_date,
                time_slot=time_slot,
                user_id=current_user.id
            )
            db.session.add(new_item)
            db.session.commit()
            flash('新的计划已添加。', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"添加每日计划时出错: {e}")
            flash('添加计划时发生错误。', 'error')

    return redirect(url_for('daily_plan.view_plan', plan_date=plan_date_str))


@daily_plan_bp.route('/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(item_id):
    """切换计划项的完成状态。"""
    item = DailyPlanItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item.is_completed = not item.is_completed
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'is_completed': item.is_completed,
            'message': '状态已更新'
        })

    flash('计划状态已更新。', 'info')
    return redirect(url_for('daily_plan.view_plan', plan_date=item.plan_date.isoformat()))


@daily_plan_bp.route('/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """处理删除计划项的请求。"""
    item = DailyPlanItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    plan_date_str = item.plan_date.isoformat()
    db.session.delete(item)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': '计划已删除'})

    flash('计划项已删除。', 'info')
    return redirect(url_for('daily_plan.view_plan', plan_date=plan_date_str))


@daily_plan_bp.route('/update/<int:item_id>', methods=['POST'])
@login_required
def update_item(item_id):
    """处理更新计划项内容的请求。"""
    item = DailyPlanItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    new_content = request.form.get('content')
    if new_content and new_content.strip():
        item.content = new_content
        db.session.commit()
        return jsonify({'success': True, 'message': '计划已更新'})
    return jsonify({'success': False, 'message': '内容不能为空'}), 400
