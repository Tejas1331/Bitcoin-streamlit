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
text_placeholder = st.empty()
status_placeholder = st.empty()  # <-- For showing status like "Waiting for new data..."

holdings = []
previous_rating = None
total_profit = 0
last_processed_timestamp = None  # <-- NEW

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
            with status_placeholder.container():
                st.info("⏳ Waiting for new data update...")
            time.sleep(5)
            continue  # Skip to next loop

        # Process only new data
        if np.isnan(predicted_price):
            rating = None
        else:
            rating = "Buy" if (predicted_price - actual_price) >= 0 else "Sell"

        if rating is not None:
            if previous_rating is None:
                previous_rating = rating

            if rating == previous_rating:
                # Continue adding to holdings
                if rating == "Buy":
                    holdings.append(actual_price)
                else:  # rating == "Sell"
                    holdings.append(-actual_price)
            else:
                # Rating changed → Book profit or loss
                if holdings:
                    units = len(holdings)
                    avg_entry_price = sum(holdings) / units  # Net entry price

                    # Exit at current actual price
                    if previous_rating == "Buy":
                        # Sell all buys
                        profit = (actual_price * units) - sum(holdings)
                    else:
                        # Buy back all sells
                        profit = sum(holdings) + (actual_price * units)

                    total_profit += profit

                # Reset holdings for new rating
                holdings = []
                if rating == "Buy":
                    holdings.append(actual_price)
                else:
                    holdings.append(-actual_price)

                previous_rating = rating

        # Update last processed timestamp
        last_processed_timestamp = actual_timestamp

        # Display updated values in compact format
        with text_placeholder.container():
            st.write(f"**Predicted Price:** {predicted_price}  |  **Rating:** {rating}  |  **Actual Price:** {actual_price}")
            st.write(f"**Total Profit/Loss:** {total_profit:.2f}")

        with status_placeholder.container():
            st.success("✅ New data processed.")

    except Exception as e:
        with text_placeholder.container():
            st.error(f"Error displaying values: {e}")

    # Update the plot with more compact settings
    with plot_placeholder.container():
        st.subheader("Live Plot (Last 120 points, Predicted at t+2)")

        fig, ax = plt.subplots(figsize=(8, 3))  # Smaller plot for compactness
        ax.plot(df['timestamp'], df['actual_price'], label="Actual Price", color='blue', linewidth=1.5)
        ax.plot(df['predicted_timestamp'], df['predicted_price'], label="Predicted Price (t+2)", color='red', marker='x', linestyle='None', markersize=4)

        ax.set_xlabel("Timestamp", fontsize=8)
        ax.set_ylabel("Price", fontsize=8)
        ax.set_title("Bitcoin: Actual vs Predicted (t+2)", fontsize=9)
        ax.grid(True)
        ax.legend(fontsize=8)

        y_min = min(df['actual_price'].min(), df['predicted_price'].min(skipna=True)) - 20
        y_max = max(df['actual_price'].max(), df['predicted_price'].max(skipna=True)) + 20
        ax.set_ylim(y_min, y_max)

        st.pyplot(fig)

    # Delay to simulate real-time updates
    time.sleep(5)
