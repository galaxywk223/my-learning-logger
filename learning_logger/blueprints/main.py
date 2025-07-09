# learning_logger/blueprints/main.py (已优化)

import os
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, session)
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
import pytz
from sqlalchemy import func

from .. import db
# 新增: 导入 DataImportForm
from ..forms import DataImportForm
from ..models import (Stage, Setting, CountdownEvent, LogEntry, DailyData,
                    WeeklyData, Motto, Todo, Category, SubCategory, Milestone,
                    MilestoneCategory, MilestoneAttachment, DailyPlanItem)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    # ... (此函数内容不变) ...
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
        if hours > 0:
            dashboard_data['records_summary'] = f"今日已记录 {hours} 小时 {minutes} 分钟"
        else:
            dashboard_data['records_summary'] = f"今日已记录 {minutes} 分钟"

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
    # 修改: 创建表单实例并传递给模板
    form = DataImportForm()
    return render_template('settings_data.html', form=form)


@main_bp.route('/stages/add', methods=['POST'])
@login_required
def add_stage():
    # ... (此函数内容不变) ...
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
    # ... (此函数内容不变) ...
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
    # ... (此函数内容不变) ...
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    try:
        # 依赖于 models.py 中定义的 cascade="all, delete-orphan"
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
    # ... (此函数内容不变) ...
    stage = Stage.query.filter_by(id=stage_id, user_id=current_user.id).first_or_404()
    session['active_stage_id'] = stage.id
    flash(f'已切换到阶段：“{stage.name}”', 'success')
    return redirect(url_for('records.list_records'))


# in: my-learning-logger/learning_logger/blueprints/main.py

@main_bp.route('/clear_my_data', methods=['POST'])
@login_required
def clear_my_data():
    try:
        # 1. 在删除数据库记录前，先删除物理附件文件
        upload_folder = current_app.config.get('MILESTONE_UPLOADS')
        if upload_folder:
            attachments_to_delete = MilestoneAttachment.query.join(Milestone).filter(
                Milestone.user_id == current_user.id).all()
            for att in attachments_to_delete:
                try:
                    # 拼接文件的完整服务器路径
                    full_path = os.path.join(upload_folder, att.file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        current_app.logger.info(f"Deleted attachment file: {full_path}")
                except Exception as file_err:
                    # 记录文件删除错误，但继续执行
                    current_app.logger.error(f"Error while deleting attachment file: {file_err}")

        # 2. 按照正确的依赖顺序，从子表到父表依次删除数据库记录

        # 删除与 Milestone 相关的记录
        milestone_ids = [m.id for m in Milestone.query.filter_by(user_id=current_user.id).with_entities(Milestone.id)]
        if milestone_ids:
            MilestoneAttachment.query.filter(MilestoneAttachment.milestone_id.in_(milestone_ids)).delete(
                synchronize_session=False)

        Milestone.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        MilestoneCategory.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)

        # 删除与 Stage 和 Category 相关的子记录
        stage_ids = [s.id for s in Stage.query.filter_by(user_id=current_user.id).with_entities(Stage.id)]
        if stage_ids:
            LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).delete(synchronize_session=False)
            DailyData.query.filter(DailyData.stage_id.in_(stage_ids)).delete(synchronize_session=False)
            WeeklyData.query.filter(WeeklyData.stage_id.in_(stage_ids)).delete(synchronize_session=False)

        category_ids = [c.id for c in Category.query.filter_by(user_id=current_user.id).with_entities(Category.id)]
        if category_ids:
            # LogEntry 对 SubCategory 的引用必须先于 SubCategory 被清除
            # 上一步删除所有 LogEntry 已经解决了这个问题，这里再删除 SubCategory
            SubCategory.query.filter(SubCategory.category_id.in_(category_ids)).delete(synchronize_session=False)

        # 删除其他独立的顶层记录
        Motto.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        Todo.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        CountdownEvent.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        Setting.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        DailyPlanItem.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)

        # 最后删除 Stage 和 Category 这两个父表
        Category.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        Stage.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)

        # 提交所有删除操作
        db.session.commit()
        flash('您的所有个人数据（包括附件）已被成功清空！', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'为用户 {current_user.id} 清空数据时出错: {e}', exc_info=True)
        flash(f'清空数据时发生严重错误: {e}', 'error')

    return redirect(url_for('main.settings_account'))