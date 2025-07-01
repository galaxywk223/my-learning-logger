# tests/test_models.py

from learning_logger.models import User


def test_new_user(db):
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the username, email, and password fields are defined correctly
    """
    # 1. 创建一个用户实例
    user = User(
        username='testuser',
        email='test@example.com'
    )
    user.set_password('a_secure_password')

    # 2. 将其保存到数据库
    db.session.add(user)
    db.session.commit()

    # 3. 从数据库中查询并进行断言
    # 检查用户数量是否为1
    assert User.query.count() == 1

    # 获取该用户
    retrieved_user = User.query.filter_by(username='testuser').first()
    assert retrieved_user is not None

    # 检查字段是否正确
    assert retrieved_user.email == 'test@example.com'

    # 检查密码哈希是否能被正确验证
    assert retrieved_user.check_password('a_secure_password')
    assert not retrieved_user.check_password('a_wrong_password')