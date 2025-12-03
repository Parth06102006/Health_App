import streamlit as st
import pandas as pd
from pymongo import MongoClient
import matplotlib.pyplot as plt
import os

# Connect to MongoDB
client = MongoClient(os.getenv("DATABASE_URL"))
db = client["health"]
reports = db["Sources"]

st.title("📊 Medical Report Dashboard")

# Reference normal ranges for parameters
normal_ranges = {
    "blood_sugar_fasting": (70, 100),
    "blood_sugar_pp": (100, 140),
    "blood_pressure_systolic": (90, 120),
    "blood_pressure_diastolic": (60, 80),
    "hemoglobin": (13.5, 17.5),  # Male average, adjust if needed
    "rbc": (4.5, 5.9),
    "wbc": (4000, 11000),
    "platelets": (150000, 450000),
    "cholesterol_total": (125, 200),
    "hdl": (40, 60),
    "ldl": (0, 100),
    "triglycerides": (0, 150),
    "creatinine": (0.6, 1.3),
    "sgot": (0, 40),
    "sgpt": (0, 40),
    "tsh": (0.4, 4.0)
}

# Fetch data from MongoDB
cursor = reports.find({})
data_list = [item["parsed_data"] for item in cursor if "parsed_data" in item]

df = pd.DataFrame(data_list)

st.write("### All Extracted Medical Data")
st.dataframe(df)

# Plot trends with normal ranges
numeric_df = df.select_dtypes(include=['number'])

for column in numeric_df.columns:
    st.write(f"### Trend: {column}")
    
    plt.figure(figsize=(8,4))
    plt.plot(numeric_df[column], marker='o', label='Patient Data')
    
    # Plot normal range as shaded area
    if column in normal_ranges:
        low, high = normal_ranges[column]
        plt.fill_between(range(len(numeric_df)), low, high, color='green', alpha=0.2, label='Normal Range')
    
    plt.xlabel("Report Number")
    plt.ylabel(column)
    plt.legend()
    st.pyplot(plt)
