import sqlite3
import pytest
from requests import patch
from database import init_db
from unittest.mock import patch

DATABASE_TEST = ":memory:"  # インメモリDBでテスト

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with patch.dict("os.environ", {
        "DEFAULT_USER_NAME": "TestUser",
        "DEFAULT_USER_EMAIL": "testdefault@example.com",
        "DATABASE": "DATABASE_TEST"
    }):
        init_db(conn)
    init_db(conn)  # 同じ接続を渡す
    yield conn
    conn.close()

def test_users_table_has_email(db):
    """usersテーブルにemailカラムがあるか"""
    columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
    assert "email" in columns

def test_writing_analyses_table_exists(db):
    """writing_analysesテーブルが作成されるか"""
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "writing_analyses" in tables

def test_login_history_table_exists(db):
    """login_historyテーブルが作成されるか"""
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "login_history" in tables

def test_test_results_table_exists(db):
    """test_resultsテーブルが作成されるか"""
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "test_results" in tables

def test_insert_user(db):
    """userを挿入してemailで検索できるか"""
    db.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE email = ?", ("test@example.com",)).fetchone()
    assert user is not None
    assert user["name"] == "Test User"

def test_default_user_inserted(db):
    """DEFAULT_USER_EMAIL設定時にデフォルトユーザーが挿入されるか"""
    user = db.execute(
        "SELECT * FROM users WHERE email = ?", ("testdefault@example.com",)
    ).fetchone()
    assert user is not None
    assert user["name"] == "TestUser"

def test_default_user_not_duplicated(db):
    """init_dbを2回呼んでもデフォルトユーザーが重複しないか"""
    with patch.dict("os.environ", {
        "DEFAULT_USER_NAME": "TestUser",
        "DEFAULT_USER_EMAIL": "testdefault@example.com"
    }):
        init_db(db)  # 2回目
    count = db.execute(
        "SELECT COUNT(*) FROM users WHERE email = ?", ("testdefault@example.com",)
    ).fetchone()[0]
    assert count == 1