# tests/test_database.py
import sqlite3
import pytest
from database import init_db, get_connection

DATABASE_TEST = ":memory:"  # インメモリDBでテスト

@pytest.fixture
def db():
    """テスト用のインメモリDBを作成して返す"""
    import database
    original = database.DATABASE
    database.DATABASE = DATABASE_TEST
    init_db()
    yield get_connection()
    database.DATABASE = original

def test_users_table_has_email(db):
    """usersテーブルにemailカラムがあるか"""
    columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
    assert "email" in columns

def test_writing_analyses_table_exists(db):
    """writing_analysesテーブルが作成されるか"""
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "writing_analyses" in tables

def test_insert_user(db):
    """userを挿入してemailで検索できるか"""
    db.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE email = ?", ("test@example.com",)).fetchone()
    assert user is not None
    assert user["name"] == "Test User"