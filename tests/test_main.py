import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def make_auth_header(user_id: int = 1) -> dict:
    """Generate a test JWT token."""
    from auth import create_access_token
    token = create_access_token({"user_id": user_id, "user_name": "Test User", "email": "test@example.com"})
    return {"Authorization": f"Bearer {token}"}


# --- _aggregate_weak_points のテスト ---

def test_aggregate_weak_points_empty():
    """分析データがない場合は空を返す"""
    from main import _aggregate_weak_points
    with patch("main.get_connection") as mock_conn:
        mock_conn.return_value.execute.return_value.fetchall.return_value = []
        result = _aggregate_weak_points(user_id=1)
    assert result["top_weak_point"] is None
    assert result["weak_points"] == []


def test_aggregate_weak_points_counts():
    """error_typesが正しく集計される"""
    from main import _aggregate_weak_points

    fake_rows = [
        MagicMock(**{"__getitem__": lambda self, k: json.dumps(["article", "tense"])}),
        MagicMock(**{"__getitem__": lambda self, k: json.dumps(["article"])}),
    ]

    with patch("main.get_connection") as mock_conn:
        mock_conn.return_value.execute.return_value.fetchall.return_value = fake_rows
        result = _aggregate_weak_points(user_id=1)

    assert result["top_weak_point"] == "article"
    assert result["weak_points"][0]["count"] == 2


# --- /analyze エンドポイントのテスト ---

def test_analyze_unauthenticated():
    """/analyze は認証なしで呼ぶとエラーを返す"""
    response = client.post("/analyze", json={"text": "I go to school yesterday."})
    assert response.status_code == 200
    assert response.json()["error"] == "Not authenticated"


def test_analyze_authenticated():
    """/analyze はOllamaをモックして正常系を確認"""
    fake_result = {
        "feedback": "Good try!",
        "errors": [{"type": "tense", "original": "go", "corrected": "went", "explanation": "Past tense needed."}],
        "error_types": ["tense"]
    }

    with patch("main.http_requests.post") as mock_post, \
         patch("main.get_connection") as mock_conn:

        mock_post.return_value.json.return_value = {"response": json.dumps(fake_result)}
        mock_conn.return_value.execute.return_value = MagicMock()
        mock_conn.return_value.commit.return_value = None

        response = client.post(
            "/analyze",
            json={"text": "I go to school yesterday."},
            headers=make_auth_header()
        )

    assert response.status_code == 200
    assert response.json()["error_types"] == ["tense"]