# learning_logger/blueprints/charts.py (Simplified)

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from ..services import chart_service

charts_bp = Blueprint('charts', 'charts_bp', url_prefix='/charts')

@charts_bp.route('/')
@login_required
def chart_page():
    """Renders the main chart page framework."""
    return render_template('chart.html')

@charts_bp.route('/api/data')
@login_required
def get_chart_data():
    """Provides the chart data via an API endpoint."""
    chart_data, _ = chart_service.get_chart_data_for_user(current_user)
    return jsonify(chart_data)