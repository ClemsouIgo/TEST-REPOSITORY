import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime
import re

# --- Config ---
BASE_DIR = Path(__file__).resolve().parent
TODAY = datetime.now().strftime("%d_%m_%Y")

def get_folder_with_today_or_latest(base_folder: Path) -> Path:
    today_folder = base_folder / TODAY
    if today_folder.exists():
        return today_folder

    candidates = [f for f in base_folder.iterdir()
                  if f.is_dir() and re.match(r"^\d{2}_\d{2}_\d{4}$", f.name)]
    if not candidates:
        return today_folder

    parsed = []
    for f in candidates:
        try:
            dt = datetime.strptime(f.name, "%d_%m_%Y")
            parsed.append((dt, f))
        except ValueError:
            continue
    latest_folder = max(parsed, key=lambda x: x[0])[1]
    return latest_folder

CHART_FOLDER_PICKLE = get_folder_with_today_or_latest(BASE_DIR / "Chart_Data")

# --- Helper functions ---

def load_pickle_chart(path: Path):
    with open(path, "rb") as f:
        return pickle.load(f)

def list_pickle_files(folder: Path):
    if not folder.exists():
        return []
    return sorted(folder.glob("*.pkl"))

def draw_chart(fig, ma_periods=None):
    x_vals = pd.Series(fig.data[0].x)
    y_vals = pd.Series(fig.data[0].y)

    if ma_periods:
        for ma in ma_periods:
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals.rolling(ma).mean(),
                mode="lines",
                name=f"MA{ma}",
                line=dict(dash="dot")
            ))

    st.plotly_chart(fig, use_container_width=True)

def draw_zscore_chart(x_vals, y_vals, zscore_periods):
    z_fig = go.Figure()

    for i, period in enumerate(zscore_periods):
        mean = y_vals.rolling(period).mean()
        std = y_vals.rolling(period).std()
        z_scores = (y_vals - mean) / std

        z_fig.add_trace(go.Scatter(
            x=x_vals,
            y=z_scores,
            mode="lines+markers",
            name=f"Z-Score {period}",
            line=dict(color=f"rgba({100+i*40 % 255},{50+i*30 % 255},200,1)")
        ))

    for level in [-3, -2, -1, 1, 2, 3]:
        z_fig.add_shape(
            type="line",
            x0=x_vals.iloc[0],
            x1=x_vals.iloc[-1],
            y0=level,
            y1=level,
            line=dict(
                color="red" if abs(level) == 3 else ("orange" if abs(level) == 2 else "gray"),
                dash="dash"
            )
        )
        z_fig.add_annotation(
            x=x_vals.iloc[-1],
            y=level,
            text=f"Z={level}",
            showarrow=False,
            yanchor="bottom" if level > 0 else "top",
            font=dict(size=10, color="black"),
            bgcolor="white",
            bordercolor="gray",
            borderwidth=1
        )

    z_fig.update_layout(title="Z-Score Chart", xaxis_title="Time", yaxis_title="Z-Score")
    st.plotly_chart(z_fig, use_container_width=True)

# --- Streamlit App ---

st.set_page_config(layout="wide")
st.title("\U0001F4CA Chart Viewer & CSV Explorer")

chart_tab, csv_tab = st.tabs(["Saved Charts", "CSV Viewer"])

# --- Tab 1: Saved Charts ---
with chart_tab:
    st.header("\U0001F4C1 Load Saved Chart")

    folder = CHART_FOLDER_PICKLE
    files = list_pickle_files(folder)

    if not files:
        st.warning(f"No pickle files found in {folder}")
    else:
        selected_file = st.selectbox("Choose a chart:", files, format_func=lambda x: x.name)

        if selected_file:
            fig = load_pickle_chart(selected_file)

            ma_input = st.text_input("Add Moving Averages (comma-separated):", "", key="ma_input_chart")
            ma_periods = [int(x.strip()) for x in ma_input.split(",") if x.strip().isdigit()]

            show_zscore = st.checkbox("Show Z-Score", key="zscore_checkbox_chart")
            zscore_period = 20

            draw_chart(fig, ma_periods=ma_periods)

            if show_zscore:
                zscore_input = st.text_input("Add Z-Score Periods (comma-separated):", str(zscore_period), key="zscore_input_chart")
                zscore_periods = [int(x.strip()) for x in zscore_input.split(",") if x.strip().isdigit()]
                x_vals = pd.Series(fig.data[0].x)
                y_vals = pd.Series(fig.data[0].y)
                draw_zscore_chart(x_vals, y_vals, zscore_periods)

# --- Tab 2: CSV Viewer ---
with csv_tab:
    st.header("\U0001F4C4 CSV Chart Viewer")
    uploaded_file = st.file_uploader("Upload CSV file", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Data Preview:", df.head())

        cols = df.columns.tolist()
        x_col = st.selectbox("X Axis", cols, key="x_axis_csv")
        y_col = st.selectbox("Y Axis", cols, index=1 if len(cols) > 1 else 0, key="y_axis_csv")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode='lines+markers', name=y_col))

        ma_input_csv = st.text_input("Add Moving Averages (comma-separated):", "", key="ma_input_csv")
        ma_periods_csv = [int(x.strip()) for x in ma_input_csv.split(",") if x.strip().isdigit()]
        for ma in ma_periods_csv:
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col].rolling(ma).mean(),
                mode="lines",
                name=f"MA{ma}",
                line=dict(dash="dot")
            ))

        fig.update_layout(title=f"{y_col} over {x_col}", xaxis_title=x_col, yaxis_title=y_col)
        st.plotly_chart(fig, use_container_width=True)

        show_zscore_csv = st.checkbox("Show Z-Score", key="zscore_checkbox_csv")
        if show_zscore_csv:
            zscore_input_csv = st.text_input("Add Z-Score Periods (comma-separated):", "20", key="zscore_input_csv")
            zscore_periods_csv = [int(x.strip()) for x in zscore_input_csv.split(",") if x.strip().isdigit()]
            x_vals_csv = pd.Series(df[x_col])
            y_vals_csv = pd.Series(df[y_col])
            draw_zscore_chart(x_vals_csv, y_vals_csv, zscore_periods_csv)
