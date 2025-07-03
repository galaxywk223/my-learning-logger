# learning_logger/blueprints/category_charts.py (MODIFIED)

from flask import Blueprint, jsonify, request # render_template is no longer needed
from flask_login import login_required, current_user
from ..services import chart_service
from ..models import Stage

category_charts_bp = Blueprint('category_charts', __name__)


# --- REMOVED: The chart_page() view function is no longer needed ---
# The main chart page is now handled by the 'charts' blueprint.


@category_charts_bp.route('/api/data')
@login_required
def get_data():
    """Provides the category breakdown data via an API endpoint. (Unchanged)"""
    stage_id = request.args.get('stage_id', default=None)
    if stage_id and stage_id.isdigit():
        stage_id = int(stage_id)
    else:
        stage_id = None

    data = chart_service.get_category_chart_data(current_user, stage_id=stage_id)

    if data:
        return jsonify(data)
    else:
        # Return a default empty structure to prevent frontend errors
        return jsonify({'main': {'labels': [], 'data': []}, 'drilldown': {}})