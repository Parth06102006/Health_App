import streamlit as st
from utils.analysis import generateSuggestions
import asyncio

st.title("Suggestions 👨‍⚕️")

if "username" not in st.session_state or not st.session_state["username"]:
    st.error("Kindly Login to find the Detailed Analysis")
    st.stop()  # Better than raising Exception in Streamlit

current_user = st.session_state["username"]
try:
    result = asyncio.run(generateSuggestions(current_user))
    st.write(result)
except Exception as e:
    st.error(f"An error occurred: {e}")