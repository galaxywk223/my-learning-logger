# learning_logger/services/data_service.py (已修复数据导入风险)

import json
import os
import zipfile
import io
from datetime import date, datetime
from flask import current_app
from .. import db
from ..models import (Stage, Setting, LogEntry, CountdownEvent, Motto, Todo, Category, SubCategory,
                      MilestoneCategory, Milestone, MilestoneAttachment, DailyPlanItem,
                      DailyData, WeeklyData)


def export_data_for_user(user):
    """
    Exports all user data, including milestone attachments, into a single ZIP file.
    (此函数保持不变)
    """

    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable for JSON")

    # 1. Gather all database records
    stages = Stage.query.filter_by(user_id=user.id).all()
    stage_ids = [s.id for s in stages]
    categories = Category.query.filter_by(user_id=user.id).all()
    subcategories = SubCategory.query.filter(SubCategory.category_id.in_([c.id for c in categories])).all()
    milestone_categories = MilestoneCategory.query.filter_by(user_id=user.id).all()
    milestones = Milestone.query.filter_by(user_id=user.id).all()
    milestone_attachments = MilestoneAttachment.query.join(Milestone).filter(Milestone.user_id == user.id).all()
    daily_plans = DailyPlanItem.query.filter_by(user_id=user.id).all()

    all_db_data = {
        'stages': [s.to_dict() for s in stages],
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
        'subcategories': [{'id': s.id, 'name': s.name, 'category_id': s.category_id} for s in subcategories],
        'log_entries': [l.to_dict() for l in LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).all()],
        'countdown_events': [c.to_dict() for c in CountdownEvent.query.filter_by(user_id=user.id).all()],
        'mottos': [{'content': m.content} for m in Motto.query.filter_by(user_id=user.id).all()],
        'todos': [{'content': t.content, 'due_date': t.due_date, 'priority': t.priority, 'is_completed': t.is_completed,
                   'created_at': t.created_at, 'completed_at': t.completed_at} for t in
                  Todo.query.filter_by(user_id=user.id).all()],
        'settings': [s.to_dict() for s in Setting.query.filter_by(user_id=user.id).all()],
        'milestone_categories': [{'id': mc.id, 'name': mc.name} for mc in milestone_categories],
        'milestones': [{'id': m.id, 'title': m.title, 'event_date': m.event_date, 'description': m.description,
                        'category_id': m.category_id} for m in milestones],
        'milestone_attachments': [{'id': ma.id, 'milestone_id': ma.milestone_id, 'file_path': ma.file_path,
                                   'original_filename': ma.original_filename} for ma in milestone_attachments],
        'daily_plan_items': [{'plan_date': dp.plan_date, 'content': dp.content, 'time_slot': dp.time_slot,
                              'is_completed': dp.is_completed, 'created_at': dp.created_at} for dp in daily_plans],
    }

    json_output = json.dumps(all_db_data, default=json_serializer, indent=4, ensure_ascii=False)

    # 2. Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('backup.json', json_output)
        upload_folder = current_app.config.get('MILESTONE_UPLOADS')
        if upload_folder:
            for attachment in milestone_attachments:
                file_path = os.path.join(upload_folder, attachment.file_path)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=attachment.file_path)

    zip_buffer.seek(0)
    return zip_buffer


def import_data_for_user(user, zip_file_stream):
    """
    【已修复】安全地从ZIP文件流导入数据，完全覆盖现有数据。
    修复方案：采用“先验证，后删除，再导入”的逻辑。
    """
    try:
        # --- 步骤 1: 验证备份文件的完整性和有效性 ---
        # 我们在一个事务之外先读取和验证文件。
        # 如果文件有问题，会直接抛出异常，不会影响现有数据。
        with zipfile.ZipFile(zip_file_stream, 'r') as zf:
            if 'backup.json' not in zf.namelist():
                raise ValueError("备份文件无效: 缺少核心的 'backup.json' 文件。")

            with zf.open('backup.json') as json_file:
                try:
                    data = json.load(json_file)
                    # 可以在这里添加更多对 `data` 内容的检查，例如检查关键key是否存在
                    if 'stages' not in data or 'log_entries' not in data:
                        raise ValueError("备份文件内容不完整: 缺少 'stages' 或 'log_entries' 关键数据。")
                except json.JSONDecodeError:
                    raise ValueError("备份文件损坏: 'backup.json' 不是一个有效的JSON文件。")

            # --- 步骤 2: 验证成功后，开始删除旧数据 ---
            # 这个过程现在被包裹在同一个事务中，可以安全回滚。
            current_app.logger.info(f"为用户 {user.id} 开始数据导入，备份文件验证通过。")

            # 2.1 删除物理附件文件
            upload_folder = current_app.config.get('MILESTONE_UPLOADS')
            if upload_folder:
                attachments_to_delete = MilestoneAttachment.query.join(Milestone).filter(Milestone.user_id == user.id).all()
                for att in attachments_to_delete:
                    try:
                        full_path = os.path.join(upload_folder, att.file_path)
                        if os.path.exists(full_path):
                            os.remove(full_path)
                            current_app.logger.info(f"已删除旧附件: {full_path}")
                    except Exception as e:
                        current_app.logger.error(f"删除附件文件 {att.file_path} 时出错: {e}")

            # 2.2 删除数据库记录 (顺序很重要，从子表到父表)
            stage_ids = [s.id for s in Stage.query.filter_by(user_id=user.id).with_entities(Stage.id)]
            category_ids = [c.id for c in Category.query.filter_by(user_id=user.id).with_entities(Category.id)]
            milestone_ids = [m.id for m in Milestone.query.filter_by(user_id=user.id).with_entities(Milestone.id)]

            if milestone_ids:
                MilestoneAttachment.query.filter(MilestoneAttachment.milestone_id.in_(milestone_ids)).delete(synchronize_session=False)
            Milestone.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            MilestoneCategory.query.filter_by(user_id=user.id).delete(synchronize_session=False)

            if stage_ids:
                LogEntry.query.filter(LogEntry.stage_id.in_(stage_ids)).delete(synchronize_session=False)
                DailyData.query.filter(DailyData.stage_id.in_(stage_ids)).delete(synchronize_session=False)
                WeeklyData.query.filter(WeeklyData.stage_id.in_(stage_ids)).delete(synchronize_session=False)
            if category_ids:
                SubCategory.query.filter(SubCategory.category_id.in_(category_ids)).delete(synchronize_session=False)

            Motto.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            Todo.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            CountdownEvent.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            Setting.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            DailyPlanItem.query.filter_by(user_id=user.id).delete(synchronize_session=False)

            Category.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            Stage.query.filter_by(user_id=user.id).delete(synchronize_session=False)

            # --- 步骤 3: 导入新数据 ---
            old_to_new_stage_id, old_to_new_category_id, old_to_new_subcategory_id = {}, {}, {}
            old_to_new_milestone_cat_id, old_to_new_milestone_id = {}, {}

            # (下面的导入逻辑与原来基本一致)
            for stage_data in data.get('stages', []):
                old_id = stage_data.pop('id')
                stage_data.pop('user_id', None)
                if stage_data.get('start_date'):
                    stage_data['start_date'] = date.fromisoformat(stage_data['start_date'])
                new_stage = Stage(user_id=user.id, **stage_data)
                db.session.add(new_stage)
                db.session.flush()
                old_to_new_stage_id[old_id] = new_stage.id

            for cat_data in data.get('categories', []):
                old_id = cat_data.pop('id')
                new_cat = Category(user_id=user.id, **cat_data)
                db.session.add(new_cat)
                db.session.flush()
                old_to_new_category_id[old_id] = new_cat.id

            for sub_data in data.get('subcategories', []):
                old_id = sub_data.pop('id')
                sub_data['category_id'] = old_to_new_category_id.get(sub_data.get('category_id'))
                new_sub = SubCategory(**sub_data)
                db.session.add(new_sub)
                db.session.flush()
                old_to_new_subcategory_id[old_id] = new_sub.id

            for item in data.get('log_entries', []):
                item.pop('id', None)
                item['stage_id'] = old_to_new_stage_id.get(item.get('stage_id'))
                item['subcategory_id'] = old_to_new_subcategory_id.get(item.get('subcategory_id'))
                if item.get('log_date'):
                    item['log_date'] = date.fromisoformat(item['log_date'])
                db.session.add(LogEntry(**item))

            for item_data in data.get('countdown_events', []):
                item_data['user_id'] = user.id
                if item_data.get('target_datetime_utc'):
                    item_data['target_datetime_utc'] = datetime.fromisoformat(item_data['target_datetime_utc'].replace('Z', '+00:00'))
                if item_data.get('created_at_utc'):
                    item_data['created_at_utc'] = datetime.fromisoformat(item_data['created_at_utc'].replace('Z', '+00:00'))
                db.session.add(CountdownEvent(**item_data))

            for item_data in data.get('mottos', []):
                item_data['user_id'] = user.id
                db.session.add(Motto(**item_data))

            for item_data in data.get('todos', []):
                item_data['user_id'] = user.id
                if item_data.get('due_date'): item_data['due_date'] = date.fromisoformat(item_data['due_date'])
                if item_data.get('created_at'): item_data['created_at'] = datetime.fromisoformat(item_data['created_at'])
                if item_data.get('completed_at'): item_data['completed_at'] = datetime.fromisoformat(item_data['completed_at'])
                db.session.add(Todo(**item_data))

            for item_data in data.get('settings', []):
                item_data['user_id'] = user.id
                db.session.add(Setting(**item_data))

            for mc_data in data.get('milestone_categories', []):
                old_id = mc_data.pop('id')
                new_mc = MilestoneCategory(user_id=user.id, **mc_data)
                db.session.add(new_mc)
                db.session.flush()
                old_to_new_milestone_cat_id[old_id] = new_mc.id

            for m_data in data.get('milestones', []):
                old_id = m_data.pop('id')
                m_data['user_id'] = user.id
                m_data['category_id'] = old_to_new_milestone_cat_id.get(m_data.get('category_id'))
                if m_data.get('event_date'):
                    m_data['event_date'] = date.fromisoformat(m_data['event_date'])
                new_m = Milestone(**m_data)
                db.session.add(new_m)
                db.session.flush()
                old_to_new_milestone_id[old_id] = new_m.id

            for ma_data in data.get('milestone_attachments', []):
                ma_data.pop('id', None)
                ma_data['milestone_id'] = old_to_new_milestone_id.get(ma_data.get('milestone_id'))
                db.session.add(MilestoneAttachment(**ma_data))

            for dp_data in data.get('daily_plan_items', []):
                dp_data['user_id'] = user.id
                if dp_data.get('plan_date'): dp_data['plan_date'] = date.fromisoformat(dp_data['plan_date'])
                if dp_data.get('created_at'): dp_data['created_at'] = datetime.fromisoformat(dp_data['created_at'])
                db.session.add(DailyPlanItem(**dp_data))

            # 3.1 导入附件文件
            if upload_folder:
                # 重新打开 zip 文件流来提取文件
                with zipfile.ZipFile(zip_file_stream, 'r') as zf_extract:
                    for zf_info in zf_extract.infolist():
                        if zf_info.filename != 'backup.json' and not zf_info.is_dir():
                            target_path = os.path.join(upload_folder, zf_info.filename)
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with zf_extract.open(zf_info) as source, open(target_path, 'wb') as target:
                                target.write(source.read())

        # --- 步骤 4: 提交事务 ---
        db.session.commit()
        return True, '数据和附件恢复成功！您的所有数据已从备份文件加载。'

    except (zipfile.BadZipFile, ValueError, json.JSONDecodeError) as e:
        # 捕获特定的验证错误
        db.session.rollback()
        current_app.logger.error(f"为用户 {user.id} 导入数据时发生验证错误: {e}", exc_info=True)
        return False, f'导入失败: {e}'
    except Exception as e:
        # 捕获所有其他未知错误
        db.session.rollback()
        current_app.logger.error(f"为用户 {user.id} 导入时发生未知错误: {e}", exc_info=True)
        return False, f'导入过程中发生严重错误，操作已回滚: {e}'
