import streamlit as st
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
 
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
     #df['predicted_price'] = df['predicted_price'].shift(0)
     #df['predicted_timestamp'] = df['timestamp'].shift(0)
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
        ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)",  color='red', marker='+', linestyle='None', markersize=2)
        ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)",  color='red', marker='x', linestyle='None', markersize=4)
 
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Bitcoin Price")
        ax.set_title("Bitcoin Actual vs Predicted Price (t+2)")
        ax.grid(True)
        ax.legend()

        if df['predicted_price'].isnull().all():
         y_min = min(df['actual_price'].min()) - 20
         y_max = max(df['actual_price'].max()) + 20
         ax.set_ylim(y_min, y_max)

        else:
         y_min = min(df['actual_price'].min(), df['predicted_price'].min(skipna=True)) - 20
         y_max = max(df['actual_price'].max(), df['predicted_price'].max(skipna=True)) + 20
         ax.set_ylim(y_min, y_max)
 
        st.pyplot(fig)
 
    time.sleep(5)
