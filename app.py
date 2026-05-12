import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("English Learning Coach")

menu = st.sidebar.selectbox("Menu", ["Today's Menu", "Register Profile"])

if menu == "Register Profile":
    st.header("Register Your Profile")

    name = st.text_input("Name")
    reading_level = st.selectbox("Reading Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
    listening_level = st.selectbox("Listening Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
    speaking_level = st.selectbox("Speaking Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
    writing_level = st.selectbox("Writing Level", ["A1", "A2", "B1", "B2", "C1", "C2"])
    weak_points = st.text_input("Weak Points (e.g. article, preposition, tense)")
    goal = st.text_input("Goal (e.g. Writing C1)")

    if st.button("Register"):
        if name:
            response = requests.post(f"{API_URL}/users", json={
                "name": name,
                "reading_level": reading_level,
                "listening_level": listening_level,
                "speaking_level": speaking_level,
                "writing_level": writing_level,
                "weak_points": weak_points,
                "goal": goal
            })
            st.success(f"Profile registered! User ID: {response.json()['user_id']}")
        else:
            st.warning("Please enter your name.")

elif menu == "Today's Menu":
    st.header("Today's Learning Menu")

    user_id = st.number_input("User ID", min_value=1, value=1, step=1)

    if st.button("Get Today's Menu"):
        with st.spinner("Generating your menu..."):
            response = requests.get(f"{API_URL}/users/{user_id}/menu")
            if "error" in response.json():
                st.error(response.json()["error"])
            else:
                st.markdown(response.json()["menu"])