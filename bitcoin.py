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

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df['timestamp'], df['actual_price'], label="Actual Price", color='blue', linewidth=2)
        ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)", color='red', marker='x', linestyle='None', markersize=4)

        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Bitcoin Price")
        ax.set_title("Bitcoin Actual vs Predicted Price (t+2)")
        ax.grid(True)
        ax.legend()

        # Check if actual_price and predicted_price contain NaN or Inf
        actual_price_min = df['actual_price'].min(skipna=True)
        actual_price_max = df['actual_price'].max(skipna=True)
        predicted_price_min = df['predicted_price'].min(skipna=True)
        predicted_price_max = df['predicted_price'].max(skipna=True)

        print(f"Actual Price Min: {actual_price_min}, Actual Price Max: {actual_price_max}")
        print(f"Predicted Price Min: {predicted_price_min}, Predicted Price Max: {predicted_price_max}")

        # Handle case where predicted_price is entirely NaN or empty
        if df['predicted_price'].isna().all() or (df['predicted_price'] == '').all():
            print("Predicted Price is empty. Setting limits based on actual_price.")
            y_min = actual_price_min - 20
            y_max = actual_price_max + 20
        else:
            # Handle case where predicted_price has NaN or Inf values
            if np.isnan(predicted_price_min) or np.isinf(predicted_price_min):
                print("Predicted Price Min is NaN or Inf. Falling back to actual price range.")
                predicted_price_min = actual_price_min
            if np.isnan(predicted_price_max) or np.isinf(predicted_price_max):
                print("Predicted Price Max is NaN or Inf. Falling back to actual price range.")
                predicted_price_max = actual_price_max
            
            y_min = min(actual_price_min, predicted_price_min) - 20
            y_max = max(actual_price_max, predicted_price_max) + 20

        # Ensure y_min and y_max are not NaN or Inf
        if np.isnan(y_min) or np.isinf(y_min):
            print("y_min is NaN or Inf. Using fallback value based on actual_price.")
            y_min = actual_price_min - 20
        if np.isnan(y_max) or np.isinf(y_max):
            print("y_max is NaN or Inf. Using fallback value based on actual_price.")
            y_max = actual_price_max + 20

        # Set the y-axis limits
        ax.set_ylim(y_min, y_max)

        st.pyplot(fig)

    time.sleep(5)
