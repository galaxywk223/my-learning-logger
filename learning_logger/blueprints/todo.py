# 文件路径: learning_logger/blueprints/todo.py
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify)
from flask_login import login_required, current_user
from datetime import datetime, date

from .. import db
from ..models import Todo

todo_bp = Blueprint('todo', __name__, url_prefix='/todo')


@todo_bp.route('/')
@login_required
def list_todos():
    """显示待办事项主页面，区分待办和已完成。"""

    pending_todos = Todo.query.filter_by(user_id=current_user.id, is_completed=False).order_by(
        Todo.priority.desc(), Todo.due_date.asc()
    ).all()

    completed_todos = Todo.query.filter_by(user_id=current_user.id, is_completed=True).order_by(
        Todo.completed_at.desc()
    ).all()

    today = date.today()
    for todo in pending_todos:
        if todo.due_date and todo.due_date < today:
            todo.is_overdue = True
        else:
            todo.is_overdue = False

    return render_template('todo.html', pending_todos=pending_todos, completed_todos=completed_todos)


@todo_bp.route('/add', methods=['POST'])
@login_required
def add_todo():
    """处理添加新待办事项的请求。"""
    content = request.form.get('content')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', 2, type=int)

    if not content or not content.strip():
        flash('待办内容不能为空。', 'error')
        return redirect(url_for('todo.list_todos'))

    due_date = date.fromisoformat(due_date_str) if due_date_str else None

    new_todo = Todo(
        content=content,
        due_date=due_date,
        priority=priority,
        user_id=current_user.id
    )
    db.session.add(new_todo)
    db.session.commit()
    flash('新的待办事项已添加。', 'success')
    return redirect(url_for('todo.list_todos'))


@todo_bp.route('/toggle/<int:todo_id>', methods=['POST'])
@login_required
def toggle_todo(todo_id):
    """切换待办事项的完成状态。"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    todo.is_completed = not todo.is_completed
    if todo.is_completed:
        todo.completed_at = datetime.utcnow()
    else:
        todo.completed_at = None

    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'is_completed': todo.is_completed})

    flash('任务状态已更新。', 'info')
    return redirect(url_for('todo.list_todos'))


@todo_bp.route('/edit/<int:todo_id>', methods=['POST'])
@login_required
def edit_todo(todo_id):
    """处理编辑待办事项的请求。"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    content = request.form.get('content')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', type=int)

    if not content or not content.strip():
        flash('待办内容不能为空。', 'error')
    else:
        todo.content = content
        todo.due_date = date.fromisoformat(due_date_str) if due_date_str else None
        todo.priority = priority
        db.session.commit()
        flash('待办事项已更新。', 'success')

    return redirect(url_for('todo.list_todos'))


@todo_bp.route('/delete/<int:todo_id>', methods=['POST'])
@login_required
def delete_todo(todo_id):
    """处理删除待办事项的请求。"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    db.session.delete(todo)
    db.session.commit()
    flash('待办事项已删除。', 'info')
    return redirect(url_for('todo.list_todos'))
