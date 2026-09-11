from pathlib import Path

import pandas as pd


INPUT_FILE = Path(__file__).with_name("dataset") / "network_data_with_efficiency.csv"
OUTPUT_FILE = Path(__file__).with_name("decision_results.csv")
SLEEP_THRESHOLD = 0.15
MAX_LOAD = 0.85
MIN_ACTIVE_CELLS = 2
REQUIRED_COLUMNS = {"Time", "Cell", "Load_Ratio", "Energy_W"}


def distribute_load(load_to_move, active_cells):
    available_capacity = {
        cell: MAX_LOAD - load
        for cell, load in active_cells.items()
        if load < MAX_LOAD
    }
    if sum(available_capacity.values()) < load_to_move - 1e-9:
        return None

    distribution = {}
    remaining = load_to_move
    for cell, capacity in sorted(
        available_capacity.items(), key=lambda item: item[1], reverse=True
    ):
        amount = min(remaining, capacity)
        if amount > 0:
            distribution[cell] = amount
            remaining -= amount
        if remaining <= 1e-9:
            return distribution

    return None


def process_timestamp(time_data, cells):
    loads = dict(zip(time_data["Cell"], time_data["Load_Ratio"]))
    states = {cell: "ACTIVE" for cell in cells}
    final_loads = loads.copy()
    distributions = {}

    candidates = sorted(
        (cell for cell in cells if loads[cell] < SLEEP_THRESHOLD),
        key=loads.__getitem__,
    )
    for sleeping_cell in candidates:
        active_cells = [cell for cell in cells if states[cell] == "ACTIVE"]
        if len(active_cells) <= MIN_ACTIVE_CELLS:
            break

        distribution = distribute_load(
            final_loads[sleeping_cell],
            {
                cell: final_loads[cell]
                for cell in active_cells
                if cell != sleeping_cell
            },
        )
        if distribution is None:
            states[sleeping_cell] = "STANDBY"
            continue

        states[sleeping_cell] = "SLEEP"
        final_loads[sleeping_cell] = 0
        distributions[sleeping_cell] = distribution
        for receiver, amount in distribution.items():
            final_loads[receiver] += amount

    return states, final_loads, distributions


def optimize(data):
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    data = data.copy()
    if data.empty or data["Cell"].isna().any():
        raise ValueError("The dataset must contain rows with a Cell value.")

    data["Time"] = pd.to_datetime(data["Time"], errors="coerce")
    data["Load_Ratio"] = pd.to_numeric(data["Load_Ratio"], errors="coerce")
    data["Energy_W"] = pd.to_numeric(data["Energy_W"], errors="coerce")
    if data[["Time", "Load_Ratio", "Energy_W"]].isna().any().any():
        raise ValueError("Time, Load_Ratio, and Energy_W must contain valid values.")
    if data.duplicated(["Time", "Cell"]).any():
        raise ValueError("Each Time and Cell pair must appear only once.")

    cells = sorted(data["Cell"].unique())
    if (data.groupby("Time")["Cell"].nunique() != len(cells)).any():
        raise ValueError("Every timestamp must include every cell.")

    results = []
    for time, time_data in data.groupby("Time"):
        states, final_loads, distributions = process_timestamp(time_data, cells)
        loads = dict(zip(time_data["Cell"], time_data["Load_Ratio"]))
        original_energy = time_data["Energy_W"].sum()
        sleeping_cells = [cell for cell in cells if states[cell] == "SLEEP"]
        sleeping_energy = time_data.loc[
            time_data["Cell"].isin(sleeping_cells), "Energy_W"
        ].sum()
        active_count = sum(state == "ACTIVE" for state in states.values())
        standby_count = sum(state == "STANDBY" for state in states.values())

        for cell in cells:
            sent_to = "; ".join(
                f"{receiver}: +{amount * 100:.2f}%"
                for receiver, amount in distributions.get(cell, {}).items()
            )
            received_from = "; ".join(
                f"{source}: +{distribution[cell] * 100:.2f}%"
                for source, distribution in distributions.items()
                if cell in distribution
            )
            results.append({
                "Time": time,
                "Cell": cell,
                "Original_Load_%": round(loads[cell] * 100, 2),
                "Final_Load_%": round(final_loads[cell] * 100, 2),
                "State": states[cell],
                "Load_Sent_To": sent_to,
                "Load_Received_From": received_from,
                "Number_of_Active_Cells": active_count,
                "Number_of_Sleeping_Cells": len(sleeping_cells),
                "Number_of_Standby_Cells": standby_count,
                "Energy_Baseline_W": round(original_energy, 2),
                "Energy_After_Optimization_W": round(
                    original_energy - sleeping_energy, 2
                ),
                "Energy_Saving_%": round(
                    sleeping_energy / original_energy * 100 if original_energy else 0, 2
                ),
            })

    return pd.DataFrame(results)


if __name__ == "__main__":
    results = optimize(pd.read_csv(INPUT_FILE))
    results.to_csv(OUTPUT_FILE, index=False)
    print(f"Output file created: {OUTPUT_FILE}")
