import streamlit as st
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
from datetime import datetime

# Set Streamlit page config
st.set_page_config(page_title="Real-time Bitcoin Data", layout="wide")

# Setup Google Sheets credentials from Streamlit Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open("BitcoinRealtimeData").sheet1  # Must match your sheet name

# Title
st.title("📈 Real-Time Bitcoin Avg Price Visualization")

# Function to fetch latest data
def get_latest_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Convert 'timestamp' tuple to datetime
    df['timestamp'] = df['timestamp'].apply(lambda x: datetime(*eval(x)))
    # 'avg_price' is already expected to be numeric
    df['avg_price'] = pd.to_numeric(df['avg_price'], errors='coerce')
    return df.tail(120)  # Keep only latest 120 points

# Real-time plotting
plot_placeholder = st.empty()

while True:
    df = get_latest_data()

    with plot_placeholder.container():
        st.subheader("Live Plot (Last 120 points)")
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df['timestamp'], df['avg_price'], color='blue', linewidth=2)
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Average Price")
        ax.set_title("Bitcoin Avg Price (Real-Time)")
        ax.grid(True)

        # Dynamically adjust y-axis limits based on data range
        ax.set_ylim(df['avg_price'].min()-20, df['avg_price'].max()+20)  # Add some margin for better visibility

        st.pyplot(fig)

    time.sleep(5)  # Update every 5 seconds
