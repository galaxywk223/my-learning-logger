# learning_logger/blueprints/charts.py (添加API接口后版本)

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from ..services import chart_service

charts_bp = Blueprint('charts', 'charts_bp', url_prefix='/charts')


@charts_bp.route('/')
@login_required
def chart_page():
    """
    渲染图表页面的主框架。
    页面加载后，将由JavaScript通过API获取并填充数据。
    """
    # 我们仍然需要检查设置，因为如果未设置，页面将无法正确显示。
    # chart_service会返回一个简单的None, True元组
    _, setup_needed = chart_service.get_chart_data_for_user(current_user)

    if setup_needed:
        return render_template('chart.html', setup_needed=True)

    # 只渲染页面框架，不传递任何图表数据
    return render_template('chart.html', setup_needed=False)


@charts_bp.route('/api/data')
@login_required
def get_chart_data():
    """
    提供图表数据的API端点。
    """
    chart_data, setup_needed = chart_service.get_chart_data_for_user(current_user)

    if setup_needed:
        return jsonify({'error': 'Setup needed, cannot provide data.'}), 404

    return jsonify(chart_data)