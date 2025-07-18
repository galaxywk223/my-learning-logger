# learning_logger/models/__init__.py (NEW FILE)

# 这个文件将所有分散的模型导入到同一个 `models` 命名空间下。
# 这样，应用的其他部分仍然可以像以前一样从 `learning_logger.models` 导入，
# 无需关心模型具体存放在哪个子文件中。

from .user_models import User, Setting
from .learning_models import Stage, Category, SubCategory, LogEntry, DailyData, WeeklyData
from .feature_models import (
    CountdownEvent,
    Motto,
    Todo,
    MilestoneCategory,
    Milestone,
    MilestoneAttachment,
    DailyPlanItem
)

# 可选：定义 __all__ 来明确指定可以从这个包导出的对象
__all__ = [
    'User', 'Setting',
    'Stage', 'Category', 'SubCategory', 'LogEntry', 'DailyData', 'WeeklyData',
    'CountdownEvent', 'Motto', 'Todo', 'MilestoneCategory', 'Milestone',
    'MilestoneAttachment', 'DailyPlanItem'
]
