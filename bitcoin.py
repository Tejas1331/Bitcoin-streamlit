import streamlit as st
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np

# Set Streamlit page config
st.set_page_config(page_title="Real-time Bitcoin Data", layout="wide")

# Setup Google Sheets credentials from Streamlit Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open("BitcoinRealtimeData").sheet1  # Match sheet name

# Title
st.title("📈 Real-Time Bitcoin: Actual vs Predicted Price (t+2)")

# Function to fetch latest data
def get_latest_data():
    data = sheet.get_all_values()
    parsed_data = []

    for row in data:
        try:
            # Convert timestamp string to datetime
            timestamp = datetime(*eval(row[0]))
            actual_price = float(row[1])
            predicted_price = float(row[2])
            parsed_data.append([timestamp, actual_price, predicted_price])
        except Exception as e:
            print(f"Skipping row due to error: {e}")

    df = pd.DataFrame(parsed_data, columns=['timestamp', 'actual_price', 'predicted_price'])

    # Shift predicted_price to t+2
    df['predicted_timestamp'] = df['timestamp'] + timedelta(minutes=2)
    
    return df.tail(120)

# Real-time plotting
plot_placeholder = st.empty()

while True:
    df = get_latest_data()

    with plot_placeholder.container():
        st.subheader("Live Plot (Last 120 points, Predicted at t+2)")

        # Handle NaN or Inf values in actual_price and predicted_price
        df['actual_price'] = pd.to_numeric(df['actual_price'], errors='coerce')
        df['predicted_price'] = pd.to_numeric(df['predicted_price'], errors='coerce')

        # Remove rows where either column is NaN or Inf
        df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['actual_price'])

        # Plotting
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Plot actual prices continuously (blue line)
        ax.plot(df['timestamp'], df['actual_price'], label="Actual Price", color='blue', linewidth=2)

        # For predicted prices, plot where data is available and leave gaps where no prediction exists
        ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)", color='red', marker='x', linestyle='None', markersize=4)

        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Bitcoin Price")
        ax.set_title("Bitcoin Actual vs Predicted Price (t+2)")
        ax.grid(True)
        ax.legend()

        # Calculate min and max values for y-axis
        actual_price_min = df['actual_price'].min()
        actual_price_max = df['actual_price'].max()

        # Handle case where predicted_price is empty or NaN
        if df['predicted_price'].isna().all():
            y_min = actual_price_min - 20
            y_max = actual_price_max + 20
        else:
            predicted_price_min = df['predicted_price'].min()
            predicted_price_max = df['predicted_price'].max()
            y_min = min(actual_price_min, predicted_price_min) - 20
            y_max = max(actual_price_max, predicted_price_max) + 20

        # If there's only one data point (min == max), artificially expand the range
        if actual_price_min == actual_price_max:
            y_min = actual_price_min - 100
            y_max = actual_price_max + 100

        # Ensure y_min and y_max are not NaN or Inf
        if np.isnan(y_min) or np.isinf(y_min):
            y_min = actual_price_min - 20
        if np.isnan(y_max) or np.isinf(y_max):
            y_max = actual_price_max + 20

        # Set y-axis limits
        ax.set_ylim(y_min, y_max)

        st.pyplot(fig)

    time.sleep(5)
