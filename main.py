from fastapi import FastAPI, Request, Header
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from database import get_connection, init_db
from auth import oauth, create_access_token, decode_access_token
import requests as http_requests
import os
from dotenv import load_dotenv
from typing import Optional
import json

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
init_db()

class UserProfile(BaseModel):
    name: str
    reading_level: str
    listening_level: str
    speaking_level: str
    writing_level: str
    weak_points: str
    goal: str

class ProfileUpdate(BaseModel):
    reading_level: str
    listening_level: str
    speaking_level: str
    writing_level: str
    weak_points: str
    goal: str

class WritingInput(BaseModel):
    text: str

def get_current_user(authorization: Optional[str] = None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    return decode_access_token(token)

@app.get("/auth/login")
async def login(request: Request):
    redirect_uri = "http://localhost:8000/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    conn = get_connection()
    existing_user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (user_info["email"],)
    ).fetchone()

    if existing_user is None:
        conn.execute("""
            INSERT INTO users (name, email)
            VALUES (?, ?)
        """, (user_info["name"], user_info["email"]))
        conn.commit()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (user_info["email"],)
    ).fetchone()
    conn.close()

    # JWTトークンを発行
    access_token = create_access_token({
        "user_id": user["id"],
        "user_name": user["name"],
        "email": user["email"]
    })

    # StreamlitにトークンをURLパラメータで渡す
    return RedirectResponse(
        url=f"http://localhost:8501?token={access_token}"
    )

@app.get("/auth/me")
async def get_me(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    if not user:
        return {"error": "Not authenticated"}
    return {"user_id": user["user_id"], "user_name": user["user_name"]}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user is None:
        return {"error": "User not found."}
    return dict(user)

@app.post("/users/{user_id}/profile")
def update_profile(user_id: int, profile: ProfileUpdate):
    conn = get_connection()
    conn.execute("""
        UPDATE users SET
            reading_level = ?,
            listening_level = ?,
            speaking_level = ?,
            writing_level = ?,
            weak_points = ?,
            goal = ?
        WHERE id = ?
    """, (profile.reading_level, profile.listening_level,
          profile.speaking_level, profile.writing_level,
          profile.weak_points, profile.goal, user_id))
    conn.commit()
    conn.close()
    return {"message": "Profile updated successfully."}

@app.get("/users/{user_id}/menu")
def get_menu(user_id: int):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user is None:
        return {"error": "User not found."}

    user = dict(user)
    prompt = f"""
You are an English learning coach. Based on the following student profile, suggest today's learning menu.

Profile:
- Reading: {user['reading_level']}
- Listening: {user['listening_level']}
- Speaking: {user['speaking_level']}
- Writing: {user['writing_level']}
- Weak points: {user['weak_points']}
- Goal: {user['goal']}

Please suggest a 1-2 hour learning menu for today with specific tasks and time allocation.
"""
    response = http_requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    menu = response.json()["response"]

    conn = get_connection()
    conn.execute("""
        INSERT INTO learning_logs (user_id, date, menu)
        VALUES (?, DATE('now'), ?)
    """, (user_id, menu))
    conn.commit()
    conn.close()

    return {"menu": menu}

@app.post("/analyze")
def analyze(input: WritingInput, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    if not user:
        return {"error": "Not authenticated"}

    prompt = f"""Analyze the following English writing and return JSON only, no explanation.

Writing:
{input.text}

Return this exact format:
{{
  "feedback": "overall feedback in 2-3 sentences",
  "errors": [
    {{"type": "article", "original": "...", "corrected": "...", "explanation": "..."}}
  ],
  "error_types": ["article", "tense"]
}}

Error types must be chosen from: article, tense, preposition, noun_phrase, spelling, other"""

    response = http_requests.post(
        "http://localhost:11434/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    )

    # JSONパース
    try:
        raw = response.json()["response"]
        result = json.loads(raw)
    except (json.JSONDecodeError, KeyError):
        return {"error": "Failed to parse Ollama response", "raw": response.json().get("response")}

    # DBに保存
    conn = get_connection()
    conn.execute("""
        INSERT INTO writing_analyses (user_id, original_text, feedback, error_types)
        VALUES (?, ?, ?, ?)
    """, (
        user["user_id"],
        input.text,
        result.get("feedback", ""),
        json.dumps(result.get("error_types", []))
    ))
    conn.commit()
    conn.close()

    return result

@app.get("/users/{user_id}/analyses")
def get_analyses(user_id: int, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    if not user:
        return {"error": "Not authenticated"}
    if user["user_id"] != user_id:
        return {"error": "Forbidden"}

    conn = get_connection()
    rows = conn.execute("""
        SELECT id, original_text, feedback, error_types, created_at
        FROM writing_analyses
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()
    conn.close()

    return [
        {**dict(row), "error_types": json.loads(row["error_types"] or "[]")}
        for row in rows
    ]

def _aggregate_weak_points(user_id: int) -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT error_types FROM writing_analyses WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()

    counter = {}
    for row in rows:
        for t in json.loads(row["error_types"] or "[]"):
            counter[t] = counter.get(t, 0) + 1

    if not counter:
        return {"weak_points": [], "top_weak_point": None}

    sorted_points = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    return {
        "weak_points": [{"type": t, "count": c} for t, c in sorted_points],
        "top_weak_point": sorted_points[0][0]
    }

@app.get("/users/{user_id}/weak_points")
def get_weak_points(user_id: int, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    if not user or user["user_id"] != user_id:
        return {"error": "Not authenticated"}
    return _aggregate_weak_points(user_id)


@app.post("/users/{user_id}/training")
def generate_training(user_id: int, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    if not user or user["user_id"] != user_id:
        return {"error": "Not authenticated"}

    # 弱点を取得
    weak_points_data = _aggregate_weak_points(user_id)
    top_weak_point = weak_points_data.get("top_weak_point")

    if not top_weak_point:
        return {"error": "No weak points found. Please analyze some writing first."}

    prompt = f"""You are an English teacher. Create 3 training exercises focused ONLY on "{top_weak_point}" errors.

Rules:
- Every exercise must specifically target "{top_weak_point}" mistakes
- Use ONLY this JSON format, no variations

Return JSON only, no explanation:

{{
  "weak_point": "{top_weak_point}",
  "exercises": [
    {{
      "format": "fill_in_the_blank or error_correction",
      "question": "the exercise sentence with ___ for blanks, or the incorrect sentence to fix",
      "answer": "the correct answer",
      "explanation": "why this is the correct answer, specifically about {top_weak_point}"
    }}
  ]
}}

Example for article errors:
{{
  "format": "fill_in_the_blank",
  "question": "I saw ___ elephant at the zoo.",
  "answer": "an",
  "explanation": "Use 'an' before words starting with a vowel sound."
}}"""

    response = http_requests.post(
        "http://localhost:11434/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    )

    try:
        raw = response.json()["response"]
        print(f"[Ollama raw response]\n{raw}")
        parsed = json.loads(raw)
        # Ollamaがリストを直接返した場合に対応
        if isinstance(parsed, list):
            result = {"weak_point": top_weak_point, "exercises": parsed}
        else:
            result = parsed
    except (json.JSONDecodeError, KeyError):
        return {"error": "Failed to parse Ollama response", "raw": response.json().get("response")}

    return result