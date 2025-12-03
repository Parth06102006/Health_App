import streamlit as st
from utils.analysis import analysis

st.title("Enter your Symptoms")

with st.form("symptom_find_disease"):
    info = st.text_area("Tell us about symptoms to find the cause ...")
    submit_button = st.form_submit_button("Analyze Reports")

    if submit_button and info:
        try:
            message = analysis(info)
            st.write(message)
        except Exception as e:
                st.error(f"An error occurred: {e}")

    else:
         if(not info):
              st.warning("Kindly enter the symptoms you are facing")