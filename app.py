import os
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

API_INTERNAL_URL = os.getenv("API_INTERNAL_URL", "http://localhost:8000")
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000")

# --- Token handling ---
params = st.query_params
token = params.get("token", None)
if token:
    st.session_state["token"] = token
    st.query_params.clear()

token = st.session_state.get("token", None)

# --- API helpers ---
def api_get(path: str):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{API_INTERNAL_URL}{path}", headers=headers)

def api_post(path: str, json: dict):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{API_INTERNAL_URL}{path}", json=json, headers=headers)

# --- Page routing ---
def go(page: str):
    st.session_state["page"] = page
    st.rerun()

# --- Pages ---
def page_login():
    st.title("English Learning Coach")
    st.warning("Please login to continue.")
    if st.button("Login with Google"):
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={API_PUBLIC_URL}/auth/login">',
            unsafe_allow_html=True
        )

def page_profile(user_id: int, required: bool = False):
    st.title("Profile")
    if required:
        st.info("Please complete your profile to get started.")
    else:
        if st.button("← Back"):
            go("home")

    user = api_get(f"/users/{user_id}").json()

    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    reading_level   = st.selectbox("Reading Level",   levels, index=levels.index(user.get("reading_level") or "B2"))
    listening_level = st.selectbox("Listening Level", levels, index=levels.index(user.get("listening_level") or "B2"))
    speaking_level  = st.selectbox("Speaking Level",  levels, index=levels.index(user.get("speaking_level") or "B2"))
    writing_level   = st.selectbox("Writing Level",   levels, index=levels.index(user.get("writing_level") or "B2"))
    weak_points     = st.text_input("Weak Points (e.g. article, preposition, tense)", value=user.get("weak_points") or "")
    goal            = st.text_input("Goal (e.g. Writing C1)", value=user.get("goal") or "")

    if st.button("Save"):
        api_post(f"/users/{user_id}/profile", {
            "reading_level": reading_level,
            "listening_level": listening_level,
            "speaking_level": speaking_level,
            "writing_level": writing_level,
            "weak_points": weak_points,
            "goal": goal
        })
        st.success("Profile updated!")
        go("home")

def page_home(user_id: int, user_name: str):
    st.title(f"Welcome, {user_name}!")

    st.divider()

    # 今日やること（自動表示）
    st.subheader("Today's plan")
    with st.spinner("Generating..."):
        response = api_get(f"/users/{user_id}/menu")
        result = response.json()
        if "error" in result:
            st.error(result["error"])
        else:
            st.markdown(result["menu"])

def page_analyze(user_id: int):
    st.title("Analyze writing")
    if st.button("← Back"):
        go("home")

    text = st.text_area("Enter your diary entry or writing:", height=200)
    if st.button("Analyze"):
        if not text.strip():
            st.warning("Please enter some text.")
        else:
            with st.spinner("Analyzing..."):
                response = api_post("/analyze", {"text": text})
                result = response.json()

            if "error" in result:
                st.error(result["error"])
                if "raw" in result:
                    st.code(result["raw"])
            else:
                st.subheader("Feedback")
                st.write(result.get("feedback", ""))

                errors = result.get("errors", [])
                if errors:
                    st.subheader("Errors found")
                    for err in errors:
                        with st.expander(f"[{err.get('type', '?')}] {err.get('original', '')}"):
                            st.write(f"**Corrected:** {err.get('corrected', '')}")
                            st.write(f"**Explanation:** {err.get('explanation', '')}")

                error_types = result.get("error_types", [])
                if error_types:
                    st.subheader("Error types")
                    st.write(", ".join(error_types))

def page_test(user_id: int):
    st.title("Test")
    if st.button("← Back"):
        go("home")

    wp_response = api_get(f"/users/{user_id}/weak_points")
    wp_data = wp_response.json()

    if not wp_data.get("top_weak_point"):
        st.info("No data yet. Please analyze some writing first.")
        return

    st.subheader("Your weak points")
    for wp in wp_data.get("weak_points", []):
        st.write(f"- **{wp['type']}**: {wp['count']} times")

    st.divider()
    st.subheader(f"Today's focus: `{wp_data['top_weak_point']}`")

    if st.button("Generate exercises"):
        with st.spinner("Generating exercises..."):
            response = api_post(f"/users/{user_id}/training", {})
            result = response.json()

        if "error" in result:
            st.error(result["error"])
            if "raw" in result:
                st.code(result["raw"])
        else:
            st.session_state["exercises"] = result.get("exercises", [])
            st.session_state["show_answers"] = {}

    exercises = st.session_state.get("exercises", [])
    for i, ex in enumerate(exercises, 1):
        with st.expander(f"Exercise {i} [{ex.get('format', '')}]", expanded=True):
            st.write(f"**Question:** {ex.get('question', '')}")
            if st.button(f"Show answer", key=f"answer_{i}"):
                st.session_state["show_answers"][i] = True
            if st.session_state.get("show_answers", {}).get(i):
                st.success(f"Answer: {ex.get('answer', '')}")
                st.write(f"**Explanation:** {ex.get('explanation', '')}")
def page_history(user_id: int):
    st.title("Analysis history")
    response = api_get(f"/users/{user_id}/analyses")
    analyses = response.json() if response.ok else []
    if not analyses:
        st.info("No analyses yet.")
    else:
        for item in analyses:
            with st.expander(f"{item['created_at'][:10]} — {item['original_text'][:40]}..."):
                st.write(f"**Feedback:** {item['feedback']}")
                st.write(f"**Error types:** {', '.join(item['error_types'])}")
                st.text_area("Original text", item["original_text"], disabled=True, key=f"history_{item['id']}")

# --- Main ---
st.set_page_config(page_title="English Learning Coach", layout="centered")

if not token:
    page_login()
else:
    me = api_get("/auth/me").json()
    if "error" in me:
        st.error("Session expired. Please login again.")
        st.session_state.clear()
        st.rerun()

    user_id   = me["user_id"]
    user_name = me["user_name"]

    # プロフィール未登録チェック
    user = api_get(f"/users/{user_id}").json()
    profile_incomplete = not user.get("weak_points")

    page = st.session_state.get("page", "home")

# サイドバー（ログイン後全画面共通）
    with st.sidebar:
        st.metric("🔥 Streak", "3 days")  # API実装後に差し替え
        st.divider()
        st.write(f"👤 {user_name}")
        if st.button("🏠 Home"):
            go("home")
        if st.button("📝 Analyze writing"):
            go("analyze")
        if st.button("🎯 Test"):
            go("test")
        if st.button("📋 History"):
            go("history")
        if st.button("👤 Edit profile"):
            go("profile")

    if profile_incomplete and page != "profile":
        page_profile(user_id, required=True)
    elif page == "profile":
        page_profile(user_id)
    elif page == "analyze":
        page_analyze(user_id)
    elif page == "test":
        page_test(user_id)
    elif page == "history":
        page_history(user_id)
    else:
        page_home(user_id, user_name)