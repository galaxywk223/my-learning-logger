# tests/conftest.py

import pytest
from learning_logger import create_app, db as _db

@pytest.fixture(scope='session')
def app():
    """
    创建一个应用实例，其作用域为整个测试会话。
    """
    # 强制使用'testing'配置
    _app = create_app('testing')

    # '应用上下文'对于许多Flask扩展来说是必需的，
    # 它们需要知道当前的应用实例是什么。
    with _app.app_context():
        yield _app

@pytest.fixture(scope='function')
def client(app):
    """
    创建一个测试客户端，其作用域为每个测试函数。
    每次测试都会得到一个新的客户端。
    """
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """
    创建一个命令行运行器。
    """
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """
    为每个测试函数设置和拆卸数据库。
    """
    with app.app_context():
        # 在测试开始前创建所有表
        _db.create_all()

        yield _db

        # 在测试结束后，清理会话并删除所有表
        _db.session.remove()
        _db.drop_all()