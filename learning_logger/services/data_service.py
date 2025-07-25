# 文件路径: learning_logger/services/data_service.py
import io
import json
import os
import zipfile
from datetime import date, datetime
from flask import current_app
from werkzeug.utils import secure_filename

from .. import db
from ..models import (
    User, Stage, Category, SubCategory, LogEntry, DailyData, WeeklyData,
    Motto, Todo, Milestone, MilestoneCategory, MilestoneAttachment,
    DailyPlanItem, Setting, CountdownEvent
)

MODELS_TO_HANDLE = [
    Setting, Stage, Category, SubCategory, LogEntry, DailyData, WeeklyData,
    Motto, Todo, MilestoneCategory, Milestone, MilestoneAttachment,
    CountdownEvent, DailyPlanItem
]


def _clear_user_data(user):
    """
    在导入前，安全地清空用户的所有关联数据。
    这是一个关键步骤，以避免主键或外键冲突。
    """
    current_app.logger.info(f"Starting to clear all data for user: {user.username} (ID: {user.id})")

    upload_folder = current_app.config.get('MILESTONE_UPLOADS')
    if upload_folder:
        user_upload_folder = os.path.join(upload_folder, str(user.id))
        if os.path.exists(user_upload_folder):
            for filename in os.listdir(user_upload_folder):
                try:
                    os.remove(os.path.join(user_upload_folder, filename))
                except Exception as e:
                    current_app.logger.error(f"Failed to remove attachment file {filename}: {e}")
    current_app.logger.info("Cleared physical milestone attachments.")

    MilestoneAttachment.query.filter(MilestoneAttachment.milestone.has(user_id=user.id)).delete(
        synchronize_session=False)
    LogEntry.query.filter(LogEntry.stage.has(user_id=user.id)).delete(synchronize_session=False)
    SubCategory.query.filter(SubCategory.category.has(user_id=user.id)).delete(synchronize_session=False)

    DailyData.query.filter(DailyData.stage.has(user_id=user.id)).delete(synchronize_session=False)
    WeeklyData.query.filter(WeeklyData.stage.has(user_id=user.id)).delete(synchronize_session=False)
    Milestone.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    Motto.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Todo.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    CountdownEvent.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    DailyPlanItem.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Setting.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Category.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    MilestoneCategory.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Stage.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    db.session.commit()
    current_app.logger.info(f"Successfully cleared all database entries for user: {user.username}")


def export_data_for_user(user):
    """
    将指定用户的所有数据导出到一个ZIP压缩包的内存缓冲区中。
    """
    current_app.logger.info(f"Starting data export for user: {user.username}")
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:

        for model in MODELS_TO_HANDLE:

            records = model.query.filter(getattr(model, 'user_id', None) == user.id).all()
            if hasattr(model, 'stage') and not hasattr(model, 'user_id'):
                records = model.query.join(Stage).filter(Stage.user_id == user.id).all()
            if hasattr(model, 'milestone') and not hasattr(model, 'user_id'):
                records = model.query.join(Milestone).filter(Milestone.user_id == user.id).all()

            data = [record.to_dict() for record in records]
            json_data = json.dumps(data, indent=4, ensure_ascii=False)
            zf.writestr(f'data/{model.__tablename__}.json', json_data)

        current_app.logger.info("Exported all database tables to JSON.")

        upload_folder = current_app.config.get('MILESTONE_UPLOADS')
        user_upload_folder = os.path.join(upload_folder, str(user.id))
        if upload_folder and os.path.exists(user_upload_folder):
            for filename in os.listdir(user_upload_folder):
                file_path = os.path.join(user_upload_folder, filename)

                zf.write(file_path, arcname=f'attachments/{filename}')
            current_app.logger.info("Exported all milestone attachments.")

    buffer.seek(0)
    return buffer


def import_data_for_user(user, zip_file_stream):
    """
    从一个ZIP文件流中为指定用户导入数据，此操作会先清空用户现有数据。
    """
    current_app.logger.info(f"Starting data import for user: {user.username}")
    try:

        _clear_user_data(user)

        with zipfile.ZipFile(zip_file_stream, 'r') as zf:

            model_map = {model.__tablename__: model for model in MODELS_TO_HANDLE}

            import_order = [
                'setting', 'stage', 'category', 'milestone_category', 'motto',
                'todo', 'countdown_event', 'daily_plan_item',
                'sub_category', 'milestone',
                'log_entry', 'daily_data', 'weekly_data', 'milestone_attachment'
            ]

            for table_name in import_order:
                model = model_map.get(table_name)
                if not model:
                    continue

                json_path = f'data/{table_name}.json'
                if json_path in zf.namelist():
                    with zf.open(json_path) as json_file:
                        records = json.load(json_file)
                        for record_data in records:

                            if 'user_id' in model.__table__.columns:
                                record_data['user_id'] = user.id

                            # --- MODIFICATION START ---
                            # 修正了日期和时间字符串的解析逻辑
                            for key, value in record_data.items():
                                # 只处理非空字符串
                                if isinstance(value, str) and value:
                                    # 更稳健地判断是否为日期时间字段，例如检查结尾是否为 _at 或 _utc
                                    if 'datetime' in key or key.endswith('_at') or key.endswith('_utc'):
                                        try:
                                            # fromisoformat 可以处理带或不带时区信息的ISO格式字符串
                                            dt_obj = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                            # 存储为无时区信息的datetime对象以兼容SQLite
                                            record_data[key] = dt_obj.replace(tzinfo=None)
                                        except ValueError:
                                            current_app.logger.warning(
                                                f"Could not parse datetime string '{value}' for key '{key}'")
                                            pass
                                    elif 'date' in key:
                                        try:
                                            record_data[key] = date.fromisoformat(value)
                                        except ValueError:
                                            current_app.logger.warning(
                                                f"Could not parse date string '{value}' for key '{key}'")
                                            pass
                            # --- MODIFICATION END ---

                            db.session.add(model(**record_data))

            current_app.logger.info("Imported all JSON data to database session.")

            upload_folder = current_app.config.get('MILESTONE_UPLOADS')
            if upload_folder:
                user_upload_folder = os.path.join(upload_folder, str(user.id))
                os.makedirs(user_upload_folder, exist_ok=True)
                for file_info in zf.infolist():
                    if file_info.filename.startswith('attachments/'):
                        zf.extract(file_info, path=user_upload_folder)

                        source_path = os.path.join(user_upload_folder, file_info.filename)
                        dest_path = os.path.join(user_upload_folder, os.path.basename(file_info.filename))
                        os.rename(source_path, dest_path)

                if os.path.exists(os.path.join(user_upload_folder, 'attachments')):
                    os.rmdir(os.path.join(user_upload_folder, 'attachments'))
                current_app.logger.info("Extracted all attachments.")

        db.session.commit()
        current_app.logger.info("Data import committed successfully.")
        return True, "数据导入成功！所有旧数据已被覆盖。"

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Data import failed for user {user.username}: {e}", exc_info=True)
        return False, f"导入失败，发生严重错误: {e}"
