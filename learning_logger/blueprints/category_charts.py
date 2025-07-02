# learning_logger/blueprints/category_charts.py

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from ..services import chart_service
from ..models import Stage

category_charts_bp = Blueprint('category_charts', __name__)


@category_charts_bp.route('/')
@login_required
def chart_page():
    """渲染分类统计图表页面框架。"""
    user_stages = Stage.query.filter_by(user_id=current_user.id).order_by(Stage.start_date.desc()).all()
    return render_template('category_chart.html', stages=user_stages)


@category_charts_bp.route('/api/data')
@login_required
def get_data():
    """提供图表数据的API端点。"""
    stage_id = request.args.get('stage_id', default=None)
    if stage_id and stage_id.isdigit():
        stage_id = int(stage_id)
    else:
        stage_id = None  # 'all' or invalid is treated as all history

    data = chart_service.get_category_chart_data(current_user, stage_id=stage_id)

    if data:
        return jsonify(data)
    else:
        return jsonify({'main': {'labels': [], 'data': []}, 'drilldown': {}})