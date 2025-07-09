# learning_logger/blueprints/charts.py (MODIFIED FOR SHAPE PARAMETER)

from flask import Blueprint, render_template, jsonify, Response, flash, redirect, url_for, request
from flask_login import login_required, current_user
import numpy as np
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


# (clean_nan_for_json and get_chart_data functions are unchanged)
def clean_nan_for_json(data):
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
    chart_data, _ = chart_service.get_chart_data_for_user(current_user)
    cleaned_chart_data = clean_nan_for_json(chart_data)

    if cleaned_chart_data.get('kpis') and 'avg_daily_minutes' in cleaned_chart_data['kpis']:
        raw_minutes = cleaned_chart_data['kpis']['avg_daily_minutes']
        hours, minutes = divmod(int(raw_minutes or 0), 60)
        cleaned_chart_data['kpis']['avg_daily_formatted'] = f"{hours}小时 {minutes}分钟"

    return jsonify(cleaned_chart_data)


# ============================================================================
# MODIFIED ROUTE FOR WORDCLOUD
# ============================================================================
@charts_bp.route('/api/wordcloud')
@login_required
def get_wordcloud_image():
    """API endpoint to generate and return the word cloud image."""
    stage_id = request.args.get('stage_id', default=None)
    if stage_id and stage_id.isdigit():
        stage_id = int(stage_id)
    else:
        stage_id = None

    # Get shape from request, default to 'random' to let service decide
    shape = request.args.get('shape', 'random')

    img_buffer = chart_service.generate_wordcloud_for_user(current_user, stage_id, shape=shape)

    if img_buffer:
        return Response(img_buffer.getvalue(), mimetype='image/png')
    else:
        return '', 204  # No Content


# (export_charts function is unchanged)
@charts_bp.route('/export')
@login_required
def export_charts():
    try:
        image_buffers = chart_service.export_all_charts_as_images(current_user)

        if image_buffers is None:
            flash('没有可供导出的图表数据。', 'warning')
            return redirect(url_for('charts.chart_page'))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('trends_summary.png', image_buffers['trends_image'].getvalue())
            zf.writestr('category_summary.png', image_buffers['category_image'].getvalue())

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