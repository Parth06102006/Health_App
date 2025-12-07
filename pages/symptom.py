import streamlit as st
from utils.analysis import analysis
import asyncio

st.title("Enter your Symptoms")

if "username" not in st.session_state or not st.session_state["username"]:
    st.error("Kindly Login to find the Detailed Analysis")
    st.stop()  # Better than raising Exception in Streamlit

with st.form("symptom_find_disease"):
    info = st.text_area("Tell us about symptoms to find the cause ...")
    submit_button = st.form_submit_button("Analyze Reports")

    if submit_button and info:
        try:
            current_user = st.session_state["username"]
            print(current_user)
            message = asyncio.run(analysis(info, current_user))
            print(message)
            st.write(message)
        except Exception as e:
                st.error(f"An error occurred: {e}")

    else:
         if(not info):
              st.warning("Kindly enter the symptoms you are facing")