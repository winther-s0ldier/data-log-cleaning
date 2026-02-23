import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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

# Business-specific prompts
from insights.business_journey_interpreter import interpret_journey_safe as business_interpret_journey_safe
from insights.business_insights_generator import generate_insights_safe as business_generate_insights_safe
from insights.business_insights_generator import generate_insights_stream as business_generate_insights_stream

import app3_session_analysis
import app4_pattern_discovery
import app3_business_analysis
import app4_business_patterns

# ---- Data directories ----
USER_BASE_DIR = "pipeline_deduplication"
BUSINESS_BASE_DIR = "pipeline_business_deduplication"

st.set_page_config(page_title="Product Analytics Dashboard", layout="wide")
st.title("Product Analytics Dashboard")


def load_pipeline_data(base_dir):
    cleaned_file = os.path.join(base_dir, "cleaned_events.csv")
    rep_file = os.path.join(base_dir, "repetition_summary.csv")
    users_file = os.path.join(base_dir, "unique_users_list.csv")

    for f in [cleaned_file, rep_file, users_file]:
        if not os.path.exists(f):
            st.error(f"Missing required file: {f}")
            st.stop()

    df = pd.read_csv(cleaned_file)
    rep_df = pd.read_csv(rep_file)
    users_df = pd.read_csv(users_file)
    return df, rep_df, users_df


def render_data_tab(app_user_df, app_user_rep_df, tab_prefix="user"):
    st.header("Event Data")

    user_events = app_user_df["event_name"].sort_values().unique().tolist()
    selected_event = st.selectbox("Select Event", ["All Events"] + user_events, key=f"{tab_prefix}_event_select")

    if selected_event == "All Events":
        view_df = app_user_df
    else:
        view_df = app_user_df[app_user_df["event_name"] == selected_event]

    view_df = view_df.sort_values(["event_date", "event_time_only"])

    st.subheader("Events")

    display_cols = ["event_date", "event_day", "event_time_only", "event_name", "category"]
    st.dataframe(view_df[display_cols], width="stretch", hide_index=True)

    st.divider()

    st.subheader("Repetition Summary")

    summary_view = app_user_rep_df.copy()
    if selected_event != "All Events":
        summary_view = summary_view[summary_view["event_name"] == selected_event]

    st.dataframe(summary_view, width="stretch", hide_index=True)


def render_analysis_tab(app_user_df, app_user_rep_df, selected_user, journey_data, tab_prefix="user", is_business=False):
    """Render the Analysis tab — journey, AI interpretation, AI insights."""
    st.header(f"Journey Analysis")

    analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs([
        "User Journey" if not is_business else "Event Flow",
        "AI Journey Interpretation" if not is_business else "AI Event Interpretation",
        "AI Insights"
    ])

    # Choose the right prompt functions
    interp_fn = business_interpret_journey_safe if is_business else interpret_journey_safe
    insights_stream_fn = business_generate_insights_stream if is_business else generate_insights_stream

    with analysis_tab1:
        st.subheader("Event Flow" if is_business else "User Journey")

        if journey_data["total_events"] == 0:
            st.info("No events found.")
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
                st.dataframe(breakdown_df, width="stretch", hide_index=True)

    with analysis_tab2:
        st.subheader("AI Event Interpretation" if is_business else "AI Journey Interpretation")

        if st.button("Generate AI Interpretation", key=f"btn_ai_journey_{tab_prefix}"):
            with st.spinner("Analyzing events..."):
                payload = build_ai_payload(app_user_df, app_user_rep_df, selected_user)
                result = interp_fn(payload)

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

        if st.button("Generate AI Insights", key=f"btn_ai_insights_{tab_prefix}"):
            payload = build_ai_payload(app_user_df, app_user_rep_df, selected_user)
            st.write_stream(insights_stream_fn(payload))



top_tab_user, top_tab_business = st.tabs(["User", "Operator"])

with top_tab_user:
    df, rep_df, users_df = load_pipeline_data(USER_BASE_DIR)

    total_users = users_df["user_uuid"].nunique()
    total_events = len(df)

    g1, g2 = st.columns(2)
    g1.metric("Total Unique Users", total_users)
    g2.metric("Total Cleaned Events", total_events)

    st.divider()
    st.info("💡 **Analysis Scope**: All dashboards below use the full **ground truth** dataset (469,268 events, 3,961 users). The 'Global AI Report' tab uses an optimized **12% sample** (56,276 events) for high-speed AI reasoning.")
    st.divider()

    user_ids = users_df["user_uuid"].sort_values().tolist()
    selected_user = st.selectbox("Select User ID", user_ids, key="user_selector")

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

    main_tab1, main_tab2, main_tab3, main_tab4, main_tab5 = st.tabs([
        "Data", 
        "Analysis", 
        "Session Analysis", 
        "Pattern Discovery",
        "Global AI Report"
    ])

    with main_tab1:
        render_data_tab(app_user_df, app_user_rep_df, tab_prefix="user")

    with main_tab2:
        render_analysis_tab(app_user_df, app_user_rep_df, selected_user, journey_data, tab_prefix="user", is_business=False)

    with main_tab3:
        app3_session_analysis.render_session_analysis(
            events_csv=os.path.join(USER_BASE_DIR, "cleaned_events.csv"),
            key_suffix='user',
            selected_user=selected_user
        )

    with main_tab4:
        app4_pattern_discovery.render_pattern_discovery(
            key_suffix='user',
            selected_user=selected_user
        )

    with main_tab5:
        st.header("Global AI Report")
        
        report_path = "lang-graph-experiment/outputs/analytics_report.html"
        if os.path.exists(report_path):
            st.warning("⚠️ **Analysis Scale Note**: This Global AI Report is based on a **sampled subset** of 56,276 events (~12% of total traffic) for performance and cost efficiency. Other tabs show the full ground truth (469,268 events).")
            
            with open(report_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            import streamlit.components.v1 as components
            components.html(html_content, height=800, scrolling=True)
            
            st.download_button(
                label="Download Full HTML Report",
                data=html_content,
                file_name="commuter_analytics_report.html",
                mime="text/html",
                key="dl_user_report"
            )
        else:
            st.warning("LangGraph report not found. Please run the analytics pipeline first.")
            st.code("python lang-graph-experiment/run_analytics.py --type commuter")

    st.divider()
    st.caption("All AI analysis is strictly per-user and filtered to application events only.")

with top_tab_business:
    biz_df, biz_rep_df, biz_users_df = load_pipeline_data(BUSINESS_BASE_DIR)
    biz_app_df = biz_df[biz_df["category"].str.lower() == "application"]
    biz_app_rep_df = biz_rep_df[
        biz_rep_df["category"].str.lower() == "application"] if "category" in biz_rep_df.columns else biz_rep_df

    total_biz_ids = biz_users_df["user_uuid"].nunique()
    total_biz_events = len(biz_df)

    g1, g2 = st.columns(2)
    g1.metric("Total Unique Operators", total_biz_ids)
    g2.metric("Total Cleaned Events", total_biz_events)

    st.divider()
    st.info("💡 **Operation Scope**: Dashboards below use the full **ground truth** dataset (816,694 events, 507 operators). The 'Global AI Report' tab uses a **1.8% sample** (14,952 events) to process complex business logic efficiently.")
    st.divider()

    user_ids = biz_users_df["user_uuid"].sort_values().tolist()
    selected_user = st.selectbox("Select Operator ID", ["All Operators"] + user_ids, key="biz_user_selector")

    if selected_user == "All Operators":
        view_biz_app_df = biz_app_df
        view_biz_app_rep_df = biz_app_rep_df
    else:
        view_biz_app_df = biz_app_df[biz_app_df["user_uuid"] == selected_user]
        view_biz_app_rep_df = biz_app_rep_df[biz_app_rep_df["user_uuid"] == selected_user]

    biz_journey_data = build_user_journey(view_biz_app_df)

    b1, b2, b3 = st.columns(3)
    events_label = "Application Events" if selected_user == "All Operators" else f"Events for {selected_user}"
    b1.metric(events_label, len(view_biz_app_df))
    b2.metric("Unique Event Types", view_biz_app_df["event_name"].nunique())
    
    if selected_user == "All Operators":
        b3.metric("Total Operators", f"{biz_users_df['user_uuid'].nunique()}")
        
        st.subheader("👥 Operator Activity Summary")
        # Create summary dataframe
        biz_summary = biz_app_df.groupby("user_uuid").agg(
            total_activities=("event_name", "count"),
            unique_events=("event_name", "nunique"),
            active_days=("event_date", "nunique"),
            last_activity=("event_time", "max")
        ).reset_index().sort_values("total_activities", ascending=False).head(50)
        st.dataframe(biz_summary, width="stretch", hide_index=True)
    else:
        b3.metric(f"Activity Span ({selected_user})", f"{biz_journey_data['metadata']['date_range']['span_days']} Days" if biz_journey_data["total_events"] > 0 else "0 Days")

    st.divider()

    # Event distribution chart
    st.subheader("📊 Event Distribution")
    event_counts = view_biz_app_df["event_name"].value_counts().head(20)
    fig = px.bar(
        x=list(event_counts.index),
        y=list(event_counts.values),
        labels={"x": "Event Name", "y": "Count"},
        title=f"Top 20 Events for {selected_user}",
        color=list(event_counts.values),
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=450, showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch")

    st.divider()

    biz_tab_labels = ["Data", "Analysis", "Session Analysis", "Pattern Discovery", "Operational Analytics", "Global AI Report"]
    biz_tabs = st.tabs(biz_tab_labels)
    
    with biz_tabs[0]:
        render_data_tab(view_biz_app_df, view_biz_app_rep_df, tab_prefix="biz")
    
    with biz_tabs[1]:
        if selected_user == "All Operators":
            st.info("Select a specific Operator ID to view detailed journey analysis and AI insights.")
            # Still show aggregate distribution if user wants
            event_counts = view_biz_app_df["event_name"].value_counts().head(20)
            plot_df = pd.DataFrame({
                "Event": list(event_counts.index),
                "Count": list(event_counts.values)
            })
            fig = px.bar(
                plot_df,
                x="Event", 
                y="Count", 
                title="Top 20 Events (Aggregate)",
                color="Count",
                color_continuous_scale="Blues"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            render_analysis_tab(view_biz_app_df, view_biz_app_rep_df, selected_user, biz_journey_data, tab_prefix="biz", is_business=True)

    with biz_tabs[2]:
        app3_session_analysis.render_session_analysis(
            profile_json='business_data_profile_report.json', 
            events_csv=os.path.join(BUSINESS_BASE_DIR, "cleaned_events.csv"),
            key_suffix='biz',
            selected_user=selected_user
        )
            
    with biz_tabs[3]:
        app4_pattern_discovery.render_pattern_discovery(
            pattern_json='business_pattern_discovery_report.json',
            key_suffix='biz',
            selected_user=selected_user
        )

    with biz_tabs[4]:
        st.header("📊 Operations Analytics")
        app3_business_analysis.render_business_session_analysis(
            csv_path=os.path.join(BUSINESS_BASE_DIR, "cleaned_events.csv"),
            selected_user=selected_user,
            key_suffix='biz'
        )

    with biz_tabs[5]:
        st.header("Global AI Report")
        
        report_path = "lang-graph-experiment/outputs/business_report.html"
        if os.path.exists(report_path):
            st.warning("⚠️ **Analysis Scale Note**: The Global AI Report is based on a **sampled subset** of 14,952 events (~1.8% of total traffic) for performance and cost efficiency. The dashboards above show the full ground truth (816,694 events).")
            
            with open(report_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            import streamlit.components.v1 as components
            components.html(html_content, height=800, scrolling=True)
            
            st.download_button(
                label="Download Full HTML Report",
                data=html_content,
                file_name="business_analytics_report.html",
                mime="text/html",
                key="dl_biz_report"
            )
        else:
            st.warning("LangGraph report not found. Please run the analytics pipeline first.")
            st.code("python lang-graph-experiment/run_analytics.py --type business")

    st.divider()
    st.caption("Business analytics — aggregate event analysis for bus operators. AI analysis uses a sampled subset of recent events.")
