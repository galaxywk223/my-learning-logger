# learning_logger/blueprints/main.py (REVISED FOR APPEARANCE SETTINGS)

import os
import pytz
from datetime import date, datetime
from flask import (Blueprint, render_template, redirect, url_for, request, flash, current_app)
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from .. import db
from ..forms import AppearanceForm
from ..models import (Stage, CountdownEvent, LogEntry, Todo, Milestone, DailyPlanItem, Setting)

main_bp = Blueprint('main', __name__)


# --- Helper function to get/set settings ---
def get_user_setting(key, default=None):
    setting = Setting.query.filter_by(user_id=current_user.id, key=key).first()
    return setting.value if setting else default


def set_user_setting(key, value):
    setting = Setting.query.filter_by(user_id=current_user.id, key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(user_id=current_user.id, key=key, value=value)
        db.session.add(setting)
    db.session.commit()


@main_bp.route('/')
@login_required
def index():
    """
    Displays the main dashboard with a summary of user's activities.
    """
    try:
        tz = pytz.timezone('Asia/Shanghai')
        current_hour = datetime.now(tz).hour
        if 5 <= current_hour < 12:
            greeting = f"早上好, {current_user.username}！"
        elif 12 <= current_hour < 18:
            greeting = f"下午好, {current_user.username}！"
        else:
            greeting = f"晚上好, {current_user.username}！"
    except Exception:
        greeting = f"你好, {current_user.username}！"

    dashboard_data = {
        'greeting': greeting,
        'records_summary': "今日暂无记录",
        'countdown_summary': "没有进行中的目标",
        'todo_summary': "没有待办事项",
        'milestone_summary': "尚未记录任何成就",
        'plan_summary': "今日暂无计划"
    }

    today_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).join(Stage).filter(
        Stage.user_id == current_user.id,
        LogEntry.log_date == date.today()
    ).scalar() or 0
    if today_duration_minutes > 0:
        hours, minutes = divmod(today_duration_minutes, 60)
        dashboard_data[
            'records_summary'] = f"今日已记录 {hours} 小时 {minutes} 分钟" if hours > 0 else f"今日已记录 {minutes} 分钟"

    now_utc = datetime.now(pytz.utc)
    next_event = CountdownEvent.query.filter(
        CountdownEvent.user_id == current_user.id,
        CountdownEvent.target_datetime_utc > now_utc
    ).order_by(CountdownEvent.target_datetime_utc.asc()).first()

    if next_event:
        if next_event.target_datetime_utc.tzinfo is None:
            next_event.target_datetime_utc = pytz.utc.localize(next_event.target_datetime_utc)
        time_diff = next_event.target_datetime_utc - now_utc
        days_remaining = time_diff.days
        if days_remaining >= 0:
            dashboard_data['countdown_summary'] = f"'{next_event.title}' 还剩 {days_remaining + 1} 天"

    pending_todos_count = Todo.query.filter_by(user_id=current_user.id, is_completed=False).count()
    if pending_todos_count > 0:
        dashboard_data['todo_summary'] = f"您有 {pending_todos_count} 个待办事项"

    milestones_count = Milestone.query.filter_by(user_id=current_user.id).count()
    if milestones_count > 0:
        dashboard_data['milestone_summary'] = f"已记录 {milestones_count} 个重要时刻"

    today_plans_query = DailyPlanItem.query.filter_by(user_id=current_user.id, plan_date=date.today())
    total_today = today_plans_query.count()
    if total_today > 0:
        completed_today = today_plans_query.filter_by(is_completed=True).count()
        dashboard_data['plan_summary'] = f"今日计划 {completed_today}/{total_today} 项已完成"

    return render_template('dashboard.html', dashboard_data=dashboard_data)


# ============================================================================
# SETTINGS PAGE ROUTES
# ============================================================================

@main_bp.route('/settings')
@login_required
def settings_redirect():
    """Redirects from the base /settings URL to the default account page."""
    return redirect(url_for('main.settings_account'))


@main_bp.route('/settings/account')
@login_required
def settings_account():
    """Renders the user account settings page."""
    return render_template('settings_account.html')


@main_bp.route('/settings/appearance', methods=['GET', 'POST'])
@login_required
def settings_appearance():
    form = AppearanceForm()
    upload_folder = current_app.config.get('BACKGROUND_UPLOADS')
    if not upload_folder:
        flash('背景图片上传路径未配置，功能受限。', 'warning')

    if request.method == 'POST':
        try:
            # --- 核心修改：重构逻辑以处理不同的提交动作 ---

            # 动作1: 用户点击了“移除背景”按钮
            if 'remove_background' in request.form:
                set_user_setting('background_image', '')
                flash('自定义背景已移除。', 'success')

            # 动作2: 用户上传了新文件（自动提交）
            elif form.background_image.data:
                if form.background_image.validate(form):
                    file = form.background_image.data
                    filename = f"bg_{current_user.id}_{int(datetime.now().timestamp())}{os.path.splitext(file.filename)[1]}"
                    filename = secure_filename(filename)
                    user_bg_folder = os.path.join(upload_folder, str(current_user.id))
                    os.makedirs(user_bg_folder, exist_ok=True)
                    file.save(os.path.join(user_bg_folder, filename))
                    relative_path = f"{current_user.id}/{filename}"
                    set_user_setting('background_image', relative_path)
                    flash('背景图片已更新。', 'success')
                else:
                    for error in form.background_image.errors:
                        flash(error, 'danger')

            # 动作3: 用户点击了“保存主题设置”按钮
            elif form.validate():  # 验证表单的其余部分（主要是主题）
                set_user_setting('theme', form.theme.data)
                flash('主题设置已保存。', 'success')

            # 如果验证失败，WTForms会自动处理错误，但我们也可以手动flash
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f"{form[field].label.text}: {error}", 'danger')

        except Exception as e:
            current_app.logger.error(f"Error updating appearance settings: {e}")
            flash('更新设置时发生错误。', 'danger')

        return redirect(url_for('main.settings_appearance'))

    # 为GET请求填充表单的当前值
    form.theme.data = get_user_setting('theme', 'palette-purple')
    current_settings = {
        'theme': get_user_setting('theme', 'palette-purple'),
        'background_image': get_user_setting('background_image')
    }

    return render_template('settings_appearance.html', form=form, current_settings=current_settings)