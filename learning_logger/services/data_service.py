# learning_logger/services/data_service.py

import json
from datetime import date, datetime
from .. import db
from ..models import Setting, WeeklyData, DailyData, LogEntry, CountdownEvent


def export_data_for_user(user):
    """
    导出指定用户的所有数据为 JSON 字符串。

    :param user: 用户对象
    :return: 包含所有数据的 JSON 格式字符串
    """

    def json_serializer(obj):
        """处理 JSON 序列化中的日期和时间对象。"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable for JSON")

    all_data = {
        'settings': [s.to_dict() for s in Setting.query.filter_by(user_id=user.id).all()],
        'weekly_data': [w.to_dict() for w in WeeklyData.query.filter_by(user_id=user.id).all()],
        'daily_data': [d.to_dict() for d in DailyData.query.filter_by(user_id=user.id).all()],
        'log_entries': [l.to_dict() for l in LogEntry.query.filter_by(user_id=user.id).all()],
        'countdown_events': [c.to_dict() for c in CountdownEvent.query.filter_by(user_id=user.id).all()],
    }

    return json.dumps(all_data, default=json_serializer, indent=4, ensure_ascii=False)


def import_data_for_user(user, file_stream):
    """
    从文件流为指定用户导入数据。
    该过程是事务性的：要么全部成功，要么全部回滚。

    :param user: 用户对象
    :param file_stream: 从上传文件获取的文件流 (e.g., request.files['file'].stream)
    :return: 一个元组 (success_boolean, message_string)
    """
    # 事务开始
    try:
        # 1. 清空该用户的所有现有数据
        LogEntry.query.filter_by(user_id=user.id).delete()
        DailyData.query.filter_by(user_id=user.id).delete()
        WeeklyData.query.filter_by(user_id=user.id).delete()
        CountdownEvent.query.filter_by(user_id=user.id).delete()
        Setting.query.filter_by(user_id=user.id).delete()

        # 2. 解析并加载新数据
        data = json.load(file_stream)
        model_map = {
            'settings': Setting, 'countdown_events': CountdownEvent,
            'weekly_data': WeeklyData, 'daily_data': DailyData, 'log_entries': LogEntry,
        }

        date_fields = {'log_date'}
        datetime_fields = {'target_datetime_utc'}

        for key, model in model_map.items():
            if key in data:
                for item in data[key]:
                    # 自动转换日期和时间字符串
                    for field in date_fields:
                        if field in item and isinstance(item[field], str):
                            item[field] = date.fromisoformat(item[field])
                    for field in datetime_fields:
                        if field in item and isinstance(item[field], str):
                            item[field] = datetime.fromisoformat(item[field].replace('Z', '+00:00'))

                    # 强制设置当前 user_id，确保数据归属正确
                    item['user_id'] = user.id
                    # 移除可能存在的旧 id，让数据库自动生成新主键
                    item.pop('id', None)

                    db.session.add(model(**item))

        # 3. 提交事务
        db.session.commit()
        return True, '数据恢复成功！您的所有数据已从备份文件加载。'

    except Exception as e:
        # 如果任何步骤出错，则回滚所有操作
        db.session.rollback()
        # 在实际应用中，这里应该使用 current_app.logger 记录错误
        print(f"为用户 {user.id} 导入JSON时出错: {e}")
        return False, f'导入过程中发生严重错误，操作已回滚: {e}'