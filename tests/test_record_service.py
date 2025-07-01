# tests/test_record_service.py

from datetime import date
from learning_logger.services import record_service
from learning_logger.models import User, Setting, LogEntry

def test_get_structured_logs_for_user(db):
    """
    GIVEN a user with settings and log entries in the database
    WHEN get_structured_logs_for_user is called
    THEN check that the logs are structured correctly by week and day
    """
    # 1. 准备测试数据
    # 创建用户
    user = User(username='service_tester', email='service@test.com')
    db.session.add(user)
    db.session.commit()

    # 创建设置
    setting = Setting(user_id=user.id, key='week_start_date', value='2023-12-25') # 周一
    db.session.add(setting)

    # 创建日志条目 (跨越两周)
    log1 = LogEntry(user_id=user.id, log_date=date(2023, 12, 28), task="周四的日志") # 第52周
    log2 = LogEntry(user_id=user.id, log_date=date(2023, 12, 28), task="周四的第二条日志") # 第52周
    log3 = LogEntry(user_id=user.id, log_date=date(2024, 1, 2), task="周二的日志") # 第1周
    db.session.add_all([log1, log2, log3])
    db.session.commit()

    # 2. 调用被测试的服务函数
    structured_logs, setup_needed = record_service.get_structured_logs_for_user(user)

    # 3. 断言结果
    assert not setup_needed  # 应该不需要设置
    assert len(structured_logs) == 2  # 应该有两周的数据

    # 检查第一周 (2024年第1周，因为默认降序排列)
    first_week = structured_logs[0]
    assert first_week['year'] == 2024
    assert first_week['week_num'] == 1
    assert len(first_week['days']) == 2  # 只有一个有日志的天

    first_week_day = first_week['days'][0]
    assert first_week_day['date'] == date(2024, 1, 2)
    assert len(first_week_day['logs']) == 1
    assert first_week_day['logs'][0].task == "周二的日志"

    # 检查第二周 (2023年第52周)
    second_week = structured_logs[1]
    assert second_week['year'] == 2023
    assert second_week['week_num'] == 52
    assert len(second_week['days']) == 1 # 只有一个有日志的天

    second_week_day = second_week['days'][0]
    assert second_week_day['date'] == date(2023, 12, 28)
    assert len(second_week_day['logs']) == 2 # 应该有两条日志
    assert second_week_day['logs'][0].task == "周四的日志"