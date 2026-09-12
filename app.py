from pathlib import Path

import pandas as pd
import streamlit as st


REPORT_FILE = Path.home() / "Desktop" / "cell_sleep_distribution_report.csv"
def distribution_chart_data(distribution):
    if distribution == "-":
        return pd.DataFrame(columns=["Sleeping cell", "Receiving cell", "Load moved (%)"])

    rows = []
    for transfer in distribution.split(" | "):
        source, receivers = transfer.split(" -> ", 1)
        for receiver in receivers.split(", "):
            cell, percentage = receiver.rsplit(" (", 1)
            rows.append({
                "Sleeping cell": source,
                "Receiving cell": cell,
                "Load moved (%)": float(percentage.removesuffix("%)")),
            })
    return pd.DataFrame(rows)


REQUIRED_COLUMNS = {
    "Time",
    "Sleep_Cells",
    "Standby_Cells",
    "Active_Cells",
    "Load_Distribution",
    "Sleep_Count",
    "Standby_Count",
    "Active_Count",
    "Total_Energy_Saved_W",
    "Total_Energy_Before_W",
    "Savings_pct",
}

st.set_page_config(page_title="Network Energy Optimization", layout="wide")
st.title("AI-Based Network Energy Optimization")

uploaded_file = st.sidebar.file_uploader(
    "Upload cell sleep distribution report", type="csv"
)
try:
    if uploaded_file:
        report = pd.read_csv(uploaded_file)
    elif REPORT_FILE.exists():
        report = pd.read_csv(REPORT_FILE)
    else:
        st.info("Upload a cell sleep distribution report CSV to view its results.")
        st.stop()
except (OSError, UnicodeDecodeError, pd.errors.ParserError) as error:
    st.error(f"Could not read the CSV: {error}")
    st.stop()

missing = REQUIRED_COLUMNS - set(report.columns)
if missing:
    st.error(f"Missing required columns: {', '.join(sorted(missing))}")
    st.stop()

report["Time"] = pd.to_datetime(report["Time"], errors="coerce")
for column in [
    "Sleep_Count",
    "Standby_Count",
    "Active_Count",
    "Total_Energy_Saved_W",
    "Total_Energy_Before_W",
    "Savings_pct",
]:
    report[column] = pd.to_numeric(report[column], errors="coerce")
if report.isna().any().any():
    st.error("The report contains invalid dates or numeric values.")
    st.stop()

report = report.sort_values("Time")
total_before = report["Total_Energy_Before_W"].sum()
total_saved = report["Total_Energy_Saved_W"].sum()
total_after = total_before - total_saved
saving_percent = total_saved / total_before * 100 if total_before else 0

first, second, third = st.columns(3)
first.metric("Total baseline energy", f"{total_before:.2f} W")
second.metric("Energy after optimization", f"{total_after:.2f} W")
third.metric("Total energy saved", f"{saving_percent:.2f}%")

st.subheader("Energy Over Time")
st.line_chart(
    report.set_index("Time")[["Total_Energy_Before_W", "Total_Energy_Saved_W"]]
)

st.subheader("Cell States Over Time")
st.line_chart(report.set_index("Time")[["Active_Count", "Sleep_Count", "Standby_Count"]])

selected_time = st.selectbox("Select time", report["Time"], format_func=str)
selected = report[report["Time"] == selected_time].iloc[0]

st.subheader("Selected Decision")
sleeping, standby, active = st.columns(3)
sleeping.write("**Sleeping cells**")
sleeping.write(selected["Sleep_Cells"])
standby.write("**Standby cells**")
standby.write(selected["Standby_Cells"])
active.write("**Active cells**")
active.write(selected["Active_Cells"])

st.subheader("Load Distribution")
distribution = distribution_chart_data(selected["Load_Distribution"])
if distribution.empty:
    st.info("No load was moved at this time.")
else:
    st.bar_chart(
        distribution.pivot(
            index="Sleeping cell", columns="Receiving cell", values="Load moved (%)"
        ).fillna(0)
    )

st.subheader("All Decisions")
st.dataframe(report, use_container_width=True, hide_index=True)
st.download_button(
    "Download report",
    report.to_csv(index=False).encode(),
    "cell_sleep_distribution_report.csv",
    "text/csv",
)
