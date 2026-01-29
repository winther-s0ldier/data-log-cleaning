import streamlit as st
import pandas as pd
import os

from insights.journey_builder import (
    build_user_journey,
    format_journey_for_display,
    get_journey_dataframe,
    build_mermaid_flowchart,
    split_into_sessions
)
from insights.payload_builder import build_ai_payload
from insights.journey_interpreter import interpret_journey_safe
from insights.insights_generator import generate_insights_safe, generate_insights_stream
from insights.components.session_renderer import render_session_cards
from insights.components.ai_session_renderer import render_ai_session_cards

BASE_DIR = "pipeline_deduplication"
CLEANED_EVENTS_FILE = os.path.join(BASE_DIR, "cleaned_events.csv")
REPETITION_SUMMARY_FILE = os.path.join(BASE_DIR, "repetition_summary.csv")
UNIQUE_USERS_FILE = os.path.join(BASE_DIR, "unique_users_list.csv")

for f in [CLEANED_EVENTS_FILE, REPETITION_SUMMARY_FILE, UNIQUE_USERS_FILE]:
    if not os.path.exists(f):
        st.error(f"Missing required file: {f}")
        st.stop()

df = pd.read_csv(CLEANED_EVENTS_FILE)
rep_df = pd.read_csv(REPETITION_SUMMARY_FILE)
users_df = pd.read_csv(UNIQUE_USERS_FILE)

st.set_page_config(page_title="Product Analytics Dashboard", layout="wide")
st.title("Product Analytics Dashboard")

total_users = users_df["user_uuid"].nunique()
total_events = len(df)

g1, g2 = st.columns(2)
g1.metric("Total Unique Users", total_users)
g2.metric("Total Cleaned Events", total_events)

st.divider()

user_ids = users_df["user_uuid"].sort_values().tolist()
selected_user = st.selectbox("Select User ID", user_ids)

user_df = df[df["user_uuid"] == selected_user]
user_rep_df = rep_df[rep_df["user_uuid"] == selected_user]

app_user_df = user_df[user_df["category"].str.lower() == "application"]
app_user_rep_df = user_rep_df[
    user_rep_df["category"].str.lower() == "application"] if "category" in user_rep_df.columns else user_rep_df

journey_data = build_user_journey(app_user_df)

u1, u2, u3 = st.columns(3)
u1.metric("Application Events", len(app_user_df))
u2.metric("Unique Event Types", app_user_df["event_name"].nunique())
u3.metric(
    "Span (Days)",
    journey_data["metadata"]["date_range"]["span_days"]
    if journey_data["total_events"] > 0
    else 0
)

st.divider()

main_tab1, main_tab2 = st.tabs(["Data", "Analysis"])

with main_tab1:
    st.header("User Data")

    user_events = app_user_df["event_name"].sort_values().unique().tolist()
    selected_event = st.selectbox("Select Event", ["All Events"] + user_events)

    if selected_event == "All Events":
        view_df = app_user_df
    else:
        view_df = app_user_df[app_user_df["event_name"] == selected_event]

    view_df = view_df.sort_values(["event_date", "event_time_only"])

    st.subheader("Events")

    display_cols = ["event_date", "event_day", "event_time_only", "event_name", "category"]
    st.dataframe(view_df[display_cols], use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Repetition Summary")

    summary_view = app_user_rep_df.copy()
    if selected_event != "All Events":
        summary_view = summary_view[summary_view["event_name"] == selected_event]

    st.dataframe(summary_view, use_container_width=True, hide_index=True)

with main_tab2:
    st.header("Journey Analysis")

    analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs([
        "User Journey",
        "AI Journey Interpretation",
        "AI Insights"
    ])

    with analysis_tab1:
        st.subheader("User Journey")

        if journey_data["total_events"] == 0:
            st.info("No events found for this user.")
        else:
            st.markdown(f"**Events:** {journey_data['total_events']}")
            st.markdown(
                f"**Time Range:** {journey_data['metadata']['date_range']['first_event']} to {journey_data['metadata']['date_range']['last_event']}")

            sessions = split_into_sessions(journey_data["events"], gap_minutes=30)
            st.markdown(f"**Sessions Detected:** {len(sessions)} (based on 30-minute gaps)")

            render_session_cards(sessions, height=350)

            with st.expander("View Event Breakdown"):
                breakdown_df = (
                    pd.DataFrame(
                        journey_data["metadata"]["event_breakdown"].items(),
                        columns=["Event Name", "Count"]
                    )
                    .sort_values("Count", ascending=False)
                )
                st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

    with analysis_tab2:
        st.subheader("AI Journey Interpretation")

        if st.button("Generate AI Interpretation", key="btn_ai_journey"):
            with st.spinner("Analyzing user journey..."):
                payload = build_ai_payload(app_user_df, app_user_rep_df, selected_user)
                result = interpret_journey_safe(payload)

            if result["success"]:
                if result.get("is_structured") and result.get("parsed"):
                    render_ai_session_cards(result["parsed"], height=450)
                else:
                    st.warning("AI did not return structured data. Showing text response:")
                    st.markdown(result["content"])
            else:
                st.error(result["error"])

    with analysis_tab3:
        st.subheader("AI-Generated Insights")

        if st.button("Generate AI Insights", key="btn_ai_insights"):
            payload = build_ai_payload(app_user_df, app_user_rep_df, selected_user)
            st.write_stream(generate_insights_stream(payload))

st.divider()
st.caption("All AI analysis is strictly per-user and filtered to application events only.")
