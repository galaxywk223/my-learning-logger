import io
import zipfile
from datetime import date

from flask import (Blueprint, render_template, jsonify, Response, flash,
                   redirect, url_for, request, current_app)
from flask_login import login_required, current_user
import numpy as np

from ..services import chart_service, chart_plotter, wordcloud_service
from ..models import Stage

charts_bp = Blueprint('charts', 'charts_bp', url_prefix='/charts')


@charts_bp.route('/')
@login_required
def chart_page():
    """渲染统一的图表分析页面。"""
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()

    # 定义蒙版选项，传递给模板 (已移除您删除的4个选项)
    mask_options = [
        {'file': 'random', 'name': '随机形状'},
        {'file': 'brain-profile.png', 'name': '大脑'},
        {'file': 'book-open.png', 'name': '书本'},
        {'file': 'lightbulb-on.png', 'name': '灯泡'},
        {'file': 'graduation-cap.png', 'name': '毕业帽'},
        {'file': 'trophy-solid.png', 'name': '奖杯'},
        {'file': 'tree-of-knowledge.png', 'name': '知识树'},
        {'file': 'arrow-growth.png', 'name': '成长箭头'},
        {'file': 'key-solid.png', 'name': '智慧之钥'},
        {'file': 'puzzle-piece.png', 'name': '知识拼图'},
        {'file': 'dialogue-bubble.png', 'name': '思维气泡'},
        {'file': 'laptop-solid.png', 'name': '电脑'},
        {'file': 'code-brackets.png', 'name': '代码'},
        {'file': 'gear-solid.png', 'name': '齿轮'},
        {'file': 'flask-solid.png', 'name': '烧瓶'},
        {'file': 'microscope.png', 'name': '显微镜'},
        {'file': 'bar-chart.png', 'name': '图表'},
    ]

    return render_template('chart.html', stages=user_stages, mask_options=mask_options)


def clean_nan_for_json(data):
    """递归清理数据中的 NaN 值，以便JSON序列化。"""
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
    """为前端提供趋势图表所需的数据。"""
    chart_data, _ = chart_service.get_chart_data_for_user(current_user)
    cleaned_chart_data = clean_nan_for_json(chart_data)

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
    mask_name = request.args.get('mask', default='random')
    palette = request.args.get('palette', default='default')

    if stage_id and stage_id.isdigit():
        stage_id = int(stage_id)
    else:
        stage_id = None

    img_buffer = wordcloud_service.generate_wordcloud_for_user(
        current_user,
        stage_id=stage_id,
        mask_name=mask_name,
        palette=palette
    )

    if img_buffer:
        return Response(img_buffer.getvalue(), mimetype='image/png')
    else:
        return '', 204


@charts_bp.route('/export')
@login_required
def export_charts():
    """
    导出所有图表为图片，并打包成一个 ZIP 文件。
    """
    try:
        trend_data, _ = chart_service.get_chart_data_for_user(current_user)
        category_data = chart_service.get_category_chart_data(current_user)

        if not trend_data.get('has_data'):
            flash('没有可供导出的图表数据。', 'warning')
            return redirect(url_for('charts.chart_page'))

        trends_image_buffer = chart_plotter.export_trends_image(current_user.username, trend_data)
        category_image_buffer = chart_plotter.export_category_image(current_user.username, category_data)

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
        current_app.logger.error(f"Chart export error: {e}", exc_info=True)
        return redirect(url_for('charts.chart_page'))
