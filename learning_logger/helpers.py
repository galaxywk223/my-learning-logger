# /learning_logger/helpers.py

import re
import numpy as np
from datetime import date, datetime
from .models import Setting


def get_setting(key, default=None):
    """获取设置项的值"""
    setting = Setting.query.get(key)
    return setting.value if setting else default


def get_custom_week_info(log_date, start_date):
    """根据自定义起始日期计算周信息"""
    if not isinstance(log_date, date):
        log_date = date.fromisoformat(log_date)
    days_diff = (log_date - start_date).days
    if days_diff < 0:
        return start_date.year, 1
    return log_date.year, (days_diff // 7) + 1


def parse_csv_duration(duration_str):
    """解析CSV中的时长字符串"""
    if not isinstance(duration_str, str) or not duration_str.strip():
        return 0
    duration_str = duration_str.strip().lower()
    try:
        if 'h' in duration_str:
            return int(float(duration_str.replace('h', '')) * 60)
        if 'min' in duration_str:
            return int(float(duration_str.replace('min', '')))
        if '上课' in duration_str:
            return 90
        return int(float(duration_str) * 60)
    except (ValueError, TypeError):
        return 0


def parse_csv_date(date_str):
    """解析CSV中的日期字符串"""
    if not isinstance(date_str, str):
        return None
    try:
        parts = date_str.replace('月', '-').replace('日', '').split('-')
        return date(datetime.now().year, int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, TypeError):
        return None


def parse_efficiency_to_numeric(eff_str):
    """将各种格式的效率描述转换为0-5的数值"""
    if not isinstance(eff_str, str) or not eff_str.strip():
        # [改进] 返回 np.nan 而不是 0，以便在图表中正确处理缺失值
        return np.nan
    eff_str = eff_str.strip()
    match = re.match(r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)', eff_str)
    if match:
        num, den = float(match.group(1)), float(match.group(2))
        return (num / den) * 5 if den != 0 else np.nan
    match = re.match(r'(\d+\.?\d*)\s*%', eff_str)
    if match:
        return (float(match.group(1)) / 100) * 5
    match = re.match(r'(\d+\.?\d*)', eff_str)
    if match:
        val = float(match.group(1))
        # 保证评分在合理范围
        return val if 0 <= val <= 5 else np.nan
    mapping = {"高效": 5, "良好": 4, "不错": 4, "一般": 3, "还行": 3, "及格": 3, "较差": 2, "差": 2, "很差": 1,
               "低效": 1}
    return float(mapping.get(eff_str, np.nan))


def moving_average(data, window_size=7):
    """
    [核心 Bug 修复] 计算移动平均值，此版本会正确地忽略 NaN 值。
    之前的版本会将 NaN 转换为 0，导致移动平均线被错误地拉低。
    """
    if len(data) < window_size:
        return np.array([])

    result = []
    # 遍历所有可能的窗口
    for i in range(len(data) - window_size + 1):
        window = data[i: i + window_size]
        # 从窗口中只选择有效的数值（非 NaN）
        valid_values = window[~np.isnan(window)]

        # 如果窗口中至少有一个有效值，则计算其平均值
        # 否则，该窗口的移动平均值也为 NaN
        if len(valid_values) > 0:
            result.append(np.mean(valid_values))
        else:
            result.append(np.nan)

    return np.array(result)


def setup_template_filters(app):
    @app.template_filter('mood_emoji')
    def mood_emoji_filter(mood_level):
        """将心情等级转换为表情符号"""
        emoji_map = {
            5: '😃',  # 非常好
            4: '😊',  # 良好
            3: '😐',  # 一般
            2: '😟',  # 不佳
            1: '😠',  # 很差
        }
        return emoji_map.get(mood_level, '🤔')  # 如果找不到对应等级，返回一个思考表情
