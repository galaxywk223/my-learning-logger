# 文件路径: learning_logger/blueprints/category_charts.py
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from ..services import chart_service
from ..models import Stage

category_charts_bp = Blueprint('category_charts', __name__)


@category_charts_bp.route('/api/data')
@login_required
def get_data():
    stage_id = request.args.get('stage_id', default=None)
    if stage_id and stage_id.isdigit():
        stage_id = int(stage_id)
    else:
        stage_id = None

    data = chart_service.get_category_chart_data(current_user, stage_id=stage_id)

    if data:
        return jsonify(data)
    else:
        return jsonify({'main': {'labels': [], 'data': []}, 'drilldown': {}})
