import streamlit as st
from utils.analysis import generateSuggestions

st.title("Suggestions 👨‍⚕️")

if "username" not in st.session_state or not st.session_state["username"]:
    st.error("Kindly Login to find the Detailed Analysis")
    st.stop()  # Better than raising Exception in Streamlit

current_user =  st.session_state["username"]
st.write(generateSuggestions(current_user))