import streamlit as st
from pathlib import Path
from tempfile import NamedTemporaryFile
from utils.extractTextFunction import extractText
import os
import asyncio

# App title
st.title("AI Health Analysis")

# Supported file types
FILE_EXTENSIONS = ["jpg", "jpeg", "png", "pdf", "txt"]

if "username" not in st.session_state or not st.session_state["username"]:
    st.error("Kindly Login to find the Detailed Analysis")
    st.stop()  # Better than raising Exception in Streamlit
# Form for file upload
with st.form("ai_health_analysis_form"):
    uploaded_file = st.file_uploader("Upload your medical reports", type=FILE_EXTENSIONS)
    submit_button = st.form_submit_button("Submit Reports")

    if submit_button:
        if uploaded_file is not None:
            suffix = Path(uploaded_file.name).suffix

            try:
                with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                    temp_file.write(uploaded_file.read())
                    temp_file_path = temp_file.name

                current_user = st.session_state["username"]
                asyncio.run(extractText(temp_file_path, suffix.lstrip("."), Path(temp_file_path).name, current_user))

                st.success("File uploaded and processed successfully.")

            except Exception as e:
                st.error(f"An error occurred: {e}")

            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        else:
            st.warning("Please upload a file to analyze.")
