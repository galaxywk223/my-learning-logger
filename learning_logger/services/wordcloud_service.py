# learning_logger/services/wordcloud_service.py (NEW FILE)

import io
import os
import random
import jieba
import numpy as np
from PIL import Image
from wordcloud import WordCloud
from flask import current_app

from ..models import Stage, LogEntry


def _load_stopwords():
    """从静态文件加载停用词。"""
    stopwords_path = os.path.join(current_app.static_folder, 'cn_stopwords.txt')
    if os.path.exists(stopwords_path):
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f}
    return set()


def _get_mask_image():
    """从静态文件夹随机选择并加载一个遮罩图片。"""
    try:
        masks_dir = os.path.join(current_app.static_folder, 'images', 'masks')
        available_masks = [f for f in os.listdir(masks_dir) if f.endswith('.png')]
        if not available_masks:
            raise FileNotFoundError("No mask images found in the masks directory.")

        selected_mask_file = random.choice(available_masks)
        mask_path = os.path.join(masks_dir, selected_mask_file)
        return np.array(Image.open(mask_path).convert("RGB"))
    except Exception as e:
        current_app.logger.error(f"Error loading mask: {e}")
        return None


def _theme_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    """为词云定义一个自定义的主题颜色函数。"""
    colors = ["#A78BFA", "#8B5CF6", "#F59E0B", "#B45309", "#4C1D95"]
    return random.choice(colors)


def generate_wordcloud_for_user(user, stage_id=None):
    """
    为用户生成一个美化的词云图片。

    :param user: 当前用户对象。
    :param stage_id: (可选) 要筛选的阶段ID。
    :return: 包含PNG图片的BytesIO缓冲，如果没有内容则返回None。
    """
    # 1. 获取笔记文本
    query = LogEntry.query.join(Stage).filter(Stage.user_id == user.id)
    if stage_id:
        query = query.filter(Stage.id == stage_id)
    notes_list = [log.notes for log in query.all() if log.notes and log.notes.strip()]
    if not notes_list:
        return None

    # 2. 文本处理
    stopwords = _load_stopwords()
    full_text = ' '.join(notes_list)
    word_list = jieba.cut(full_text)
    filtered_words = [word for word in word_list if word not in stopwords and len(word) > 1]
    if not filtered_words:
        return None
    segmented_text = ' '.join(filtered_words)

    # 3. 获取资源路径和遮罩
    font_path = os.path.join(current_app.static_folder, 'fonts', 'MaShanZheng-Regular.ttf')
    if not os.path.exists(font_path):
        current_app.logger.error(f"Font file not found: {font_path}")
        return None

    mask_image = _get_mask_image()

    # 4. 生成词云
    try:
        wordcloud = WordCloud(
            font_path=font_path,
            width=800,
            height=800,
            background_color='rgba(255, 255, 255, 0)',
            mode='RGBA',
            mask=mask_image,
            color_func=_theme_color_func,
            prefer_horizontal=0.9,
            collocations=False,
            margin=5,
            max_words=200
        ).generate(segmented_text)

        img_buffer = io.BytesIO()
        wordcloud.to_image().save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer

    except Exception as e:
        current_app.logger.error(f"Failed to generate word cloud: {e}", exc_info=True)
        return None
