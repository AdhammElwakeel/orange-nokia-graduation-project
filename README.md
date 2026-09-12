# Orange Nokia Graduation Project

## Run the dashboard

Install the required packages:

```bash
python3 -m pip install pandas streamlit
```

Start the dashboard:

```bash
cd ~/Desktop/orange-nokia-graduation-project
streamlit run app.py
```

Upload a `cell_sleep_distribution_report.csv` file in the sidebar to view its energy, cell-state, and load-distribution results. On this computer, the dashboard automatically loads `~/Desktop/cell_sleep_distribution_report.csv` when no file is uploaded.
