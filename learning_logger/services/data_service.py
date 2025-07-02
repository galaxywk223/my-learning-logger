# learning_logger/services/data_service.py (Completely Fixed Export/Import)

import json
from datetime import date, datetime
from flask import current_app
from .. import db
from ..models import Stage, Setting, LogEntry, CountdownEvent, Motto, Todo


def export_data_for_user(user):
    """
    【完全修正版】导出指定用户的所有数据。
    确保 'mottos' 和 'todos' 等新模型被正确导出。
    """

    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable for JSON")

    # The user's stages are the root for most data
    stages = Stage.query.filter_by(user_id=user.id).all()
    stage_ids = [s.id for s in stages]

    all_data = {
        'stages': [s.to_dict() for s in stages],
        'settings': [s.to_dict() for s in Setting.query.filter_by(user_id=user.id).all()],
        'log_entries': [l.to_dict() for l in LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).all()],
        'countdown_events': [c.to_dict() for c in CountdownEvent.query.filter_by(user_id=user.id).all()],
        # FIXED: Ensure new models are exported
        'mottos': [{'content': m.content} for m in Motto.query.filter_by(user_id=user.id).all()],
        'todos': [
            {
                'content': t.content,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'priority': t.priority,
                'is_completed': t.is_completed,
                'created_at': t.created_at.isoformat(),
                'completed_at': t.completed_at.isoformat() if t.completed_at else None
            } for t in Todo.query.filter_by(user_id=user.id).all()
        ]
    }
    # We no longer export 'weekly_data' or 'daily_data' as they are calculated automatically.
    return json.dumps(all_data, default=json_serializer, indent=4, ensure_ascii=False)


def import_data_for_user(user, file_stream):
    """
    【完全修正版】导入数据，确保所有模型都被正确处理。
    """
    try:
        # Step 1: Clean slate. A separate transaction for cleaning up data.
        Stage.query.filter_by(user_id=user.id).delete()
        CountdownEvent.query.filter_by(user_id=user.id).delete()
        Setting.query.filter_by(user_id=user.id).delete()
        Motto.query.filter_by(user_id=user.id).delete()
        Todo.query.filter_by(user_id=user.id).delete()
        db.session.commit()

        # Step 2: A new transaction for importing data.
        data = json.load(file_stream)

        # --- Import Stages ---
        old_to_new_stage_id = {}
        if 'stages' in data:
            for stage_data in data['stages']:
                old_id = stage_data.pop('id', None)  # Use .pop for safety
                stage_data['user_id'] = user.id
                if 'start_date' in stage_data and stage_data['start_date']:
                    stage_data['start_date'] = date.fromisoformat(stage_data['start_date'])
                new_stage = Stage(**stage_data)
                db.session.add(new_stage)
                if old_id is not None:
                    db.session.flush()  # Makes new_stage.id available
                    old_to_new_stage_id[old_id] = new_stage.id

        # --- Import Log Entries ---
        if 'log_entries' in data:
            for item in data['log_entries']:
                item.pop('id', None)
                old_stage_id = item.get('stage_id')
                # Map to the new stage ID created in this session
                if old_stage_id in old_to_new_stage_id:
                    item['stage_id'] = old_to_new_stage_id[old_stage_id]
                else:
                    # If a log entry's stage doesn't exist, we must skip it.
                    current_app.logger.warning(
                        f"Skipping log entry because its stage_id '{old_stage_id}' was not found.")
                    continue

                if 'log_date' in item and item['log_date']:
                    item['log_date'] = date.fromisoformat(item['log_date'])
                db.session.add(LogEntry(**item))

        # --- FIXED: Import Settings ---
        if 'settings' in data:
            for item in data['settings']:
                item['user_id'] = user.id
                db.session.add(Setting(**item))

        # --- FIXED: Import Countdown Events ---
        if 'countdown_events' in data:
            for item in data['countdown_events']:
                item.pop('id', None)
                item['user_id'] = user.id
                if 'target_datetime_utc' in item and item['target_datetime_utc']:
                    # Handle Z suffix for UTC timezone
                    dt_str = item['target_datetime_utc'].replace('Z', '+00:00')
                    item['target_datetime_utc'] = datetime.fromisoformat(dt_str)
                db.session.add(CountdownEvent(**item))

        # --- FIXED: Import Mottos ---
        if 'mottos' in data:
            for item in data['mottos']:
                item['user_id'] = user.id
                db.session.add(Motto(**item))

        # --- FIXED: Import Todos ---
        if 'todos' in data:
            for item in data['todos']:
                item['user_id'] = user.id
                # Handle possible null dates
                if 'due_date' in item and item['due_date']:
                    item['due_date'] = date.fromisoformat(item['due_date'])
                if 'created_at' in item and item['created_at']:
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                if 'completed_at' in item and item['completed_at']:
                    item['completed_at'] = datetime.fromisoformat(item['completed_at'])
                db.session.add(Todo(**item))

        # Step 3: Commit everything in one go.
        db.session.commit()
        return True, '数据恢复成功！您的所有数据已从备份文件加载。'

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"为用户 {user.id} 导入JSON时出错: {e}", exc_info=True)
        return False, f'导入过程中发生严重错误，操作已回滚: {e}'