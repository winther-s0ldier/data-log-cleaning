"""
Business Analytics — Session Analysis Replacement

This module provides business-appropriate analytics for the operator event stream.
Instead of per-user sessions (which are impossible without user IDs), it provides:
1. Workflow breakdown (hisab, dashboard, login, etc.)
2. Hourly/daily usage heatmaps
3. Push notification funnel
4. Login/auth funnel
5. Feature adoption over time
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime


# ---- Workflow Definitions ----
WORKFLOWS = {
    "Hisab (Accounting)": [
        "viewed_hisab_page", "viewed_hisab_bus_detail", "viewed_hisab_trip_detail",
        "clicked_hisab_trip_detail_card", "clicked_hisab_bus_detail_card",
        "clicked_hisab_yestarday_btn", "clicked_hisab_coustom_date_btn",
        "clicked_hisab_today_btn", "clicked_hisab_bus_detail_yeaterday_btn",
        "clicked_hisab_download_btn", "clicked_hisab_bus_detail_today_btn",
        "clicked_hisab_bus_detail_download_btn",
    ],
    "Dashboard": [
        "viewed_dashboard_page", "dashboard_clicked_gps_vistar_se_dekhe_bus_card",
        "home_page_load_error", "dashboard_page_pay_btn",
    ],
    "Login / Auth": [
        "viewed_login_page", "viewed_login/signup_page", "viewed_login_otp_verify_page",
        "clicked_login_send_otp_btn", "clicked_login_verify_otp",
        "login_verify_otp_success", "login_verify_otp_failed",
        "User Login", "clicked_login_resend_otp", "clicked_login_btn",
    ],
    "Push Notifications": [
        "Push Sent", "Push Delivered", "Push Impression",
        "Push Dismiss", "Push Click", "Push Notification Failed",
    ],
    "Navigation": [
        "clicked_nav_drawer_menu", "clicked_nav_drawer_my_profile",
        "clicked_nav_drawer_cash_settlement", "clicked_nav_drawer_dsn_mapping",
        "clicked_nav_drawer_logout", "clicked_nav_drawer_offer_discount",
        "clicked_nav_drawer_online_payments_history", "clicked_nav_drawer_recharge",
        "clicked_nav_drawer_change_language", "clicked_nav_drawer_t&c",
        "clicked_nav_drawer_training_videos",
    ],
    "Cash Settlement": [
        "clicked_cash_settlement_settle_btn", "clicked_cash_settlement_non_settled_btn",
        "clicked_cash_settlement_trip_setlle_btn", "viewed_cash_settlement_screen",
        "clicked_cash_settlement_settled_btn", "clicked_cash_settlement_bus_card",
    ],
    "Pricing & Offers": [
        "viewed_offer_discount_page", "clicked_offer_discount_edit",
        "clicked_offer_discount_delete", "clicked_offer_discount_delete_btn",
        "clicked_offer_discount_delete_confirm", "clicked_offer_discount_delete_confirm_btn",
        "clicked_offer_discount_ladies_discount", "clicked_offer_discount_student_discount",
        "clicked_view_pricing_page_prices_download", "view_pricing_page_prices_download_success",
        "clicked_view_pricing_page_prices_upload", "clicked_view_pricing_page_seat_type_selection",
        "viewed_manage_route_and_pricing_page", "clicked_manage_route_and_pricing_view_pricing_btn",
        "viewed_view_pricing_page", "view_pricing_page_prices_upload_success",
        "clicked_manage_route_and_pricing_bus_card",
    ],
    "Route Management": [
        "clicked_view_route_page_submit_changes", "clicked_view_route_page_submit_changes_confirmed",
        "viewed_view_route_page_back_btn", "clicked_manage_route_and_pricing_view_route_btn",
        "viewed_view_route_page",
    ],
    "Settings & Ticketing": [
        "viewed_setting_ticketing_machine_page", "viewed_machine_name_change_page",
        "smart_ticketing_settings_failed",
    ],
    "Payments & Recharge": [
        "viewed_online_payment_history_page", "viewed_recharge_page",
        "viewed_card_wallet_history_page", "viewed_pending_payment_page",
    ],
}


# Build reverse lookup: event_name → workflow (fast O(1) mapping)
_EVENT_TO_WORKFLOW = {}
for _wf, _events in WORKFLOWS.items():
    for _ev in _events:
        _EVENT_TO_WORKFLOW[_ev] = _wf


@st.cache_data
def load_business_data(csv_path: str = "Business Events data.csv"):
    """Load and prepare business event data."""
    try:
        df = pd.read_csv(csv_path)
        df['event_time'] = pd.to_datetime(df['event_time'], format='mixed')
        df['date'] = df['event_time'].dt.date
        df['hour'] = df['event_time'].dt.hour
        df['day_of_week'] = df['event_time'].dt.day_name()
        # Vectorized workflow mapping — much faster than .apply()
        df['workflow'] = df['event_name'].map(_EVENT_TO_WORKFLOW).fillna("Other")
        return df
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        return None


def render_business_session_analysis(csv_path: str = "Business Events data.csv", selected_user: str = "All Operators", key_suffix=''):
    """Render business-specific analytics replacing session analysis."""
    df = load_business_data(csv_path)
    if df is None:
        return

    if selected_user != "All Operators":
        df = df[df['user_uuid'] == selected_user]

    app_df = df[df['category'] == 'application']
    sys_df = df[df['category'] == 'system']

    st.header(f"📊 Business Operations Analytics {'- ' + str(selected_user) if selected_user != 'All Operators' else ''}")
    st.markdown(f"*Aggregate behavior analysis for bus operator platform — context: {str(selected_user)}*")

    # ---- Top-level metrics ----
    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric(f"Total Events ({str(selected_user)})", f"{len(app_df):,}")
    with b2:
        st.metric(f"Event Types ({str(selected_user)})", f"{app_df['event_name'].nunique()}")
    with b3:
        # Safely calculate span
        span = 0
        if not app_df.empty:
            span = (app_df['event_time'].max() - app_df['event_time'].min()).days + 1
        st.metric(f"Span (Days) ({str(selected_user)})", f"{span}")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔧 Workflow Breakdown",
        "📈 Trends & Heatmap",
        "🔐 Login Funnel",
        "🚀 Feature Adoption",
    ])

    # ========================================================================
    # TAB 1: WORKFLOW BREAKDOWN
    # ========================================================================
    with tab1:
        st.header("🔧 Operational Workflow Breakdown")
        st.markdown("Events grouped by business function")

        workflow_counts = app_df['workflow'].value_counts()

        col1, col2 = st.columns([2, 1])

        with col1:
            # Donut chart
            fig = px.pie(
                names=workflow_counts.index,
                values=workflow_counts.values,
                title=f"Event Distribution by Workflow ({selected_user})",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=500)
            st.plotly_chart(fig, width="stretch")

        with col2:
            st.subheader("Workflow Volume")
            # Use same color palette as the pie chart (px.colors.qualitative.Set2)
            colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3']
            for i, (wf, count) in enumerate(workflow_counts.items()):
                pct = count / len(app_df) * 100
                color = colors[i % len(colors)]
                st.markdown(f"**{wf}**")
                # Fix: Calculate relative width correctly (relative to the max workflow count)
                # This ensures the top workflow fills the bar, and others are scaled proportional to it
                max_count = workflow_counts.values[0]
                progress_val = (count / max_count) * 100
                
                # Custom HTML progress bar with lighter background so the colors are visible
                st.markdown(f"""
                    <div style="background-color: rgba(51, 65, 85, 0.2); border-radius: 4px; height: 12px; width: 100%; margin: 4px 0;">
                        <div style="background-color: {color}; height: 100%; width: {progress_val}%; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);"></div>
                    </div>
                """, unsafe_allow_html=True)
                st.caption(f"{count:,} events ({pct:.1f}%)")

        st.divider()

        # Per-workflow top events
        st.subheader("Top Events per Workflow")
        selected_wf = st.selectbox(
            "Select Workflow",
            [wf for wf in workflow_counts.index if wf != "Other"],
            key=f"biz_wf_select_{key_suffix}"
        )

        wf_events = app_df[app_df['workflow'] == selected_wf]['event_name'].value_counts()
        wf_plot_df = pd.DataFrame({
            "Event": list(wf_events.index),
            "Count": list(wf_events.values)
        })
        fig = px.bar(
            wf_plot_df,
            x="Event",
            y="Count",
            labels={"index_col": "Event", "value_col": "Count"},
            title=f"Top Events: {selected_wf} ({str(selected_user)})",
            color="Count",
            color_continuous_scale="Teal",
        )
        fig.update_layout(height=400, xaxis_tickangle=-30, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, key=f"wf_events_bar_{key_suffix}")

    # ========================================================================
    # TAB 2: DAILY / HOURLY TRENDS
    # ========================================================================
    with tab2:
        st.header("📈 Usage Trends & Patterns")

        # Daily volume trend
        st.subheader("Daily Event Volume")
        daily_counts = df.groupby('date').size().reset_index(name='events')
        daily_app = app_df.groupby('date').size().reset_index(name='app_events')
        daily_merged = daily_counts.merge(daily_app, on='date', how='left').fillna(0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_merged['date'], y=daily_merged['events'],
            mode='lines+markers', name='All Events',
            line=dict(color='#4B9EFF', width=2), marker=dict(size=3)
        ))
        fig.add_trace(go.Scatter(
            x=daily_merged['date'], y=daily_merged['app_events'],
            mode='lines', name='Application Events',
            line=dict(color='#00CC66', width=2)
        ))
        fig.update_layout(height=400, xaxis_title="Date", yaxis_title="Events",
                          hovermode='x unified')
        st.plotly_chart(fig, width="stretch", key=f"daily_vol_scatter_{key_suffix}")

        col1, col2 = st.columns(2)

        with col1:
            # Hourly distribution
            st.subheader("Hourly Activity Pattern")
            hourly_counts = df.groupby('hour').size().reset_index(name='events')
            fig = px.bar(
                x=list(hourly_counts['hour']),
                y=list(hourly_counts['events']),
                title=f"Hourly Activity Distribution ({selected_user})",
                labels={"x": "Hour of Day", "y": "Number of Events"},
                color=list(hourly_counts['events']),
                color_continuous_scale="Viridis",
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, width="stretch")

        with col2:
            # Day-of-week distribution
            st.subheader("Day-of-Week Pattern")
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow = app_df.groupby('day_of_week').size().reindex(day_order).reset_index()
            dow.columns = ['day', 'events']
            fig = px.bar(
                dow, x='day', y='events',
                title=f"Application Events by Day of Week ({selected_user})",
                color='events', color_continuous_scale='Viridis',
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, width="stretch")

        if app_df.empty:
            st.info(f"No activity data available for {str(selected_user)}.")
        else:
            # Hour x Day-of-week heatmap
            st.subheader("Activity Heatmap (Hour × Day)")
            
            # Ensure all days and hours are present to avoid px.imshow dimension mismatch
            heatmap_data = app_df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
            heatmap_data = heatmap_data.reindex(index=day_order, columns=range(24), fill_value=0)

            fig = px.imshow(
                heatmap_data.values,
                x=[f"{h:02d}:00" for h in range(24)],
                y=list(heatmap_data.index),
                color_continuous_scale='YlOrRd',
                labels=dict(x="Hour", y="Day", color="Events"),
                title=f"Application Events: Hour × Day of Week ({str(selected_user)})",
                aspect="auto"
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, width="stretch", key=f"activity_heatmap_{key_suffix}")

    # ========================================================================
    # TAB 3: LOGIN / AUTH FUNNEL
    # ========================================================================
    with tab3:
        st.header("🔐 Login / Authentication Funnel")
        st.markdown("*Operator login pipeline — from page view to successful authentication*")

        login_events = {
            "View Login Page": df[df['event_name'].isin(['viewed_login_page', 'viewed_login/signup_page'])].shape[0],
            "Send OTP": df[df['event_name'] == 'clicked_login_send_otp_btn'].shape[0],
            "View OTP Page": df[df['event_name'] == 'viewed_login_otp_verify_page'].shape[0],
            "Verify OTP": df[df['event_name'] == 'clicked_login_verify_otp'].shape[0],
            "OTP Success": df[df['event_name'] == 'login_verify_otp_success'].shape[0],
            "User Login": df[df['event_name'] == 'User Login'].shape[0],
        }
        otp_failed = df[df['event_name'] == 'login_verify_otp_failed'].shape[0]

        # Metrics
        cols = st.columns(6)
        for i, (label, val) in enumerate(login_events.items()):
            cols[i].metric(label, f"{val:,}")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Funnel
            fig = go.Figure(go.Funnel(
                y=list(login_events.keys()),
                x=list(login_events.values()),
                textinfo="value+percent initial+percent previous",
                marker=dict(color=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']),
            ))
            fig.update_layout(title=f"Login Funnel ({selected_user})", height=450)
            st.plotly_chart(fig, width="stretch", key=f"login_funnel_chart_{key_suffix}")

        with col2:
            st.subheader("📊 Conversion Rates")
            if login_events["View Login Page"] > 0:
                st.metric(
                    "OTP Send Rate",
                    f"{login_events['Send OTP'] / login_events['View Login Page']:.1%}"
                )

            if login_events["Verify OTP"] > 0:
                success_rate = login_events["OTP Success"] / login_events["Verify OTP"]
                st.metric("OTP Success Rate", f"{success_rate:.1%}")

            if login_events["View Login Page"] > 0:
                overall = login_events["User Login"] / login_events["View Login Page"]
                st.metric("Overall Login Rate", f"{overall:.1%}")

            st.divider()
            st.metric("OTP Failures", f"{otp_failed:,}", delta=None)
            if login_events["Verify OTP"] > 0:
                st.caption(f"Failure rate: {otp_failed / login_events['Verify OTP']:.1%}")

    # ========================================================================
    # TAB 4: FEATURE ADOPTION OVER TIME
    # ========================================================================
    with tab4:
        st.header("🚀 Feature Adoption Trends")
        st.markdown("*How are different features being used over time?*")

        # Daily workflow trends
        workflow_daily = app_df.groupby(['date', 'workflow']).size().reset_index(name='events')

        # Exclude "Other" for cleaner chart
        top_workflows = [w for w in app_df['workflow'].value_counts().head(6).index if w != "Other"]
        wf_filtered = workflow_daily[workflow_daily['workflow'].isin(top_workflows)]

        fig = px.line(
            wf_filtered, x='date', y='events', color='workflow',
            title=f"Daily Event Volume by Workflow ({selected_user})",
            labels={"date": "Date", "events": "Events", "workflow": "Workflow"},
        )
        fig.update_layout(height=450, hovermode='x unified')
        st.plotly_chart(fig, width="stretch", key=f"wf_daily_line_{key_suffix}")

        st.divider()

        # Week-over-week comparison
        st.subheader("Weekly Workflow Comparison")
        app_df_copy = app_df.copy()
        
        # Combine Year and Week to handle data spanning multiple years or discrete segments
        app_df_copy['year'] = app_df_copy['event_time'].dt.isocalendar().year
        app_df_copy['week_num'] = app_df_copy['event_time'].dt.isocalendar().week
        app_df_copy['week'] = "W" + app_df_copy['week_num'].astype(str) + " (" + app_df_copy['year'].astype(str) + ")"
        
        # Group by the new formatted week string
        # We sort by year and week_num first to ensure the bars appear in chronological order
        weekly_wf = app_df_copy.groupby(['year', 'week_num', 'week', 'workflow']).size().reset_index(name='events')
        weekly_wf = weekly_wf[weekly_wf['workflow'].isin(top_workflows)]
        weekly_wf = weekly_wf.sort_values(['year', 'week_num'])

        fig = px.bar(
            weekly_wf, x='week', y='events', color='workflow',
            title=f"Weekly Workflow Volume ({selected_user})",
            barmode='stack',
            category_orders={"week": weekly_wf['week'].unique().tolist()}
        )
        fig.update_layout(height=450, xaxis_title="Week (Year)", xaxis={'type': 'category'})
        st.plotly_chart(fig, width="stretch", key=f"weekly_wf_bar_{key_suffix}")

    # ---- Footer ----
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Date Range", f"{df['date'].min()} → {df['date'].max()}")
    c2.metric("Workflows Tracked", len([w for w in WORKFLOWS if w != "Other"]))
    c3.metric("Peak Hour", f"{app_df.groupby('hour').size().idxmax():02d}:00")

    st.caption(f"""
    **Data Source**: {csv_path} | **Analysis Type**: Aggregate event stream (no per-user grouping)
    **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)


if __name__ == "__main__":
    st.set_page_config(page_title="Business Operations Analytics", page_icon="📊", layout="wide")
    render_business_session_analysis()
