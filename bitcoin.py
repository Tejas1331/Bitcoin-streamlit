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

        if actual_timestamp == last_processed_timestamp:
            with status_placeholder.container():
                st.info("⏳ Waiting for new data update...")
            time.sleep(5)
            continue

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

        last_processed_timestamp = actual_timestamp

        # 🔥 NEW layout using columns
        with plot_placeholder.container():
            col1, col2 = st.columns([1, 2])  # 1/3 screen for info, 2/3 screen for plot

            with col1:
                st.markdown("### Latest Information")
                st.metric("Predicted Price", f"${predicted_price:.2f}" if not np.isnan(predicted_price) else "N/A")
                st.metric("Actual Price", f"${actual_price:.2f}")
                st.metric("Rating", f"{rating}" if rating else "No prediction yet")
                st.metric("Holdings (count)", f"{len(holdings)} units")
                st.metric("Total Profit/Loss", f"${total_profit:.2f}")

            with col2:
                st.subheader("Live Plot (Last 120 points, Predicted at t+2)")

                fig, ax = plt.subplots(figsize=(12, 5))
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

        with status_placeholder.container():
            st.success("✅ New data processed.")

    except Exception as e:
        with text_placeholder.container():
            st.error(f"Error displaying values: {e}")

    time.sleep(5)
