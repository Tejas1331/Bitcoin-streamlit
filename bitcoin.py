
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
    data = sheet.get_all_values()[1:]
    parsed_data = []

    for row in data:
        try:
            timestamp = datetime(*eval(row[0]))  # Modify format if needed
            actual_price = float(row[1])
            if row[2] == '':
                predicted_price = np.nan
            else:
                predicted_price = float(row[2])
            parsed_data.append([timestamp, actual_price, predicted_price])
        except Exception as e:
            print(f"Skipping row due to error: {e}")

    df = pd.DataFrame(parsed_data, columns=['timestamp', 'actual_price', 'predicted_price'])

    # Shift predicted_price to t+2
    df['predicted_timestamp'] = df['timestamp'] + timedelta(minutes=2)
    df['predicted_price'] = df['predicted_price'].fillna(np.nan)

    return df.tail(120), df.tail(1)  # Returning last 120 entries and the latest entry

# Real-time plotting and text display
plot_placeholder = st.empty()

#holdings = []
#previous_rating = None
#total_profit = 0

if 'holdings' not in st.session_state:
    st.session_state.holdings = []
if 'previous_rating' not in st.session_state:
    st.session_state.previous_rating = None
if 'total_profit' not in st.session_state:
    st.session_state.total_profit = 0
    
last_processed_timestamp = None

while True:
    df, last_entry = get_latest_data()

    try:
        predicted_price = last_entry['predicted_price'].values[0]
        if np.isnan(predicted_price):
            predicted_timestamp = np.nan
        else:
            predicted_timestamp = last_entry['predicted_timestamp'].values[0]
        actual_price = last_entry['actual_price'].values[0]
        actual_timestamp = last_entry['timestamp'].values[0]

        # Skip if already processed
        if actual_timestamp == last_processed_timestamp:
            with plot_placeholder.container():
                cols = st.columns([1, 2])

                with cols[0]:
                    st.subheader("📋 Live Status")
                    #st.info("⏳ Waiting for new data update...")

                with cols[1]:
                    st.subheader("📈 Live Plot (Last 120 points, Predicted at t+2)")
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(df['timestamp'], df['actual_price'], label="Actual Price", color='blue', linewidth=2)
                    ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)", color='red', marker='x', linestyle='None', markersize=4)

                    ax.set_xlabel("Timestamp")
                    ax.set_ylabel("Bitcoin Price")
                    ax.set_title("Bitcoin Actual vs Predicted Price (t+2)")
                    ax.grid(True)
                    ax.legend()

                    y_min = min(df['actual_price'].min(), df['predicted_price'].min(skipna=True)) - 20
                    y_max = max(df['actual_price'].max(), df['predicted_price'].max(skipna=True)) + 20
                    ax.set_ylim(y_min, y_max)

                    st.pyplot(fig)
            time.sleep(5)
            continue

        # Process only new data
        if np.isnan(predicted_price):
            rating = None
        else:
            rating = "Buy" if (predicted_price - actual_price) >= 0 else "Sell"

        if rating is not None:
            if st.session_state.previous_rating is None:
                st.session_state.previous_rating = rating

            if rating == st.session_state.previous_rating:
                if rating == "Buy":
                    st.session_state.holdings.append(actual_price)
                else:
                    st.session_state.holdings.append(-actual_price)
            else:
                if st.session_state.holdings:
                    units = len(st.session_state.holdings)
                    avg_entry_price = sum(st.session_state.holdings) / units

                    if st.session_state.previous_rating == "Buy":
                        profit = (actual_price * units) - sum(st.session_state.holdings)
                    else:
                        profit = sum(st.session_state.holdings) + (actual_price * units)

                    st.session_state.total_profit += profit

                st.session_state.holdings = []
                if rating == "Buy":
                    st.session_state.holdings.append(actual_price)
                else:
                    st.session_state.holdings.append(-actual_price)

                st.session_state.previous_rating = rating

        last_processed_timestamp = actual_timestamp

        # Display updated layout
        with plot_placeholder.container():
            cols = st.columns([1, 2])

            with cols[0]:
                st.subheader("📋 Live Status")
                st.markdown(f"**Predicted Price:** {predicted_price}")
                st.markdown(f"**Timestamp for Prediction:** {predicted_timestamp}")
                st.markdown(f"**Timestamp for Actual Price:** {actual_timestamp}")
                st.markdown(f"**Actual Price:** {actual_price}")
                if rating == 'Buy':
                    st.success(f"**Rating:** {rating}")
                elif rating == 'Sell':
                    st.error(f"**Rating:** {rating}")
                else:
                    st.markdown(f"**Rating:** {rating}")
                st.session_state.holdings = [round(float(h), 2) for h in st.session_state.holdings]
                st.markdown(f"**Current Holdings:** {st.session_state.holdings}")
                st.markdown(f"**Total Profit/Loss:** {st.session_state.total_profit:.2f}")
                if np.isnan(predicted_price):
                    st.info("⏳ Waiting for new data update...")
                else:
                    st.success("✅ New data processed.")

            with cols[1]:
                st.subheader("📈 Live Plot (Last 120 points, Predicted at t+2)")
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(df['timestamp'], df['actual_price'], label="Actual Price", color='blue', linewidth=2)
                ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)", color='red', marker='x', linestyle='None', markersize=4)

                ax.set_xlabel("Timestamp")
                ax.set_ylabel("Bitcoin Price")
                ax.set_title("Bitcoin Actual vs Predicted Price (t+2)")
                ax.grid(True)
                ax.legend()

                y_min = min(df['actual_price'].min(), df['predicted_price'].min(skipna=True)) - 20
                y_max = max(df['actual_price'].max(), df['predicted_price'].max(skipna=True)) + 20
                ax.set_ylim(y_min, y_max)

                st.pyplot(fig)

    except Exception as e:
        with plot_placeholder.container():
            cols = st.columns([1, 2])

            with cols[0]:
                st.subheader("📋 Live Status")
                st.error(f"Error displaying values: {e}")

            with cols[1]:
                st.subheader("📈 Live Plot (Last 120 points, Predicted at t+2)")
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(df['timestamp'], df['actual_price'], label="Actual Price", color='blue', linewidth=2)
                ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)", color='red', marker='x', linestyle='None', markersize=4)

                ax.set_xlabel("Timestamp")
                ax.set_ylabel("Bitcoin Price")
                ax.set_title("Bitcoin Actual vs Predicted Price (t+2)")
                ax.grid(True)
                ax.legend()

                y_min = min(df['actual_price'].min(), df['predicted_price'].min(skipna=True)) - 20
                y_max = max(df['actual_price'].max(), df['predicted_price'].max(skipna=True)) + 20
                ax.set_ylim(y_min, y_max)

                st.pyplot(fig)

    time.sleep(5)
