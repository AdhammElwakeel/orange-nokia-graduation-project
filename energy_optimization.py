import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


INPUT_FILE = "network_data_with_efficiency.csv"
OUTPUT_FILE = "decision_results.csv"

SLEEP_THRESHOLD = 0.15
MAX_LOAD = 0.85
MIN_ACTIVE_CELLS = 2


df = pd.read_csv(INPUT_FILE)
df["Time"] = pd.to_datetime(df["Time"])
df["Load_Ratio"] = pd.to_numeric(df["Load_Ratio"], errors="coerce")
cells = sorted(df["Cell"].unique())

print("=" * 70)
print("AI-BASED NETWORK ENERGY OPTIMIZATION")
print("=" * 70)
print(f"Number of cells: {len(cells)}")
print(f"Cells: {', '.join(cells)}")
print()


def distribute_load(load_to_move, active_cells):
    if not active_cells:
        return None

    available_capacity = {}
    for cell, load in active_cells.items():
        capacity = MAX_LOAD - load
        if capacity > 0:
            available_capacity[cell] = capacity

    total_capacity = sum(available_capacity.values())
    if total_capacity < load_to_move - 1e-9:
        return None

    distribution = {}
    remaining = load_to_move
    sorted_cells = sorted(
        available_capacity.items(), key=lambda x: x[1], reverse=True
    )

    for cell, capacity in sorted_cells:
        if remaining <= 1e-9:
            break

        amount = min(remaining, capacity)
        distribution[cell] = amount
        remaining -= amount

    if remaining > 1e-9:
        return None

    return distribution


def process_timestamp(time_data):
    loads = dict(zip(time_data["Cell"], time_data["Load_Ratio"]))
    states = {cell: "ACTIVE" for cell in cells}
    final_loads = loads.copy()
    distributions = {}

    candidates = [cell for cell in cells if loads[cell] < SLEEP_THRESHOLD]
    candidates = sorted(candidates, key=lambda cell: loads[cell])

    for sleeping_cell in candidates:
        current_active = [cell for cell in cells if states[cell] == "ACTIVE"]
        if len(current_active) <= MIN_ACTIVE_CELLS:
            break

        load_to_move = final_loads[sleeping_cell]
        receiver_cells = {
            cell: final_loads[cell]
            for cell in current_active
            if cell != sleeping_cell
        }
        distribution = distribute_load(load_to_move, receiver_cells)

        if distribution is None:
            states[sleeping_cell] = "STANDBY"
            continue

        valid = True
        for receiver, amount in distribution.items():
            new_load = final_loads[receiver] + amount
            if new_load > MAX_LOAD + 1e-9:
                valid = False
                break

        if not valid:
            states[sleeping_cell] = "STANDBY"
            continue

        states[sleeping_cell] = "SLEEP"
        distributions[sleeping_cell] = distribution
        final_loads[sleeping_cell] = 0

        for receiver, amount in distribution.items():
            final_loads[receiver] += amount

    active_cells = [cell for cell in cells if states[cell] == "ACTIVE"]
    if len(active_cells) < MIN_ACTIVE_CELLS:
        sleeping_cells = [cell for cell in cells if states[cell] == "SLEEP"]

        for cell in reversed(sleeping_cells):
            states[cell] = "ACTIVE"
            final_loads[cell] = loads[cell]
            if cell in distributions:
                del distributions[cell]

            active_cells = [c for c in cells if states[c] == "ACTIVE"]
            if len(active_cells) >= MIN_ACTIVE_CELLS:
                break

    return states, final_loads, distributions


results = []
all_distributions = []

for time, time_data in df.groupby("Time"):
    states, final_loads, distributions = process_timestamp(time_data)
    loads = dict(zip(time_data["Cell"], time_data["Load_Ratio"]))

    original_energy = time_data["Energy_W"].sum()
    sleeping_cells = [cell for cell in cells if states[cell] == "SLEEP"]
    sleeping_energy = time_data[time_data["Cell"].isin(sleeping_cells)]["Energy_W"].sum()
    actual_energy = original_energy - sleeping_energy

    if original_energy > 0:
        saving_percent = (sleeping_energy / original_energy) * 100
    else:
        saving_percent = 0

    for cell in cells:
        original_load = loads[cell]
        new_load = final_loads[cell]
        state = states[cell]

        if cell in distributions:
            receivers = distributions[cell]
            receiver_text = "; ".join(
                f"{receiver}: +{amount * 100:.2f}%"
                for receiver, amount in receivers.items()
            )
        else:
            receiver_text = ""

        received_from = []
        for source_cell, distribution in distributions.items():
            if cell in distribution:
                received_from.append(
                    f"{source_cell}: +{distribution[cell] * 100:.2f}%"
                )

        received_text = "; ".join(received_from)
        results.append({
            "Time": time,
            "Cell": cell,
            "Original_Load_%": round(original_load * 100, 2),
            "Final_Load_%": round(new_load * 100, 2),
            "State": state,
            "Load_Sent_To": receiver_text,
            "Load_Received_From": received_text,
            "Number_of_Active_Cells": len([
                c for c in cells if states[c] == "ACTIVE"
            ]),
            "Number_of_Sleeping_Cells": len(sleeping_cells),
            "Number_of_Standby_Cells": len([
                c for c in cells if states[c] == "STANDBY"
            ]),
            "Energy_Baseline_W": round(original_energy, 2),
            "Energy_After_Optimization_W": round(actual_energy, 2),
            "Energy_Saving_%": round(saving_percent, 2),
        })


results_df = pd.DataFrame(results)
results_df.to_csv(OUTPUT_FILE, index=False)

print()
print("=" * 70)
print("DECISION ENGINE FINISHED")
print("=" * 70)
print()
print(f"Output file created: {OUTPUT_FILE}")

print()
print("SAMPLE DECISIONS")
print("=" * 70)

sleep_times = results_df[results_df["State"] == "SLEEP"]["Time"].unique()
for time in sleep_times[:10]:
    temp = results_df[results_df["Time"] == time]
    print()
    print(f"TIME: {time}")

    for _, row in temp.iterrows():
        print(
            f"{row['Cell']}: "
            f"{row['Original_Load_%']:.2f}% "
            f"-> "
            f"{row['Final_Load_%']:.2f}% "
            f"| {row['State']}"
        )

        if row["Load_Sent_To"]:
            print(f"   Load sent to: {row['Load_Sent_To']}")

        if row["Load_Received_From"]:
            print(f"   Load received from: {row['Load_Received_From']}")


optimization_times = results_df[
    results_df["Number_of_Sleeping_Cells"] > 0
]["Time"].unique()

if len(optimization_times) > 0:
    selected_time = optimization_times[0]
    graph_data = results_df[results_df["Time"] == selected_time].copy()
    x = np.arange(len(cells))
    width = 0.35

    original = [
        graph_data[graph_data["Cell"] == cell]["Original_Load_%"].iloc[0]
        for cell in cells
    ]
    final = [
        graph_data[graph_data["Cell"] == cell]["Final_Load_%"].iloc[0]
        for cell in cells
    ]

    plt.figure(figsize=(10, 6))
    plt.bar(x - width / 2, original, width, label="Original Load")
    plt.bar(x + width / 2, final, width, label="Final Load")
    plt.axhline(85, linestyle="--", label="85% Maximum Load")
    plt.axhline(15, linestyle=":", label="15% Sleep Threshold")
    plt.xticks(x, cells)
    plt.ylabel("Load (%)")
    plt.xlabel("Cell")
    plt.title(f"Cell Load Before vs After Optimization\n{selected_time}")
    plt.legend()
    plt.tight_layout()
    plt.show()


energy_data = (
    results_df[["Time", "Energy_Saving_%"]]
    .drop_duplicates()
    .sort_values("Time")
)

plt.figure(figsize=(12, 6))
plt.plot(energy_data["Time"], energy_data["Energy_Saving_%"])
plt.xlabel("Time")
plt.ylabel("Energy Saving (%)")
plt.title("Network Energy Saving Over Time")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


state_data = (
    results_df[
        [
            "Time",
            "Number_of_Active_Cells",
            "Number_of_Sleeping_Cells",
            "Number_of_Standby_Cells",
        ]
    ]
    .drop_duplicates()
    .sort_values("Time")
)

plt.figure(figsize=(12, 6))
plt.plot(
    state_data["Time"],
    state_data["Number_of_Active_Cells"],
    label="Active",
)
plt.plot(
    state_data["Time"],
    state_data["Number_of_Sleeping_Cells"],
    label="Sleep",
)
plt.plot(
    state_data["Time"],
    state_data["Number_of_Standby_Cells"],
    label="Standby",
)
plt.xlabel("Time")
plt.ylabel("Number of Cells")
plt.title("Network Cell States Over Time")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.show()


if len(optimization_times) > 0:
    selected_time = optimization_times[0]
    temp = results_df[results_df["Time"] == selected_time]
    sleeping = temp[temp["State"] == "SLEEP"]

    for _, row in sleeping.iterrows():
        if row["Load_Sent_To"]:
            print()
            print("=" * 70)
            print(f"LOAD DISTRIBUTION: {row['Cell']}")
            print("=" * 70)
            print(
                f"{row['Cell']} "
                f"went to SLEEP "
                f"with original load "
                f"{row['Original_Load_%']}%"
            )
            print()
            print("Its load was distributed to:")
            print(row["Load_Sent_To"])


print()
print("=" * 70)
print("ALL DONE")
print("=" * 70)
