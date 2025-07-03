# learning_logger/blueprints/main.py (FIXED DATETIME AWARENESS)

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, session)
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
import pytz
from sqlalchemy import func

from .. import db
from ..models import Stage, Setting, CountdownEvent, LogEntry, DailyData, WeeklyData, Motto, Todo, Category

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """【已修复】仪表盘现在可以正确处理时区。"""

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
        'todo_summary': "没有待办事项"
    }

    today_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).join(Stage).filter(
        Stage.user_id == current_user.id,
        LogEntry.log_date == date.today()
    ).scalar() or 0
    if today_duration_minutes > 0:
        hours, minutes = divmod(today_duration_minutes, 60)
        if hours > 0:
            dashboard_data['records_summary'] = f"今日已记录 {hours} 小时 {minutes} 分钟"
        else:
            dashboard_data['records_summary'] = f"今日已记录 {minutes} 分钟"

    # --- 修复开始 ---
    now_utc = datetime.now(pytz.utc)
    next_event = CountdownEvent.query.filter(
        CountdownEvent.user_id == current_user.id,
        CountdownEvent.target_datetime_utc > now_utc
    ).order_by(CountdownEvent.target_datetime_utc.asc()).first()

    if next_event:
        # 确保从数据库取出的时间是 "aware" 的
        if next_event.target_datetime_utc.tzinfo is None:
            next_event.target_datetime_utc = pytz.utc.localize(next_event.target_datetime_utc)

        time_diff = next_event.target_datetime_utc - now_utc
        days_remaining = time_diff.days
        if days_remaining >= 0:
            dashboard_data['countdown_summary'] = f"'{next_event.title}' 还剩 {days_remaining + 1} 天"
    # --- 修复结束 ---

    pending_todos_count = Todo.query.filter_by(user_id=current_user.id, is_completed=False).count()
    if pending_todos_count > 0:
        dashboard_data['todo_summary'] = f"您有 {pending_todos_count} 个待办事项"

    return render_template('dashboard.html', dashboard_data=dashboard_data)


# ============================================================================
# SETTINGS PAGE ROUTES (No changes below this line)
# ============================================================================

@main_bp.route('/settings')
@login_required
def settings_redirect():
    return redirect(url_for('main.settings_account'))


@main_bp.route('/settings/account')
@login_required
def settings_account():
    return render_template('settings_account.html')


@main_bp.route('/settings/content')
@login_required
def settings_content():
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    user_categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    user_mottos = Motto.query.filter_by(user_id=current_user.id).order_by(Motto.id.desc()).all()
    return render_template('settings_content.html',
                           user_stages=user_stages,
                           categories=user_categories,
                           mottos=user_mottos)


@main_bp.route('/settings/data')
@login_required
def settings_data():
    return render_template('settings_data.html')


@main_bp.route('/stages/add', methods=['POST'])
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
    return redirect(url_for('main.settings_content'))


@main_bp.route('/stages/edit/<int:stage_id>', methods=['POST'])
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
    return redirect(url_for('main.settings_content'))


@main_bp.route('/stages/delete/<int:stage_id>', methods=['POST'])
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
    return redirect(url_for('main.settings_content'))


@main_bp.route('/stages/apply/<int:stage_id>', methods=['POST'])
@login_required
def apply_stage(stage_id):
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    session['active_stage_id'] = stage.id
    flash(f'已切换到阶段：“{stage.name}”', 'success')
    return redirect(url_for('records.list_records'))


@main_bp.route('/clear_my_data', methods=['POST'])
@login_required
def clear_my_data():
    try:
        user_stages = Stage.query.filter_by(user_id=current_user.id).all()
        stage_ids = [s.id for s in user_stages]
        if stage_ids:
            LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).delete(synchronize_session=False)
            DailyData.query.filter(DailyData.stage_id.in_(stage_ids)).delete(synchronize_session=False)
            WeeklyData.query.filter(WeeklyData.stage_id.in_(stage_ids)).delete(synchronize_session=False)
        Motto.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        Todo.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        CountdownEvent.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        Setting.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        if user_stages:
            for stage in user_stages:
                db.session.delete(stage)
        db.session.commit()
        flash('您的所有个人数据已被成功清空！', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'为用户 {current_user.id} 清空数据时出错: {e}', exc_info=True)
        flash(f'清空数据时发生严重错误: {e}', 'error')
    return redirect(url_for('main.settings_account'))