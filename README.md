# Orange Nokia Graduation Project

## Run the dashboard

Install the required packages:

```bash
python3 -m pip install pandas streamlit altair
```

Start the dashboard:

```bash
cd ~/Desktop/orange-nokia-graduation-project
streamlit run app.py
```

The dashboard automatically uses `dataset/network_data_with_efficiency.csv`. You can also upload another CSV with `Time`, `Cell`, `Load_Ratio`, and `Energy_W` columns.

It keeps at least two cells active, compares before/after load at two timestamps, and lets you download the decision results.
