# learning_logger/services/chart_service.py (FINAL COLOR FIX)

import collections
import io
from datetime import date, timedelta
from sqlalchemy import func, desc
import matplotlib.pyplot as plt
import numpy as np

from .. import db
from ..models import Stage, LogEntry, WeeklyData, DailyData, Category, SubCategory
from ..helpers import get_custom_week_info

# --- 美化样式配置 (颜色格式修正) ---
plt.style.use('seaborn-v0_8-whitegrid')
try:
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    print("Warning: Chinese font 'SimHei' not found. Chart labels may not render correctly.")

# 修正：将 rgba 字符串转换为 matplotlib 可接受的元组格式 (R/255, G/255, B/255, A)
COLORS = {
    'duration_bar': (96 / 255, 165 / 255, 250 / 255, 0.6),
    'duration_line': '#2563EB',
    'efficiency_bar': (248 / 255, 113 / 255, 113 / 255, 0.6),
    'efficiency_line': '#B91C1C',
    'category_palette': ['#60A5FA', '#F87171', '#FBBF24', '#4ADE80', '#A78BFA', '#2DD4BF', '#F472B6', '#818CF8']
}


def _calculate_sma(data, window_size=7):
    # 此内部函数保持不变
    if not data or window_size <= 1: return [None] * len(data)
    sma_values, window = [], collections.deque(maxlen=window_size)
    for i, value in enumerate(data):
        try:
            numeric_value = float(value) if value is not None else np.nan
        except (ValueError, TypeError):
            numeric_value = np.nan
        window.append(numeric_value)
        if i < window_size - 1:
            sma_values.append(np.nan)
        else:
            valid_values = [v for v in window if not np.isnan(v)]
            sma = sum(valid_values) / len(valid_values) if valid_values else np.nan
            sma_values.append(round(sma, 2) if not np.isnan(sma) else np.nan)
    return sma_values


def get_chart_data_for_user(user):
    # 此数据获取函数保持不变
    all_stages = Stage.query.filter_by(user_id=user.id).order_by(Stage.start_date.asc()).all()
    if not all_stages:
        return {'kpis': {}, 'stage_annotations': [], 'setup_needed': True}, False

    stage_ids = [s.id for s in all_stages]
    all_logs = LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).all()
    if not all_logs:
        return {'kpis': {'avg_daily_minutes': 0, 'efficiency_star': 'N/A', 'weekly_trend': 'N/A'},
                'has_data': False}, False

    kpis = {}
    total_duration_minutes = db.session.query(func.sum(LogEntry.actual_duration)).filter(
        LogEntry.stage_id.in_(stage_ids)).scalar() or 0
    total_days_with_logs = db.session.query(func.count(func.distinct(LogEntry.log_date))).filter(
        LogEntry.stage_id.in_(stage_ids)).scalar() or 0
    kpis['avg_daily_minutes'] = round(total_duration_minutes / total_days_with_logs,
                                      1) if total_days_with_logs > 0 else 0

    top_efficiency_day = DailyData.query.join(Stage).filter(Stage.user_id == user.id).order_by(
        desc(DailyData.efficiency)).first()
    if top_efficiency_day and top_efficiency_day.efficiency is not None:
        kpis[
            'efficiency_star'] = f"{top_efficiency_day.log_date.strftime('%Y-%m-%d')} (效率: {top_efficiency_day.efficiency:.1f})"
    else:
        kpis['efficiency_star'] = "无足够数据"

    today = date.today()
    start_of_this_week = today - timedelta(days=today.weekday())
    end_of_this_week = start_of_this_week + timedelta(days=6)
    logs_this_week = db.session.query(func.sum(LogEntry.actual_duration)).join(Stage).filter(Stage.user_id == user.id,
                                                                                             LogEntry.log_date.between(
                                                                                                 start_of_this_week,
                                                                                                 end_of_this_week)).scalar() or 0
    start_of_last_week = start_of_this_week - timedelta(days=7)
    end_of_last_week = start_of_this_week - timedelta(days=1)
    logs_last_week = db.session.query(func.sum(LogEntry.actual_duration)).join(Stage).filter(Stage.user_id == user.id,
                                                                                             LogEntry.log_date.between(
                                                                                                 start_of_last_week,
                                                                                                 end_of_last_week)).scalar() or 0
    if logs_last_week > 0:
        percentage_change = ((logs_this_week - logs_last_week) / logs_last_week) * 100
        kpis['weekly_trend'] = f"{'+' if percentage_change >= 0 else ''}{percentage_change:.0f}%"
    elif logs_this_week > 0:
        kpis['weekly_trend'] = "新开始"
    else:
        kpis['weekly_trend'] = "无对比数据"

    first_log_date = min(log.log_date for log in all_logs)
    last_log_date = date.today()
    global_start_date = all_stages[0].start_date
    date_range = [first_log_date + timedelta(days=x) for x in range((last_log_date - first_log_date).days + 1)]
    daily_labels = [d.isoformat() for d in date_range]
    daily_duration_map = {d[0]: d[1] for d in
                          db.session.query(LogEntry.log_date, func.sum(LogEntry.actual_duration)).filter(
                              LogEntry.stage_id.in_(stage_ids)).group_by(LogEntry.log_date).all()}
    daily_durations = [round((daily_duration_map.get(d, 0) or 0) / 60, 2) for d in date_range]
    daily_efficiency_map = {d.log_date: d.efficiency for d in
                            DailyData.query.join(Stage).filter(Stage.user_id == user.id).all()}
    daily_efficiencies = [daily_efficiency_map.get(d) for d in date_range]

    weekly_data = collections.defaultdict(lambda: {'duration': 0, 'efficiency': None})
    current_d = first_log_date
    while current_d <= last_log_date:
        year, week_num = get_custom_week_info(current_d, global_start_date)
        weekly_data[(year, week_num)]['duration'] += daily_duration_map.get(current_d, 0)
        current_d += timedelta(days=1)
    weekly_efficiency_from_db = WeeklyData.query.join(Stage).filter(Stage.user_id == user.id).all()
    for w_eff in weekly_efficiency_from_db:
        week_start_in_stage = w_eff.stage.start_date + timedelta(weeks=w_eff.week_num - 1)
        global_year, global_week_num = get_custom_week_info(week_start_in_stage, global_start_date)
        if (global_year, global_week_num) in weekly_data:
            weekly_data[(global_year, global_week_num)]['efficiency'] = w_eff.efficiency
    sorted_week_keys = sorted(weekly_data.keys())
    weekly_labels = [f"{k[0]}-W{k[1]:02}" for k in sorted_week_keys]
    weekly_durations = [round(weekly_data[k]['duration'] / 60, 2) for k in sorted_week_keys]
    weekly_efficiencies = [weekly_data[k]['efficiency'] for k in sorted_week_keys]

    stage_annotations = []
    for stage in all_stages:
        start_g_year, start_g_week = get_custom_week_info(stage.start_date, global_start_date)
        next_stage_check = Stage.query.filter(Stage.user_id == user.id, Stage.start_date > stage.start_date).order_by(
            Stage.start_date.asc()).first()
        end_date = (next_stage_check.start_date - timedelta(days=1)) if next_stage_check else last_log_date
        end_g_year, end_g_week = get_custom_week_info(end_date, global_start_date)
        stage_annotations.append({'name': stage.name, 'start_week_label': f"{start_g_year}-W{start_g_week:02}",
                                  'end_week_label': f"{end_g_year}-W{end_g_week:02}"})

    return {
        'kpis': kpis,
        'stage_annotations': stage_annotations,
        'has_data': True,
        'weekly_duration_data': {'labels': weekly_labels, 'actuals': weekly_durations,
                                 'trends': _calculate_sma(weekly_durations, 3)},
        'weekly_efficiency_data': {'labels': weekly_labels, 'actuals': weekly_efficiencies,
                                   'trends': _calculate_sma(weekly_efficiencies, 3)},
        'daily_duration_data': {'labels': daily_labels, 'actuals': daily_durations,
                                'trends': _calculate_sma(daily_durations, 7)},
        'daily_efficiency_data': {'labels': daily_labels, 'actuals': daily_efficiencies,
                                  'trends': _calculate_sma(daily_efficiencies, 7)}
    }, False


def get_category_chart_data(user, stage_id=None):
    # 此数据获取函数保持不变
    query = db.session.query(Category.name, SubCategory.name, func.sum(LogEntry.actual_duration)).join(SubCategory,
                                                                                                       LogEntry.subcategory_id == SubCategory.id).join(
        Category, SubCategory.category_id == Category.id).filter(Category.user_id == user.id).group_by(Category.name,
                                                                                                       SubCategory.name)
    if stage_id: query = query.filter(LogEntry.stage_id == stage_id)
    results = query.all()
    if not results: return None
    category_data = collections.defaultdict(lambda: {'total': 0, 'subs': []})
    for cat_name, sub_name, duration in results:
        duration_hours = (duration or 0) / 60.0
        category_data[cat_name]['total'] += duration_hours
        category_data[cat_name]['subs'].append({'name': sub_name, 'duration': round(duration_hours, 2)})

    sorted_categories = sorted(category_data.items(), key=lambda item: item[1]['total'], reverse=True)

    main_labels = [item[0] for item in sorted_categories]
    main_data = [round(item[1]['total'], 2) for item in sorted_categories]

    sub_data = {
        cat_name: {
            'labels': [sub['name'] for sub in sorted(cat_info['subs'], key=lambda x: x['duration'], reverse=True)],
            'data': [sub['duration'] for sub in sorted(cat_info['subs'], key=lambda x: x['duration'], reverse=True)]
        } for cat_name, cat_info in sorted_categories
    }

    return {'main': {'labels': main_labels, 'data': main_data}, 'drilldown': sub_data}


def export_all_charts_as_images(user):
    """
    生成包含所有趋势图表和完整分类图表（含子图）的两张美化后的图片。
    """
    trend_data, _ = get_chart_data_for_user(user)
    category_data = get_category_chart_data(user, stage_id=None)

    if not trend_data.get('has_data'):
        return None

    # --- 1. 生成趋势图表图片 ---
    fig_trends, axes_trends = plt.subplots(2, 2, figsize=(20, 14), dpi=120)
    fig_trends.suptitle(f'{user.username} 的学习趋势总览', fontsize=24, weight='bold', y=0.98)

    # a. 每周时长
    ax1 = axes_trends[0, 0]
    weekly_duration = trend_data['weekly_duration_data']
    ax1.bar(weekly_duration['labels'], weekly_duration['actuals'], label='实际时长 (小时)',
            color=COLORS['duration_bar'], width=0.6)
    trends_y = np.array(weekly_duration['trends'], dtype=float)
    trends_x = np.arange(len(weekly_duration['labels']))
    valid_mask = ~np.isnan(trends_y)
    ax1.plot(trends_x[valid_mask], trends_y[valid_mask], label='趋势线 (3周)', color=COLORS['duration_line'],
             marker='o', markersize=4, linewidth=2.5)
    ax1.set_title('每周学习时长', fontsize=16, weight='bold')
    ax1.tick_params(axis='x', rotation=45, labelsize=10)
    ax1.legend()

    # b. 每周效率
    ax2 = axes_trends[0, 1]
    weekly_efficiency = trend_data['weekly_efficiency_data']
    eff_y = np.array(weekly_efficiency['actuals'], dtype=float)
    eff_x_labels = weekly_efficiency['labels']
    valid_eff_mask = ~np.isnan(eff_y)
    ax2.bar(np.array(eff_x_labels)[valid_eff_mask], eff_y[valid_eff_mask], label='实际效率',
            color=COLORS['efficiency_bar'], width=0.6)
    trends_eff_y = np.array(weekly_efficiency['trends'], dtype=float)
    trends_eff_x = np.arange(len(eff_x_labels))
    valid_trends_mask = ~np.isnan(trends_eff_y)
    ax2.plot(trends_eff_x[valid_trends_mask], trends_eff_y[valid_trends_mask], label='趋势线 (3周)',
             color=COLORS['efficiency_line'], marker='o', markersize=4, linewidth=2.5)
    ax2.set_title('每周学习效率', fontsize=16, weight='bold')
    ax2.tick_params(axis='x', rotation=45, labelsize=10)
    ax2.legend()

    # c. 每日时长
    ax3 = axes_trends[1, 0]
    daily_duration = trend_data['daily_duration_data']
    # 修正：每日图的线状图应使用不透明的线条颜色
    ax3.plot(daily_duration['labels'], daily_duration['actuals'], label='实际时长 (小时)',
             color=COLORS['duration_line'], alpha=0.5)
    daily_trends_y = np.array(daily_duration['trends'], dtype=float)
    daily_trends_x = np.arange(len(daily_duration['labels']))
    valid_daily_mask = ~np.isnan(daily_trends_y)
    ax3.plot(daily_trends_x[valid_daily_mask], daily_trends_y[valid_daily_mask], label='趋势线 (7日)',
             color=COLORS['duration_line'], linewidth=2.5)
    ax3.set_title('每日学习时长', fontsize=16, weight='bold')
    ax3.set_xticks([])
    ax3.legend()

    # d. 每日效率
    ax4 = axes_trends[1, 1]
    daily_efficiency = trend_data['daily_efficiency_data']
    # 修正：每日图的线状图应使用不透明的线条颜色
    ax4.plot(daily_efficiency['labels'], daily_efficiency['actuals'], label='实际效率', color=COLORS['efficiency_line'],
             alpha=0.5)
    daily_eff_y = np.array(daily_efficiency['trends'], dtype=float)
    daily_eff_x = np.arange(len(daily_efficiency['labels']))
    valid_daily_eff_mask = ~np.isnan(daily_eff_y)
    ax4.plot(daily_eff_x[valid_daily_eff_mask], daily_eff_y[valid_daily_eff_mask], label='趋势线 (7日)',
             color=COLORS['efficiency_line'], linewidth=2.5)
    ax4.set_title('每日学习效率', fontsize=16, weight='bold')
    ax4.set_xticks([])
    ax4.legend()

    fig_trends.tight_layout(rect=[0, 0.03, 1, 0.95])
    trends_img_buffer = io.BytesIO()
    fig_trends.savefig(trends_img_buffer, format='png')
    trends_img_buffer.seek(0)
    plt.close(fig_trends)

    # --- 2. 生成分类图表图片 ---
    if not category_data or not category_data['main']['labels']:
        fig_cats, ax = plt.subplots(figsize=(12, 8), dpi=100)
        ax.text(0.5, 0.5, '没有可用于导出的分类数据', ha='center', va='center', fontsize=18)
        ax.axis('off')
    else:
        num_sub_charts = len(category_data['drilldown'])
        figure_height = 8 + (num_sub_charts * 4)

        fig_cats = plt.figure(figsize=(12, figure_height), dpi=120)
        gs = fig_cats.add_gridspec(num_sub_charts + 1, 1, height_ratios=[4] + [2] * num_sub_charts)
        fig_cats.suptitle(f'{user.username} 的学习分类总览', fontsize=24, weight='bold')

        main_cat_ax = fig_cats.add_subplot(gs[0, 0])
        main_data = category_data['main']
        wedges, texts, autotexts = main_cat_ax.pie(
            main_data['data'],
            labels=main_data['labels'],
            autopct='%1.1f%%',
            startangle=90,
            pctdistance=0.85,
            colors=COLORS['category_palette'],
            wedgeprops=dict(width=0.4, edgecolor='w')
        )
        plt.setp(autotexts, size=10, weight="bold", color="white")
        main_cat_ax.set_title('主分类时长占比', fontsize=16, weight='bold', pad=20)
        main_cat_ax.axis('equal')

        sorted_main_categories = category_data['main']['labels']

        for i, cat_name in enumerate(sorted_main_categories):
            sub_data = category_data['drilldown'].get(cat_name)
            if not sub_data or not sub_data['labels']:
                continue

            sub_ax = fig_cats.add_subplot(gs[i + 1, 0])
            sub_labels = sub_data['labels']
            sub_values = sub_data['data']

            bar_color = COLORS['category_palette'][i % len(COLORS['category_palette'])]

            sub_ax.barh(sub_labels, sub_values, color=bar_color, height=0.5)
            sub_ax.set_title(f'“{cat_name}” 分类下的标签详情 (小时)', fontsize=14, weight='bold')
            sub_ax.invert_yaxis()

            for index, value in enumerate(sub_values):
                sub_ax.text(value, index, f' {value:.1f}h', va='center', fontsize=10)

            sub_ax.spines['top'].set_visible(False)
            sub_ax.spines['right'].set_visible(False)
            sub_ax.spines['left'].set_visible(False)

    fig_cats.tight_layout(rect=[0, 0.03, 1, 0.96])
    category_img_buffer = io.BytesIO()
    fig_cats.savefig(category_img_buffer, format='png')
    category_img_buffer.seek(0)
    plt.close(fig_cats)

    return {
        'trends_image': trends_img_buffer,
        'category_image': category_img_buffer
    }