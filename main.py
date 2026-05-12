from fastapi import FastAPI
from pydantic import BaseModel
from database import get_connection, init_db
import requests

app = FastAPI()
init_db()

class UserProfile(BaseModel):
    name: str
    reading_level: str
    listening_level: str
    speaking_level: str
    writing_level: str
    weak_points: str
    goal: str

class WritingInput(BaseModel):
    text: str

@app.post("/users")
def create_user(profile: UserProfile):
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO users (name, reading_level, listening_level, speaking_level, writing_level, weak_points, goal)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (profile.name, profile.reading_level, profile.listening_level,
          profile.speaking_level, profile.writing_level, profile.weak_points, profile.goal))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"user_id": user_id, "message": "Profile created successfully."}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user is None:
        return {"error": "User not found."}
    return dict(user)

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
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2",
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
def analyze(input: WritingInput):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2",
            "prompt": f"Please analyze the following English writing for grammar errors:\n\n{input.text}",
            "stream": False
        }
    )
    return {"result": response.json()["response"]}