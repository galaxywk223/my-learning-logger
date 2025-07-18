# learning_logger/blueprints/charts.py (REFACTORED)

import io
import zipfile
from datetime import date

from flask import (Blueprint, render_template, jsonify, Response, flash,
                   redirect, url_for, request)
from flask_login import login_required, current_user
import numpy as np

# --- 修改: 引入新的、职责分离的服务 ---
from ..services import chart_service, chart_plotter, wordcloud_service
from ..models import Stage

charts_bp = Blueprint('charts', 'charts_bp', url_prefix='/charts')


@charts_bp.route('/')
@login_required
def chart_page():
    """渲染统一的图表分析页面。"""
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    return render_template('chart.html', stages=user_stages)


def clean_nan_for_json(data):
    """递归清理数据中的 NaN 值，以便JSON序列化。(保持不变)"""
    if isinstance(data, dict):
        return {k: clean_nan_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_nan_for_json(i) for i in data]
    if isinstance(data, float) and np.isnan(data):
        return None
    return data


@charts_bp.route('/api/data')
@login_required
def get_chart_data():
    """为前端提供趋势图表所需的数据。(保持不变)"""
    chart_data, _ = chart_service.get_chart_data_for_user(current_user)
    cleaned_chart_data = clean_nan_for_json(chart_data)

    # 格式化平均每日时长
    if cleaned_chart_data.get('kpis') and 'avg_daily_minutes' in cleaned_chart_data['kpis']:
        raw_minutes = cleaned_chart_data['kpis']['avg_daily_minutes']
        hours, minutes = divmod(int(raw_minutes or 0), 60)
        cleaned_chart_data['kpis']['avg_daily_formatted'] = f"{hours}小时 {minutes}分钟"

    return jsonify(cleaned_chart_data)


@charts_bp.route('/api/wordcloud')
@login_required
def get_wordcloud_image():
    """API端点，用于生成并返回词云图片。"""
    stage_id = request.args.get('stage_id', default=None)
    if stage_id and stage_id.isdigit():
        stage_id = int(stage_id)
    else:
        stage_id = None

    # --- 修改: 调用新的 wordcloud_service ---
    img_buffer = wordcloud_service.generate_wordcloud_for_user(current_user, stage_id=stage_id)

    if img_buffer:
        return Response(img_buffer.getvalue(), mimetype='image/png')
    else:
        # 如果没有内容生成词云，返回 204 No Content
        return '', 204


@charts_bp.route('/export')
@login_required
def export_charts():
    """
    导出所有图表为图片，并打包成一个 ZIP 文件。
    此函数现在调用新的、分离的服务。
    """
    try:
        # 1. 分别获取趋势数据和分类数据
        trend_data, _ = chart_service.get_chart_data_for_user(current_user)
        category_data = chart_service.get_category_chart_data(current_user)

        if not trend_data.get('has_data'):
            flash('没有可供导出的图表数据。', 'warning')
            return redirect(url_for('charts.chart_page'))

        # 2. 分别调用绘图服务来生成图片
        trends_image_buffer = chart_plotter.export_trends_image(current_user.username, trend_data)
        category_image_buffer = chart_plotter.export_category_image(current_user.username, category_data)

        # 3. 将生成的图片打包成 ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            if trends_image_buffer:
                zf.writestr('trends_summary.png', trends_image_buffer.getvalue())
            if category_image_buffer:
                zf.writestr('category_summary.png', category_image_buffer.getvalue())

        zip_buffer.seek(0)
        username = current_user.username.replace(" ", "_")
        today_str = date.today().strftime("%Y-%m-%d")
        filename = f"{username}_charts_{today_str}.zip"

        return Response(
            zip_buffer,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        flash(f'导出图表时发生错误: {e}', 'error')
        print(f"Chart export error: {e}")
        return redirect(url_for('charts.chart_page'))
