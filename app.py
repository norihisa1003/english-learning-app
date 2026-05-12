import streamlit as st
import requests

st.title("English Writing Analyzer")

text = st.text_area("Enter your diary entry here:")

if st.button("Analyze"):
    if text:
        with st.spinner("Analyzing..."):
            response = requests.post(
                "http://localhost:8000/analyze",
                json={"text": text}
            )
            result = response.json()["result"]
            st.write("### Feedback")
            st.write(result)
    else:
        st.warning("Please enter some text.")