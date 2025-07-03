# learning_logger/blueprints/motto.py (REDIRECTS FIXED)

import random
from flask import (Blueprint, request, redirect, url_for,
                   flash, jsonify)
from flask_login import login_required, current_user

from .. import db
from ..models import Motto

motto_bp = Blueprint('motto', __name__, url_prefix='/mottos')


@motto_bp.route('/add', methods=['POST'])
@login_required
def add_motto():
    """处理添加新格言的请求。"""
    content = request.form.get('content')
    if not content or not content.strip():
        flash('格言内容不能为空。', 'error')
    else:
        new_motto = Motto(content=content, user_id=current_user.id)
        db.session.add(new_motto)
        db.session.commit()
        flash('新格言已成功添加！', 'success')

    # 修复：重定向到新的内容管理页面
    return redirect(url_for('main.settings_content') + '#headingMottos')


@motto_bp.route('/edit/<int:motto_id>', methods=['POST'])
@login_required
def edit_motto(motto_id):
    """处理编辑格言的请求。"""
    motto = Motto.query.filter_by(id=motto_id, user_id=current_user.id).first_or_404()
    content = request.form.get('content')
    if not content or not content.strip():
        flash('格言内容不能为空。', 'error')
    else:
        motto.content = content
        db.session.commit()
        flash('格言已更新。', 'success')

    # 修复：重定向到新的内容管理页面
    return redirect(url_for('main.settings_content') + '#headingMottos')


@motto_bp.route('/delete/<int:motto_id>', methods=['POST'])
@login_required
def delete_motto(motto_id):
    """处理删除格言的请求。"""
    motto = Motto.query.filter_by(id=motto_id, user_id=current_user.id).first_or_404()
    db.session.delete(motto)
    db.session.commit()
    flash('格言已删除。', 'info')

    # 修复：重定向到新的内容管理页面
    return redirect(url_for('main.settings_content') + '#headingMottos')


@motto_bp.route('/api/random')
@login_required
def get_random_motto():
    """API端点，返回一个随机的格言。(此部分无改动)"""
    mottos = Motto.query.filter_by(user_id=current_user.id).all()
    if not mottos:
        return jsonify({'content': '书山有路勤为径，学海无涯苦作舟。'})

    random_motto = random.choice(mottos)
    return jsonify({'content': random_motto.content})