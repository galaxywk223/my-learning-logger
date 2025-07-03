# learning_logger/services/data_service.py (FINAL FIX for SQLAlchemy delete restrictions)

import json
from datetime import date, datetime
from flask import current_app
from .. import db
from ..models import Stage, Setting, LogEntry, CountdownEvent, Motto, Todo, Category, SubCategory


def export_data_for_user(user):
    # This function is correct and remains unchanged.
    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable for JSON")

    stages = Stage.query.filter_by(user_id=user.id).all()
    stage_ids = [s.id for s in stages]

    categories = Category.query.filter_by(user_id=user.id).all()
    category_ids = [c.id for c in categories]
    subcategories = SubCategory.query.filter(SubCategory.category_id.in_(category_ids)).all()

    all_data = {
        'stages': [s.to_dict() for s in stages],
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
        'subcategories': [{'id': s.id, 'name': s.name, 'category_id': s.category_id} for s in subcategories],
        'log_entries': [l.to_dict() for l in LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).all()],
        'countdown_events': [c.to_dict() for c in CountdownEvent.query.filter_by(user_id=user.id).all()],
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
        ],
        'settings': [s.to_dict() for s in Setting.query.filter_by(user_id=user.id).all()]
    }
    return json.dumps(all_data, default=json_serializer, indent=4, ensure_ascii=False)


def import_data_for_user(user, file_stream):
    """
    Imports data from a JSON file stream, completely overwriting existing data.
    """
    try:
        # --- FINAL FIX: Delete data without using joins ---
        # Step 1: Clean slate.
        # Collect all IDs first.
        stage_ids_to_delete = [s.id for s in Stage.query.filter_by(user_id=user.id).with_entities(Stage.id)]
        category_ids_to_delete = [c.id for c in Category.query.filter_by(user_id=user.id).with_entities(Category.id)]

        # Delete all child objects using the collected IDs.
        if stage_ids_to_delete:
            LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids_to_delete)).delete(synchronize_session=False)
            DailyData.query.filter(DailyData.stage_id.in_(stage_ids_to_delete)).delete(synchronize_session=False)
            WeeklyData.query.filter(WeeklyData.stage_id.in_(stage_ids_to_delete)).delete(synchronize_session=False)

        if category_ids_to_delete:
            SubCategory.query.filter(SubCategory.category_id.in_(category_ids_to_delete)).delete(
                synchronize_session=False)

        # Delete all other user-specific data directly.
        Motto.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        Todo.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        CountdownEvent.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        Setting.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Finally, delete the parent objects themselves.
        if stage_ids_to_delete:
            Stage.query.filter(Stage.id.in_(stage_ids_to_delete)).delete(synchronize_session=False)
        if category_ids_to_delete:
            Category.query.filter(Category.id.in_(category_ids_to_delete)).delete(synchronize_session=False)

        db.session.commit()
        # --- FIX END ---

        # Step 2: A new transaction for importing data.
        data = json.load(file_stream)

        # ... (The rest of the import logic is correct and remains unchanged) ...
        old_to_new_stage_id = {}
        for stage_data in data.get('stages', []):
            old_id = stage_data.pop('id')
            stage_data['user_id'] = user.id
            if stage_data.get('start_date'):
                stage_data['start_date'] = date.fromisoformat(stage_data['start_date'])
            new_stage = Stage(**stage_data)
            db.session.add(new_stage)
            db.session.flush()
            old_to_new_stage_id[old_id] = new_stage.id

        old_to_new_category_id = {}
        for cat_data in data.get('categories', []):
            old_id = cat_data.pop('id')
            cat_data['user_id'] = user.id
            new_cat = Category(**cat_data)
            db.session.add(new_cat)
            db.session.flush()
            old_to_new_category_id[old_id] = new_cat.id

        old_to_new_subcategory_id = {}
        for sub_data in data.get('subcategories', []):
            old_id = sub_data.pop('id')
            old_cat_id = sub_data.get('category_id')
            new_cat_id = old_to_new_category_id.get(old_cat_id)
            if not new_cat_id:
                current_app.logger.warning(
                    f"Skipping subcategory '{sub_data.get('name')}' because its parent category ID '{old_cat_id}' was not found.")
                continue
            sub_data['category_id'] = new_cat_id
            new_sub = SubCategory(**sub_data)
            db.session.add(new_sub)
            db.session.flush()
            old_to_new_subcategory_id[old_id] = new_sub.id

        for item in data.get('log_entries', []):
            item.pop('id', None)
            item['stage_id'] = old_to_new_stage_id.get(item.get('stage_id'))
            item['subcategory_id'] = old_to_new_subcategory_id.get(item.get('subcategory_id'))
            if not item.get('stage_id'):
                current_app.logger.warning(f"Skipping log entry because its stage_id was not found.")
                continue
            if item.get('log_date'):
                item['log_date'] = date.fromisoformat(item['log_date'])
            db.session.add(LogEntry(**item))

        for item in data.get('countdown_events', []):
            item.pop('id', None)
            item['user_id'] = user.id
            if item.get('target_datetime_utc'):
                dt_str = item['target_datetime_utc'].replace('Z', '+00:00')
                item['target_datetime_utc'] = datetime.fromisoformat(dt_str)
            if item.get('created_at_utc'):
                created_dt_str = item['created_at_utc'].replace('Z', '+00:00')
                item['created_at_utc'] = datetime.fromisoformat(created_dt_str)
            db.session.add(CountdownEvent(**item))

        for item in data.get('mottos', []):
            item['user_id'] = user.id
            db.session.add(Motto(**item))

        for item in data.get('todos', []):
            item['user_id'] = user.id
            if item.get('due_date'): item['due_date'] = date.fromisoformat(item['due_date'])
            if item.get('created_at'): item['created_at'] = datetime.fromisoformat(item['created_at'])
            if item.get('completed_at'): item['completed_at'] = datetime.fromisoformat(item['completed_at'])
            db.session.add(Todo(**item))

        for item in data.get('settings', []):
            item['user_id'] = user.id
            db.session.add(Setting(**item))

        db.session.commit()
        return True, '数据恢复成功！您的所有数据已从备份文件加载。'

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"为用户 {user.id} 导入JSON时出错: {e}", exc_info=True)
        return False, f'导入过程中发生严重错误，操作已回滚: {e}'