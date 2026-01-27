import streamlit as st
import pandas as pd
import os

BASE_DIR = "pipeline_time_sequence"

TIMELINE_FILE = os.path.join(BASE_DIR, "cleaned_events_chronological.csv")
UNIQUE_USERS_FILE = os.path.join(BASE_DIR, "unique_users_list.csv")

for f in [TIMELINE_FILE, UNIQUE_USERS_FILE]:
    if not os.path.exists(f):
        st.error(f"Missing required file: {f}")
        st.stop()

df = pd.read_csv(TIMELINE_FILE)
users_df = pd.read_csv(UNIQUE_USERS_FILE)

df["event_time"] = pd.to_datetime(df["event_time"], format="ISO8601")

st.set_page_config(
    page_title="User Event Timeline",
    layout="wide"
)

st.title("User Event Timeline")

total_users = users_df["user_uuid"].nunique()
total_events = len(df)

col1, col2 = st.columns(2)
col1.metric("Total Unique Users", total_users)

st.divider()

user_ids = users_df["user_uuid"].sort_values().tolist()
selected_user = st.selectbox("Select User ID", user_ids)

user_df = df[df["user_uuid"] == selected_user]

user_event_count = len(user_df)
user_unique_events = user_df["event_name"].nunique()

col3, col4 = st.columns(2)
col3.metric("Events for Selected User", user_event_count)
col4.metric("Unique Event Types", user_unique_events)

st.divider()

user_events = (
    user_df["event_name"]
    .sort_values()
    .unique()
    .tolist()
)

selected_event = st.selectbox(
    "Select Event",
    ["All Events"] + user_events
)

if selected_event == "All Events":
    timeline_df = user_df
else:
    timeline_df = user_df[user_df["event_name"] == selected_event]

timeline_df = timeline_df.sort_values("event_time")

st.subheader("Event Timeline")

display_cols = [
    "event_date",
    "event_day",
    "event_time_only",
    "event_name",
    "category"
]

st.dataframe(
    timeline_df[display_cols],
    use_container_width=True,
    hide_index=True
)
