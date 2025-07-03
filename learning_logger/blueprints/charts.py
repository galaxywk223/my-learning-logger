# learning_logger/blueprints/charts.py (FINAL FIX FOR API)

from flask import Blueprint, render_template, jsonify, Response, flash, redirect, url_for
from flask_login import login_required, current_user
import numpy as np  # <-- 新增导入
import io
import zipfile
from datetime import date

from ..services import chart_service
from ..models import Stage

charts_bp = Blueprint('charts', 'charts_bp', url_prefix='/charts')


@charts_bp.route('/')
@login_required
def chart_page():
    """Renders the unified chart page."""
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    return render_template('chart.html', stages=user_stages)


# --- 新增：一个辅助函数，用于将 np.nan 转换为 None ---
def clean_nan_for_json(data):
    """
    递归地遍历数据结构，将所有 np.nan 值替换为 None，以便进行 JSON 序列化。
    """
    if isinstance(data, dict):
        return {k: clean_nan_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_nan_for_json(i) for i in data]
    # 使用 np.isnan() 来检查 NaN 值，因为它对 float 和 np.nan 都有效
    if isinstance(data, float) and np.isnan(data):
        return None
    return data


@charts_bp.route('/api/data')
@login_required
def get_chart_data():
    """Provides the chart data, with formatted KPIs."""
    chart_data, _ = chart_service.get_chart_data_for_user(current_user)

    # 在发送到前端之前，清理数据中的 np.nan 值
    cleaned_chart_data = clean_nan_for_json(chart_data)

    # Format the average minutes KPI before sending
    if cleaned_chart_data.get('kpis') and 'avg_daily_minutes' in cleaned_chart_data['kpis']:
        raw_minutes = cleaned_chart_data['kpis']['avg_daily_minutes']
        hours, minutes = divmod(int(raw_minutes or 0), 60)
        cleaned_chart_data['kpis']['avg_daily_formatted'] = f"{hours}小时 {minutes}分钟"

    return jsonify(cleaned_chart_data)


# --- 导出路由保持不变 ---
@charts_bp.route('/export')
@login_required
def export_charts():
    """
    调用服务生成图表图片，将它们打包成 ZIP 文件并提供下载。
    """
    try:
        image_buffers = chart_service.export_all_charts_as_images(current_user)

        if image_buffers is None:
            flash('没有可供导出的图表数据。', 'warning')
            return redirect(url_for('charts.chart_page'))

        # 创建一个内存中的 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('trends_summary.png', image_buffers['trends_image'].getvalue())
            zf.writestr('category_summary.png', image_buffers['category_image'].getvalue())

        zip_buffer.seek(0)

        # 准备下载的文件名
        username = current_user.username.replace(" ", "_")
        today_str = date.today().strftime("%Y-%m-%d")
        filename = f"{username}_charts_{today_str}.zip"

        # 返回 ZIP 文件作为响应
        return Response(
            zip_buffer,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        flash(f'导出图表时发生错误: {e}', 'error')
        # 在开发中打印更详细的错误
        print(f"Chart export error: {e}")
        return redirect(url_for('charts.chart_page'))