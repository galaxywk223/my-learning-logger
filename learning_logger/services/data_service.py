# learning_logger/services/data_service.py

import json
from datetime import date, datetime
from flask import current_app
from .. import db
# 引入 Stage 并调整模型导入顺序
from ..models import Stage, Setting, WeeklyData, DailyData, LogEntry, CountdownEvent


def export_data_for_user(user):
    """导出指定用户的所有数据为 JSON 字符串，包含阶段信息。"""

    def json_serializer(obj):
        """处理 JSON 序列化中的日期和时间对象。"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable for JSON")

    # 获取用户的所有阶段
    stages = Stage.query.filter_by(user_id=user.id).all()
    stage_ids = [s.id for s in stages]

    all_data = {
        'stages': [s.to_dict() for s in stages],
        'settings': [s.to_dict() for s in Setting.query.filter_by(user_id=user.id).all()],
        'weekly_data': [w.to_dict() for w in WeeklyData.query.filter(WeeklyData.stage_id.in_(stage_ids)).all()],
        'daily_data': [d.to_dict() for d in DailyData.query.filter(DailyData.stage_id.in_(stage_ids)).all()],
        'log_entries': [l.to_dict() for l in LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).all()],
        'countdown_events': [c.to_dict() for c in CountdownEvent.query.filter_by(user_id=user.id).all()],
    }

    return json.dumps(all_data, default=json_serializer, indent=4, ensure_ascii=False)


def import_data_for_user(user, file_stream):
    """
    从文件流为指定用户导入包含阶段的数据。
    这是一个事务性操作，保证数据要么全部导入成功，要么全部回滚。
    """
    try:
        # 1. 清空该用户与阶段相关的所有数据
        # 级联删除会自动处理 WeeklyData, DailyData, LogEntry
        Stage.query.filter_by(user_id=user.id).delete()
        # 单独删除其他用户数据
        CountdownEvent.query.filter_by(user_id=user.id).delete()
        Setting.query.filter_by(user_id=user.id).delete()
        # 先提交一次清空操作
        db.session.commit()

        data = json.load(file_stream)

        # 2. 导入 Stages 并建立新旧 ID 的映射
        old_to_new_stage_id = {}
        if 'stages' in data:
            for stage_data in data['stages']:
                old_id = stage_data.pop('id')
                stage_data['user_id'] = user.id
                if 'start_date' in stage_data:
                    stage_data['start_date'] = date.fromisoformat(stage_data['start_date'])

                new_stage = Stage(**stage_data)
                db.session.add(new_stage)
                db.session.flush()  # flush() 使 new_stage.id 可用
                old_to_new_stage_id[old_id] = new_stage.id

        # 3. 导入依赖于 Stage 的数据
        data_models = {'weekly_data': WeeklyData, 'daily_data': DailyData, 'log_entries': LogEntry}
        for key, model in data_models.items():
            if key in data:
                for item in data[key]:
                    item.pop('id', None)
                    # 使用映射表更新 stage_id
                    old_stage_id = item.get('stage_id')
                    if old_stage_id in old_to_new_stage_id:
                        item['stage_id'] = old_to_new_stage_id[old_stage_id]
                    else:
                        # 如果找不到对应的 stage，可以选择跳过或抛出错误
                        current_app.logger.warning(f"跳过记录，因为找不到对应的 stage_id: {old_stage_id}")
                        continue

                    if 'log_date' in item:
                        item['log_date'] = date.fromisoformat(item['log_date'])

                    db.session.add(model(**item))

        # 4. 导入不依赖于 Stage 的数据
        if 'settings' in data:
            for item in data['settings']:
                item['user_id'] = user.id
                db.session.add(Setting(**item))

        if 'countdown_events' in data:
            for item in data['countdown_events']:
                item.pop('id', None)
                item['user_id'] = user.id
                if 'target_datetime_utc' in item:
                    item['target_datetime_utc'] = datetime.fromisoformat(
                        item['target_datetime_utc'].replace('Z', '+00:00'))
                db.session.add(CountdownEvent(**item))

        # 5. 提交整个事务
        db.session.commit()
        return True, '数据恢复成功！您的所有阶段和记录已从备份文件加载。'

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"为用户 {user.id} 导入JSON时出错: {e}")
        return False, f'导入过程中发生严重错误，操作已回滚: {e}'