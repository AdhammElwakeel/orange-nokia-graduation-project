from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from energy_optimization import MAX_LOAD, MIN_ACTIVE_CELLS, SLEEP_THRESHOLD, optimize


INPUT_FILE = Path(__file__).with_name("dataset") / "network_data_with_efficiency.csv"


def load_chart(data, title):
    cells = data["Cell"].tolist()
    loads = data.melt(
        id_vars="Cell",
        value_vars=["Original_Load_%", "Final_Load_%"],
        var_name="Load",
        value_name="Load (%)",
    ).replace({"Original_Load_%": "Original Load", "Final_Load_%": "Final Load"})
    bars = alt.Chart(loads).mark_bar().encode(
        x=alt.X("Cell:N", sort=cells, title="Cell"),
        xOffset="Load:N",
        y=alt.Y("Load (%):Q", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("Load:N", title=None),
        tooltip=["Cell:N", "Load:N", "Load (%):Q"],
    )
    maximum = alt.Chart(pd.DataFrame({"Load (%)": [MAX_LOAD * 100]})).mark_rule(
        color="#1f77b4", strokeDash=[6, 4]
    ).encode(y="Load (%):Q")
    threshold = alt.Chart(pd.DataFrame({"Load (%)": [SLEEP_THRESHOLD * 100]})).mark_rule(
        color="#ff7f0e", strokeDash=[2, 2]
    ).encode(y="Load (%):Q")
    return alt.layer(bars, maximum, threshold).properties(title=title, height=400)


st.set_page_config(page_title="Network Energy Optimization", layout="wide")
st.title("AI-Based Network Energy Optimization")
st.caption("Dashed line: 85% maximum load. Dotted line: 15% sleep threshold.")

uploaded_file = st.sidebar.file_uploader("Upload network data CSV", type="csv")
try:
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
    elif INPUT_FILE.exists():
        data = pd.read_csv(INPUT_FILE)
    else:
        st.info("Upload a network data CSV to view its optimization results.")
        st.stop()
    results = optimize(data)
except (OSError, UnicodeDecodeError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Could not optimize the CSV: {error}")
    st.stop()

summary = results.drop_duplicates("Time").sort_values("Time")
total_before = summary["Energy_Baseline_W"].sum()
total_after = summary["Energy_After_Optimization_W"].sum()
saving_percent = (total_before - total_after) / total_before * 100 if total_before else 0

first, second, third, fourth = st.columns(4)
first.metric("Baseline energy", f"{total_before:.2f} W")
second.metric("Optimized energy", f"{total_after:.2f} W")
third.metric("Energy saving", f"{saving_percent:.2f}%")
fourth.metric("Minimum active cells", int(summary["Number_of_Active_Cells"].min()))

st.subheader("Energy Saving Over Time")
st.line_chart(summary.set_index("Time")[["Energy_Saving_%"]])

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

times = summary["Time"].tolist()
if len(times) < 2:
    st.error("The dataset needs at least two timestamps for comparison.")
    st.stop()

st.subheader("Compare Two Timestamps")
left, right = st.columns(2)
first_time = left.selectbox("First timestamp", times, format_func=str)
second_time = right.selectbox(
    "Second timestamp", [time for time in times if time != first_time], format_func=str
)

first_data = results[results["Time"] == first_time].sort_values("Cell")
second_data = results[results["Time"] == second_time].sort_values("Cell")
left.altair_chart(load_chart(first_data, str(first_time)), use_container_width=True)
right.altair_chart(load_chart(second_data, str(second_time)), use_container_width=True)

load_change = (
    first_data.set_index("Cell")["Final_Load_%"]
    .rename("First timestamp")
    .to_frame()
    .join(second_data.set_index("Cell")["Final_Load_%"].rename("Second timestamp"))
)
load_change["Final Load Change (%)"] = (
    load_change["Second timestamp"] - load_change["First timestamp"]
)
st.subheader("Final Load Change Between Timestamps")
st.bar_chart(load_change[["Final Load Change (%)"]])

st.subheader("Decisions")
st.dataframe(second_data, use_container_width=True, hide_index=True)
st.download_button(
    "Download decision results",
    results.to_csv(index=False).encode(),
    "decision_results.csv",
    "text/csv",
)
