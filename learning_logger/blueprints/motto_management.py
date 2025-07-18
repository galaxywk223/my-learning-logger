# 文件路径: learning_logger/blueprints/motto_management.py
import random
from flask import (Blueprint, render_template, request, redirect, url_for, flash, jsonify)
from flask_login import login_required, current_user
from .. import db
from ..models import Motto

motto_management_bp = Blueprint('motto_management', __name__, url_prefix='/mottos')


@motto_management_bp.route('/')
@login_required
def manage_mottos():
    user_mottos = Motto.query.filter_by(user_id=current_user.id).order_by(Motto.id.desc()).all()
    return render_template('motto_management.html', mottos=user_mottos)


@motto_management_bp.route('/add', methods=['POST'])
@login_required
def add_motto():
    content = request.form.get('content')
    if not content or not content.strip():
        return jsonify({'success': False, 'message': '格言内容不能为空。'}), 400

    new_motto = Motto(content=content, user_id=current_user.id)
    db.session.add(new_motto)
    db.session.commit()

    new_motto_html = render_template('_motto_item.html', motto=new_motto)
    return jsonify({
        'success': True,
        'message': '新格言已添加。',
        'html': new_motto_html,
        'target_container': '#motto-list-container',
        'action': 'prepend'  # Add the new item to the top
    })


@motto_management_bp.route('/edit/<int:motto_id>', methods=['POST'])
@login_required
def edit_motto(motto_id):
    motto = Motto.query.filter_by(id=motto_id, user_id=current_user.id).first_or_404()
    content = request.form.get('content')
    if not content or not content.strip():
        return jsonify({'success': False, 'message': '格言内容不能为空。'}), 400

    motto.content = content
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '格言已更新。',
        'update_target': f'#motto-{motto_id} .motto-content',
        'update_content': f'“ {motto.content} ”'
    })


@motto_management_bp.route('/delete/<int:motto_id>', methods=['POST'])
@login_required
def delete_motto(motto_id):
    motto = Motto.query.filter_by(id=motto_id, user_id=current_user.id).first_or_404()
    db.session.delete(motto)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '格言已删除。',
        'remove_target': f'#motto-{motto_id}'
    })


@motto_management_bp.route('/api/random')
@login_required
def get_random_motto():
    mottos = Motto.query.filter_by(user_id=current_user.id).all()
    if not mottos:
        return jsonify({'content': '书山有路勤为径，学海无涯苦作舟。'})

    random_motto = random.choice(mottos)
    return jsonify({'content': random_motto.content})
