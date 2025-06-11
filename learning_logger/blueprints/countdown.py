from datetime import date, datetime
import pytz

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
# --- MODIFIED: 导入登录管理工具 ---
from flask_login import login_required, current_user

from .. import db
# --- MODIFIED: 导入 Setting 模型用于获取用户设置 ---
from ..models import CountdownEvent, Setting
from ..helpers import get_custom_week_info

countdown_bp = Blueprint('countdown', __name__, url_prefix='/countdown')

# 定义时区，以便在整个蓝图中重用
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


@countdown_bp.route('/')
# --- MODIFIED: 保护路由 ---
@login_required
def list_events():
    """
    显示当前用户的所有倒计时事件的列表，区分为已激活和已过期。
    """
    now_utc = datetime.now(pytz.utc)
    # --- MODIFIED: 查询当前用户的事件 ---
    all_events = CountdownEvent.query.filter_by(user_id=current_user.id).order_by(CountdownEvent.target_datetime_utc.asc()).all()

    active_events = []
    expired_events = []

    # --- MODIFIED: 尝试获取当前用户的周起始日期设置 ---
    start_date_setting = Setting.query.filter_by(user_id=current_user.id, key='week_start_date').first()

    # 计算当前相对时间
    if not start_date_setting:
        current_relative_time = "请先在设置中指定起始周"
    else:
        start_date = date.fromisoformat(start_date_setting.value)
        now_beijing = now_utc.astimezone(BEIJING_TZ)
        _, week_num = get_custom_week_info(now_beijing.date(), start_date)
        day_map = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
        day_of_week_str = day_map.get(now_beijing.weekday(), '')
        hour = now_beijing.hour
        time_of_day_str = "凌晨" if 0 <= hour < 6 else "上午" if hour < 12 else "中午" if hour < 14 else "下午" if hour < 18 else "晚上"
        current_relative_time = f"第 {week_num} 周周{day_of_week_str}{time_of_day_str}"

    for event in all_events:
        # 确保从数据库取出的时间是 UTC 感知的
        if event.target_datetime_utc.tzinfo is None:
            event.target_datetime_utc = pytz.utc.localize(event.target_datetime_utc)

        # 将 UTC 时间转换为北京时间用于显示
        event.target_datetime_beijing = event.target_datetime_utc.astimezone(BEIJING_TZ)

        # 将目标时间也转换为 ISO 格式字符串，方便前端JS处理
        event.target_iso_utc = event.target_datetime_utc.isoformat()

        # 根据是否过期进行分类
        if event.target_datetime_utc < now_utc:
            event.is_expired = True
            expired_events.append(event)
        else:
            event.is_expired = False
            active_events.append(event)

    # 过期事件按时间倒序排列，最近的在前
    expired_events.sort(key=lambda x: x.target_datetime_utc, reverse=True)

    return render_template(
        'countdown.html',
        active_events=active_events,
        expired_events=expired_events,
        current_relative_time=current_relative_time
    )


@countdown_bp.route('/form/add')
# --- MODIFIED: 保护路由 ---
@login_required
def get_add_form():
    """提供用于添加新事件的空白表单。"""
    return render_template('_form_countdown.html', event=None, action_url=url_for('countdown.add'),
                           submit_button_text='添加目标')


@countdown_bp.route('/form/edit/<int:event_id>')
# --- MODIFIED: 保护路由 ---
@login_required
def get_edit_form(event_id):
    """提供用于编辑现有事件的、已填充数据的表单。"""
    # --- MODIFIED: 安全地获取事件，确保属于当前用户 ---
    event = CountdownEvent.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    # 将 UTC 时间转换为北京时间，以便在表单中正确显示
    event.target_datetime_beijing = event.target_datetime_utc.astimezone(BEIJING_TZ)
    return render_template('_form_countdown.html', event=event, action_url=url_for('countdown.edit', event_id=event.id),
                           submit_button_text='更新目标')


def _process_form_and_get_utc_datetime():
    """内部辅助函数，用于处理表单数据并返回 UTC 时间。"""
    title = request.form.get('title')
    target_date_str = request.form.get('target_date')
    target_time_str = request.form.get('target_time') or "00:00"

    if not all([title, target_date_str]):
        raise ValueError("目标名称和日期是必填项。")

    local_dt_naive = datetime.strptime(f"{target_date_str} {target_time_str}", '%Y-%m-%d %H:%M')
    local_dt_aware = BEIJING_TZ.localize(local_dt_naive)
    utc_dt = local_dt_aware.astimezone(pytz.utc)

    return title, utc_dt


@countdown_bp.route('/add', methods=['POST'])
# --- MODIFIED: 保护路由 ---
@login_required
def add():
    """处理新倒计时事件的添加请求。"""
    try:
        title, utc_dt = _process_form_and_get_utc_datetime()
        # --- MODIFIED: 创建时必须关联当前用户 ---
        new_event = CountdownEvent(title=title, target_datetime_utc=utc_dt, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'success': True, 'message': f'新的倒计时目标 “{title}” 已添加！'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"添加倒计时事件时出错: {e}")
        return jsonify({'success': False, 'message': f'添加目标时出错: {e}'}), 400


@countdown_bp.route('/edit/<int:event_id>', methods=['POST'])
# --- MODIFIED: 保护路由 ---
@login_required
def edit(event_id):
    """处理倒计时事件的编辑请求。"""
    # --- MODIFIED: 安全地获取事件 ---
    event = CountdownEvent.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    try:
        title, utc_dt = _process_form_and_get_utc_datetime()
        event.title = title
        event.target_datetime_utc = utc_dt
        db.session.commit()
        return jsonify({'success': True, 'message': f'目标 “{title}” 已更新！'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"编辑事件 {event_id} 时出错: {e}")
        return jsonify({'success': False, 'message': f'更新目标时出错: {e}'}), 400


@countdown_bp.route('/delete/<int:event_id>', methods=['POST'])
# --- MODIFIED: 保护路由 ---
@login_required
def delete(event_id):
    """处理倒计时事件的删除请求。"""
    # --- MODIFIED: 安全地获取事件 ---
    event = CountdownEvent.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    try:
        title = event.title
        db.session.delete(event)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'目标 “{title}” 已删除。'})

        flash(f'目标 “{title}” 已删除。', 'info')
        return redirect(url_for('countdown.list_events'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除事件 {event_id} 时出错: {e}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'删除目标时出错: {e}'}), 400

        flash(f'删除目标时出错: {e}', 'error')
        return redirect(url_for('countdown.list_events'))
