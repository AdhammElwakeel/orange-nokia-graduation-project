from pathlib import Path

import pandas as pd
import streamlit as st

from energy_optimization import optimize


DEFAULT_INPUT = Path(__file__).with_name("dataset") / "network_data_with_efficiency.csv"

st.set_page_config(page_title="Network Energy Optimization", layout="wide")
st.title("AI-Based Network Energy Optimization")

uploaded_file = st.sidebar.file_uploader("Upload network CSV", type="csv")
try:
    data = pd.read_csv(uploaded_file or DEFAULT_INPUT)
    results = optimize(data)
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.error(str(error))
    st.stop()

summary = results.drop_duplicates("Time").sort_values("Time")
baseline = summary["Energy_Baseline_W"].sum()
optimized = summary["Energy_After_Optimization_W"].sum()
saving = (baseline - optimized) / baseline * 100 if baseline else 0

first, second, third = st.columns(3)
first.metric("Total baseline energy", f"{baseline:.2f} W")
second.metric("Optimized energy", f"{optimized:.2f} W")
third.metric("Energy saving", f"{saving:.2f}%")

st.subheader("Energy Saving Over Time")
st.line_chart(summary.set_index("Time")["Energy_Saving_%"])

st.subheader("Cell States Over Time")
st.line_chart(
    summary.set_index("Time")[
        [
            "Number_of_Active_Cells",
            "Number_of_Sleeping_Cells",
            "Number_of_Standby_Cells",
        ]
    ]
)

selected_time = st.selectbox("Select time", summary["Time"], format_func=str)
selected = results[results["Time"] == selected_time].sort_values("Cell")

st.subheader("Load Before and After Optimization")
st.bar_chart(selected.set_index("Cell")[["Original_Load_%", "Final_Load_%"]])

st.subheader("Decisions")
st.dataframe(selected, use_container_width=True, hide_index=True)
st.download_button(
    "Download decision results",
    results.to_csv(index=False).encode(),
    "decision_results.csv",
    "text/csv",
)
