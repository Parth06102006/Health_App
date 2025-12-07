import streamlit as st
import pandas as pd
from pymongo import MongoClient
import plotly.graph_objects as go
import plotly.express as px
import os

# Connect to MongoDB
def getData():
    client = MongoClient(os.getenv("DATABASE_URL"))
    db = client["health"]
    reports = db["Sources"]

    current_user = st.session_state["username"]
    # <CHANGE> Fetch real data from MongoDB instead of using random seed data
    cursor = reports.find({"user":current_user})
    data = [item.get("parsed_data", item) for item in cursor]
    client.close()
    return data

data_list = getData()

if not data_list:
    st.warning("No medical data found in database. Please upload reports first.")
    st.stop()

if "username" not in st.session_state or not st.session_state["username"]:
    st.error("Kindly Login to find the Detailed Analysis")
    st.stop()  # Better than raising Exception in Streamlit

st.set_page_config(page_title="Medical Report Dashboard", layout="wide")
st.title("Medical Report Dashboard")

# Reference normal ranges for parameters
normal_ranges = {
    "blood_sugar_fasting": {"range": (70, 100), "unit": "mg/dL"},
    "blood_sugar_pp": {"range": (100, 140), "unit": "mg/dL"},
    "blood_pressure_systolic": {"range": (90, 120), "unit": "mmHg"},
    "blood_pressure_diastolic": {"range": (60, 80), "unit": "mmHg"},
    "hemoglobin": {"range": (13.5, 17.5), "unit": "g/dL"},
    "rbc": {"range": (4.5, 5.9), "unit": "M/µL"},
    "wbc": {"range": (4000, 11000), "unit": "cells/µL"},
    "platelets": {"range": (150000, 450000), "unit": "cells/µL"},
    "cholesterol_total": {"range": (125, 200), "unit": "mg/dL"},
    "hdl": {"range": (40, 60), "unit": "mg/dL"},
    "ldl": {"range": (0, 100), "unit": "mg/dL"},
    "triglycerides": {"range": (0, 150), "unit": "mg/dL"},
    "creatinine": {"range": (0.6, 1.3), "unit": "mg/dL"},
    "sgot": {"range": (0, 40), "unit": "U/L"},
    "sgpt": {"range": (0, 40), "unit": "U/L"},
    "tsh": {"range": (0.4, 4.0), "unit": "mIU/L"}
}

df = pd.DataFrame(data_list)

# Display raw data
st.subheader("Extracted Medical Data")
st.dataframe(df, use_container_width=True)

# Get numeric columns
numeric_columns = df.select_dtypes(include=['number']).columns.tolist()

if not numeric_columns:
    st.warning("No numeric data found to display.")
    st.stop()

# <CHANGE> Create interactive metrics with comparisons to normal ranges
st.subheader("Health Indicators vs Normal Ranges")

# Create columns for metric cards
cols = st.columns(min(3, len(numeric_columns)))

for idx, column in enumerate(numeric_columns):
    latest_value = df[column].iloc[-1] if len(df) > 0 else None
    
    if latest_value is None or pd.isna(latest_value):
        continue
    
    col = cols[idx % len(cols)]
    
    if column in normal_ranges:
        normal_low, normal_high = normal_ranges[column]["range"]
        unit = normal_ranges[column]["unit"]
        
        # Determine status
        if normal_low <= latest_value <= normal_high:
            status = "Normal"
            status_color = "green"
        elif latest_value < normal_low:
            status = "Low"
            status_color = "orange"
        else:
            status = "High"
            status_color = "red"
        
        with col:
            st.metric(
                label=f"{column}",
                value=f"{latest_value:.2f} {unit}",
                delta=f"Status: {status}",
                delta_color="inverse"
            )
            st.caption(f"Normal Range: {normal_low} - {normal_high} {unit}")
    else:
        with col:
            st.metric(label=column, value=f"{latest_value:.2f}")

# <CHANGE> Interactive trend charts with normal range visualization
st.subheader("Trend Analysis")

selected_parameter = st.selectbox("Select parameter to analyze:", numeric_columns)

if selected_parameter:
    # Get the data for the selected parameter
    values = df[selected_parameter].dropna().tolist()
    indices = list(range(len(values)))
    
    # Create interactive Plotly figure
    fig = go.Figure()
    
    # Add patient data line
    fig.add_trace(go.Scatter(
        x=indices,
        y=values,
        mode='lines+markers',
        name='Patient Data',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=8)
    ))
    
    # Add normal range as shaded area if available
    if selected_parameter in normal_ranges:
        normal_low, normal_high = normal_ranges[selected_parameter]["range"]
        unit = normal_ranges[selected_parameter]["unit"]
        
        # Upper bound of normal range
        fig.add_trace(go.Scatter(
            x=indices,
            y=[normal_high] * len(indices),
            fill=None,
            mode='lines',
            line_color='rgba(0,0,0,0)',
            showlegend=False
        ))
        
        # Lower bound of normal range
        fig.add_trace(go.Scatter(
            x=indices,
            y=[normal_low] * len(indices),
            fill='tonexty',
            mode='lines',
            line_color='rgba(0,0,0,0)',
            name='Normal Range',
            fillcolor='rgba(0,255,0,0.2)'
        ))
        
        fig.add_hline(y=normal_high, line_dash="dash", line_color="green", annotation_text="Upper Limit")
        fig.add_hline(y=normal_low, line_dash="dash", line_color="green", annotation_text="Lower Limit")
    
    fig.update_layout(
        title=f"{selected_parameter} Trend Analysis",
        xaxis_title="Report Number",
        yaxis_title=f"{selected_parameter} ({normal_ranges.get(selected_parameter, {}).get('unit', '')})",
        hovermode='x unified',
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# <CHANGE> Distribution and comparison charts
st.subheader("Health Indicators Distribution")

cols_dist = st.columns(2)

# Box plot for all numeric columns
with cols_dist[0]:
    fig_box = go.Figure()
    
    for column in numeric_columns[:5]:  # Show first 5 for clarity
        values = df[column].dropna()
        fig_box.add_trace(go.Box(y=values, name=column))
    
    fig_box.update_layout(title="Value Distribution", height=400, template='plotly_white')
    st.plotly_chart(fig_box, use_container_width=True)

# Comparison against normal ranges
with cols_dist[1]:
    comparison_data = []
    
    for col in numeric_columns[:5]:
        if col in normal_ranges and len(df) > 0:
            latest = df[col].iloc[-1]
            normal_low, normal_high = normal_ranges[col]["range"]
            comparison_data.append({
                "Parameter": col,
                "Value": latest,
                "Normal Min": normal_low,
                "Normal Max": normal_high
            })
    
    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        
        fig_comp = go.Figure()
        
        fig_comp.add_trace(go.Bar(
            x=comp_df["Parameter"],
            y=comp_df["Value"],
            name="Current Value",
            marker_color='#1f77b4'
        ))
        
        fig_comp.add_trace(go.Bar(
            x=comp_df["Parameter"],
            y=comp_df["Normal Max"],
            name="Normal Range Max",
            marker_color='rgba(0,255,0,0.5)'
        ))
        
        fig_comp.update_layout(
            title="Values vs Normal Range Maxima",
            barmode='group',
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)

# Summary statistics
st.subheader("Summary Statistics")
st.dataframe(df[numeric_columns].describe(), use_container_width=True)