import os
import shutil
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app)
# --- MODIFIED: 导入登录管理工具 ---
from flask_login import login_required, current_user

from .. import db
# --- MODIFIED: 导入所有模型，因为清理数据时需要 ---
from ..models import Setting, LogEntry, DailyData, WeeklyData, CountdownEvent

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
# --- MODIFIED: 保护路由，需要登录才能访问 ---
@login_required
def index():
    """
    新的主页，作为功能导航仪表盘。
    """
    # 渲染新的 dashboard.html 模板
    return render_template('dashboard.html')


@main_bp.route('/settings', methods=['GET', 'POST'])
# --- MODIFIED: 保护路由 ---
@login_required
def settings():
    """
    处理特定于当前用户的应用设置。
    """
    if request.method == 'POST':
        # 遍历表单提交的所有键值对
        for key, value in request.form.items():
            # --- MODIFIED: 查询设置时，同时匹配 key 和 user_id ---
            # Setting 模型现在是复合主键 (key, user_id)
            setting = db.session.get(Setting, (key, current_user.id))

            if setting:
                # 如果存在，则更新其值
                setting.value = value
            else:
                # --- MODIFIED: 创建新设置时，必须绑定当前用户 ---
                # 如果不存在，则创建新的设置项并添加到会话中
                db.session.add(Setting(key=key, value=value, user_id=current_user.id))

        try:
            db.session.commit()
            flash('设置已成功更新！', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'更新设置时出错: {e}', 'error')

        return redirect(url_for('main.settings'))

    # --- MODIFIED: GET 请求时，只获取当前用户的设置项 ---
    all_settings = Setting.query.filter_by(user_id=current_user.id).all()
    # 将设置列表转换为字典，方便在模板中通过键来访问
    settings_dict = {setting.key: setting.value for setting in all_settings}
    return render_template('settings.html', settings=settings_dict)


# --- DEPRECATED: 废弃了 _restore_data_from_backup 和 clear_all_data 函数 ---
# 这些全局操作在多用户场景下非常危险，已被移除或替换。
# 导入/导出功能将在 records.py 中以对用户安全的方式实现。


# --- MODIFIED: 路由和函数功能已完全改变 ---
@main_bp.route('/clear_my_data', methods=['POST'])
@login_required
def clear_my_data():
    """
    清空当前用户的所有数据。这是一个危险操作！
    它会删除该用户的所有学习记录、效率、倒计时和设置。
    """
    try:
        # 按正确的顺序删除数据，以避免外键约束问题
        LogEntry.query.filter_by(user_id=current_user.id).delete()
        DailyData.query.filter_by(user_id=current_user.id).delete()
        WeeklyData.query.filter_by(user_id=current_user.id).delete()
        CountdownEvent.query.filter_by(user_id=current_user.id).delete()
        Setting.query.filter_by(user_id=current_user.id).delete()

        db.session.commit()
        flash('您的所有个人数据已被成功清空！', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'为用户 {current_user.id} 清空数据时出错: {e}')
        flash(f'清空数据时发生严重错误: {e}', 'error')

    return redirect(url_for('main.settings'))
