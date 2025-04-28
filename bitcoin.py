import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets credentials from Streamlit Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open("BitcoinRealtimeData").sheet1  # Match sheet name

# Function to get the latest data
def get_latest_data():
    data = sheet.get_all_values()[1:]  # Skipping header
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

# Initialize placeholders
plot_placeholder = st.empty()
text_placeholder = st.empty()

# Initialize state variables
previous_rating = None
holdings = []
total_profit = 0
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

        # Determine rating based on prediction
        if np.isnan(predicted_price):
            rating = None
        else:
            rating = "Buy" if (predicted_price - actual_price) >= 0 else "Sell"

        if rating is not None:
            if previous_rating is None:
                previous_rating = rating

            if rating == previous_rating:
                if rating == "Buy":
                    holdings.append(actual_price)
                else:
                    holdings.append(-actual_price)
            else:
                if holdings:
                    units = len(holdings)
                    avg_entry_price = sum(holdings) / units

                    if previous_rating == "Buy":
                        profit = (actual_price * units) - sum(holdings)
                    else:
                        profit = sum(holdings) + (actual_price * units)

                    total_profit += profit

                holdings = []
                if rating == "Buy":
                    holdings.append(actual_price)
                else:
                    holdings.append(-actual_price)

                previous_rating = rating

        # Display updated values
        with text_placeholder.container():
            st.write(f"**Predicted Price:** {predicted_price}")
            st.write(f"**Timestamp for Prediction:** {predicted_timestamp}")
            st.write(f"**Timestamp for Actual Price:** {actual_timestamp}")
            st.write(f"**Actual Price:** {actual_price}")

            # Show rating with color
            if rating == "Buy":
                st.success(f"Rating: {rating}")
            elif rating == "Sell":
                st.error(f"Rating: {rating}")
            else:
                st.write(f"Rating: {rating}")

            st.write(f"**Current Holdings:** {holdings}")
            st.write(f"**Total Profit/Loss:** {total_profit:.2f}")

            current_time = datetime.now().strftime("%I:%M:%S %p")

            if actual_timestamp == last_processed_timestamp:
                st.info(f"⏳ Waiting for new data update... (Last checked at {current_time})")
            else:
                st.success(f"✅ New data processed. (at {current_time})")

        # Update plot
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

            y_min = min(df['actual_price'].min(), df['predicted_price'].min(skipna=True)) - 20
            y_max = max(df['actual_price'].max(), df['predicted_price'].max(skipna=True)) + 20
            ax.set_ylim(y_min, y_max)

            st.pyplot(fig)

        # Update last processed timestamp after successful processing
        last_processed_timestamp = actual_timestamp

    except Exception as e:
        with text_placeholder.container():
            st.error(f"Error displaying values: {e}")

    time.sleep(5)
