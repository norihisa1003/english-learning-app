import streamlit as st
import requests

API_URL = "http://localhost:8000"

# URLパラメータからトークンを取得
params = st.query_params
token = params.get("token", None)

if token:
    st.session_state["token"] = token
    st.query_params.clear()

token = st.session_state.get("token", None)

def api_get(path: str):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{API_URL}{path}", headers=headers)

def api_post(path: str, json: dict):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{API_URL}{path}", json=json, headers=headers)

st.title("English Learning Coach")

if not token:
    st.warning("Please login to continue.")
    if st.button("Login with Google"):
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={API_URL}/auth/login">',
            unsafe_allow_html=True
        )
else:
    me = api_get("/auth/me").json()
    if "error" in me:
        st.error("Session expired. Please login again.")
        st.session_state.clear()
        st.rerun()

    st.success(f"Welcome, {me['user_name']}!")
    user_id = me["user_id"]

    menu = st.sidebar.selectbox(
        "Menu",
        ["Today's Menu", "Analyze Writing", "History", "Register Profile"]
    )

    if menu == "Register Profile":
        st.header("Register Your Profile")

        reading_level = st.selectbox("Reading Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
        listening_level = st.selectbox("Listening Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
        speaking_level = st.selectbox("Speaking Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
        writing_level = st.selectbox("Writing Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
        weak_points = st.text_input("Weak Points (e.g. article, preposition, tense)")
        goal = st.text_input("Goal (e.g. Writing C1)")

        if st.button("Register"):
            response = api_post(f"/users/{user_id}/profile", {
                "reading_level": reading_level,
                "listening_level": listening_level,
                "speaking_level": speaking_level,
                "writing_level": writing_level,
                "weak_points": weak_points,
                "goal": goal
            })
            st.success("Profile updated!")

    elif menu == "Today's Menu":
        st.header("Today's Learning Menu")

        if st.button("Get Today's Menu"):
            with st.spinner("Generating your menu..."):
                response = api_get(f"/users/{user_id}/menu")
                if "error" in response.json():
                    st.error(response.json()["error"])
                else:
                    st.markdown(response.json()["menu"])
    
    elif menu == "Analyze Writing":
        st.header("Analyze Your Writing")

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
                        st.code(result["raw"])  # Ollamaの生レスポンスを表示してデバッグしやすく
                else:
                    st.subheader("Feedback")
                    st.write(result.get("feedback", ""))

                    errors = result.get("errors", [])
                    if errors:
                        st.subheader("Errors Found")
                        for err in errors:
                            with st.expander(f"[{err.get('type', '?')}] {err.get('original', '')}"):
                                st.write(f"**Corrected:** {err.get('corrected', '')}")
                                st.write(f"**Explanation:** {err.get('explanation', '')}")

                    error_types = result.get("error_types", [])
                    if error_types:
                        st.subheader("Error Types")
                        st.write(", ".join(error_types))

    elif menu == "History":
        st.header("Analysis History")

        response = api_get(f"/users/{user_id}/analyses")
        analyses = response.json()

        if not analyses:
            st.info("No analyses yet. Try analyzing some writing first!")
        else:
            for item in analyses:
                with st.expander(f"{item['created_at'][:10]} — {item['original_text'][:40]}..."):
                    st.write(f"**Feedback:** {item['feedback']}")
                    st.write(f"**Error types:** {', '.join(item['error_types'])}")
                    st.text_area("Original text", item["original_text"], disabled=True)
