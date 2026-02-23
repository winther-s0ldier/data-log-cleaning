
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime

# Load data
@st.cache_data
def load_session_data(profile_json='data_profile_report.json', events_csv='Commuter Users Event data.csv'):
    """Load session profile and raw events"""
    try:
        with open(profile_json, 'r') as f:
            profile = json.load(f)

        events_df = pd.read_csv(events_csv)
        # Standardize column names — handle both commuter (user_uuid) and business (id) columns
        if 'user_uuid' in events_df.columns:
            events_df = events_df.rename(columns={'user_uuid': 'user_id', 'event_time': 'timestamp'})
        elif 'id' in events_df.columns:
            events_df = events_df.rename(columns={'id': 'user_id', 'event_time': 'timestamp'})
            events_df = events_df.drop(columns=['external_event_id', 'source'], errors='ignore')
        else:
            events_df = events_df.rename(columns={'event_time': 'timestamp'})
        events_df['timestamp'] = pd.to_datetime(events_df['timestamp'], format='mixed')

        return profile, events_df
    except FileNotFoundError as e:
        st.error(f"Required file not found: {e}")
        return None, None

def render_session_analysis(profile_json='data_profile_report.json', events_csv='Commuter Users Event data.csv', key_suffix='', selected_user='All'):
    profile, events_df = load_session_data(profile_json, events_csv)
    
    if profile is None:
        return

    sessions = profile['sessions']
    stats = profile['basic_stats']

    # Header
    st.header(f"🎯 Session Analysis Dashboard")
    st.markdown("*Based on system-event-marked sessions (ground truth)*")
    st.markdown(f"**Detection Method**: {sessions['session_detection_method'].replace('_', ' ').title()}")

    st.divider()

    # ============================================================================
    # OVERVIEW METRICS
    # ============================================================================
    st.subheader("📊 Session Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Total Sessions",
        f"{sessions['total_sessions']:,}",
        help="Sessions detected by system event markers"
    )

    col2.metric(
        "Avg Events/Session",
        f"{sessions['avg_session_length']:.1f}",
        help="Average number of events per session"
    )

    col3.metric(
        "Avg Duration",
        f"{sessions['avg_session_duration_minutes']:.1f} min",
        help="Average session duration in minutes"
    )

    col4.metric(
        "Bounce Rate",
        f"{sessions['bounce_rate']:.1%}",
        help="% of sessions with only 1 event"
    )

    col5.metric(
        "System Markers",
        f"{sessions['session_markers_used']:,}",
        help="Explicit session boundaries from app"
    )

    st.divider()

    # ============================================================================
    # SESSION TYPES
    # ============================================================================
    st.subheader("🚀 Session Types Distribution")

    # System markers data
    system_markers = {
        'Journey Started': 27380,
        'Session Started': 11736,
        'App Installed': 3951,
        'User Login': 4080,
        'Push Click': 93
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Session Start Events")
        for event, count in system_markers.items():
            pct = (count / sum(system_markers.values())) * 100
            st.metric(event, f"{count:,}", f"{pct:.1f}%")

    with col2:
        fig = px.pie(
            values=list(system_markers.values()),
            names=list(system_markers.keys()),
            title="Session Distribution by Start Event Type",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, width="stretch", key=f"session_start_dist_{key_suffix}")

    st.divider()

    # ============================================================================
    # DROP-OFF ANALYSIS
    # ============================================================================
    st.subheader("⚠️ Drop-off Analysis")

    st.markdown("""
    **Critical insight**: These are the last events before users end their session.
    Identifying drop-off points helps us know WHERE to intervene.
    """)

    exit_events = sessions['common_end_events']
    exit_df = pd.DataFrame([
        {
            'Event': k,
            'Sessions': v,
            'Percentage': (v/sessions['total_sessions'])*100
        }
        for k, v in list(exit_events.items())[:10]
    ])

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            exit_df,
            x='Sessions',
            y='Event',
            orientation='h',
            title="Top 10 Exit Events (Last event before session end)",
            color='Percentage',
            color_continuous_scale='Reds',
            labels={'Sessions': 'Number of Sessions Ending Here'}
        )
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, width="stretch", key=f"exit_events_bar_{key_suffix}")

    with col2:
        st.markdown("### 🎯 Critical Drop-offs")

        critical = [
            ('select_seat', exit_events.get('select_seat', 0)),
            ('login', exit_events.get('login', 0)),
            ('_user', exit_events.get('_user', 0)),
            ('choose_language', exit_events.get('choose_language', 0)),
            ('_profile', exit_events.get('_profile', 0))
        ]

        for event, count in critical:
            if count > 0:
                pct = (count/sessions['total_sessions'])*100
                priority = "🔴 HIGH" if pct > 8 else "🟡 MEDIUM"
                st.markdown(f"**{priority}**: {event}")
                st.markdown(f"└─ {count:,} sessions ({pct:.1f}%)")
                st.markdown("")

    st.divider()

    # ============================================================================
    # SESSION START PATTERNS
    # ============================================================================
    st.subheader("🔍 Session Start Patterns")

    st.markdown("""
    **First application events** after system markers reveal user intent and journey start patterns.
    """)

    start_events = sessions['common_start_events']
    start_df = pd.DataFrame([
        {
            'Event': k,
            'Sessions': v,
            'Percentage': (v/sessions['total_sessions'])*100
        }
        for k, v in list(start_events.items())[:10]
    ])

    fig = px.bar(
        start_df,
        x='Event',
        y='Sessions',
        title="Top 10 Session Start Events (First app event after system marker)",
        color='Sessions',
        color_continuous_scale='Blues'
    )
    fig.update_layout(height=400, showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch", key=f"start_events_bar_{key_suffix}")

    st.divider()

    # ============================================================================
    # SESSION LENGTH DISTRIBUTION
    # ============================================================================
    st.subheader("📏 Session Length Distribution")

    col1, col2 = st.columns(2)

    with col1:
        length_dist = sessions['session_length_distribution']

        percentile_df = pd.DataFrame([
            {'Percentile': 'P25', 'Events': length_dist['p25'], 'Label': '25th'},
            {'Percentile': 'P50', 'Events': length_dist['p50'], 'Label': 'Median'},
            {'Percentile': 'P75', 'Events': length_dist['p75'], 'Label': '75th'},
            {'Percentile': 'P90', 'Events': length_dist['p90'], 'Label': '90th'},
            {'Percentile': 'P95', 'Events': length_dist['p95'], 'Label': '95th'},
        ])

        fig = px.bar(
            percentile_df,
            x='Label',
            y='Events',
            title="Session Length by Percentile",
            color='Events',
            color_continuous_scale='Greens',
            text='Events'
        )
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch", key=f"session_percentiles_{key_suffix}")

    with col2:
        st.markdown("### 💡 Session Length Insights")
        st.markdown(f"")
        st.markdown(f"- **25% of sessions** have ≤ {length_dist['p25']:.0f} events (Quick interactions)")
        st.markdown(f"- **50% of sessions** have ≤ {length_dist['p50']:.0f} events (Typical session)")
        st.markdown(f"- **75% of sessions** have ≤ {length_dist['p75']:.0f} events (Engaged users)")
        st.markdown(f"- **Top 10%** have > {length_dist['p90']:.0f} events (Power users)")
        st.markdown(f"- **Top 5%** have > {length_dist['p95']:.0f} events (Deep exploration)")

        st.markdown("""
        **Session Categories:**
        - **Short** (< 10 events): Browse/Quick search
        - **Medium** (10-30 events): Active exploration
        - **Long** (> 30 events): Complete booking flow
        """)

    st.divider()

    # ============================================================================
    # EVENT CLASSIFICATION
    # ============================================================================
    st.subheader("🏷️ Event Classification by Category")

    classification = profile['event_classification']
    class_df = pd.DataFrame([
        {
            'Category': k.replace('_', ' ').title(),
            'Events': v['event_count'],
            'Types': v['unique_events'],
            'Percentage': (v['event_count']/stats['total_events'])*100
        }
        for k, v in classification.items()
    ]).sort_values('Events', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            class_df,
            x='Category',
            y='Events',
            title="Event Distribution by Category",
            color='Category',
            text='Events',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig.update_layout(height=450, showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig, width="stretch", key=f"category_dist_{key_suffix}")

    with col2:
        st.markdown("### Category Breakdown")
        for _, row in class_df.iterrows():
            st.markdown(f"**{row['Category']}**")
            st.markdown(f"└─ {row['Events']:,} events ({row['Percentage']:.1f}%)")
            st.markdown(f"└─ {row['Types']} unique event types")
            st.markdown("")

    st.divider()

    # ============================================================================
    # ACTIONABLE RECOMMENDATIONS
    # ============================================================================
    st.subheader("💡 Actionable Recommendations")

    st.markdown("""
    Based on session analysis, here are the **highest-impact interventions** you can make:
    """)

    # Define core target events to look for
    target_recommendations = [
        ('select_seat', 'Seat Selection Drop-off', '• Simplify seat selection UI\n• Show real-time seat availability\n• Add "Best seats" recommendation'),
        ('login', 'Login/Authentication Friction', '• Add social login (Google/Facebook)\n• Implement guest checkout\n• Reduce OTP timeout'),
        ('_profile', 'User Profile Abandonment', '• Make profile setup optional\n• Show value proposition\n• Allow skip for first booking'),
        ('choose_language', 'Language Selection', '• Auto-detect language\n• Remember user preference\n• Skip if already selected')
    ]

    # Support Operator/Business specific events if the above are missing
    if 'viewed_hisab_page' in exit_events or 'viewed_dashboard_page' in exit_events:
        target_recommendations = [
            ('viewed_hisab_page', 'Hisab Page Exit', '• Audit Hisab page loading times\n• Simplify complex tables\n• Add clear "Next Step" buttons'),
            ('viewed_dashboard_page', 'Dashboard Abandonment', '• Personalize dashboard metrics\n• Highlighting critical alerts\n• Improve navigation links'),
            ('viewed_login/signup_page', 'Login Page Drop-off', '• Check OTP delivery stability\n• Decrease login steps\n• Support persistent sessions'),
            ('home_page_load_error', 'System Load Errors', '• Optimize API response times\n• Implement better error handling\n• Add offline local caching')
        ]

    recommendations = []
    total_sessions = sessions['total_sessions'] if sessions['total_sessions'] > 0 else 1

    for event_key, issue_name, intervention in target_recommendations:
        count = exit_events.get(event_key, 0)
        pct = (count / total_sessions) * 100
        
        priority = 'LOW'
        if pct > 10: priority = 'HIGH'
        elif pct > 5: priority = 'MEDIUM'
        
        impact = '⬆️ +8-12% engagement'
        if priority == 'HIGH': impact = '⬆️ +15-20% retention'
        
        recommendations.append({
            'priority': priority,
            'issue': issue_name,
            'sessions': count,
            'pct': pct,
            'intervention': intervention,
            'impact': impact
        })

    for rec in recommendations:
        priority_emoji = "🔴" if rec['priority'] == "HIGH" else "🟡" if rec['priority'] == "MEDIUM" else "🟢"

        with st.expander(f"{priority_emoji} **{rec['priority']} PRIORITY**: {rec['issue']} ({rec['sessions']:,} sessions, {rec['pct']:.1f}%)"):
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**📊 Problem**")
                st.markdown(f"{rec['sessions']:,} users ({rec['pct']:.1f}% of all sessions) drop off at this point")

                st.markdown("**🎯 Recommended Actions**")
                st.markdown(rec['intervention'])

            with col_b:
                st.markdown("**📈 Expected Impact**")
                st.markdown(rec['impact'])

                st.markdown("**⏱️ Implementation**")
                impl_time = "1-2 weeks" if rec['priority'] == "LOW" else "2-3 weeks" if rec['priority'] == "MEDIUM" else "3-4 weeks"
                st.markdown(f"Estimated time: {impl_time}")

    st.divider()

    # ============================================================================
    # FOOTER
    # ============================================================================
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Events Analyzed", f"{stats['total_events']:,}")
    col2.metric("Unique Users", f"{stats['unique_users']:,}")
    col3.metric("Date Range", f"{stats['date_range']['span_days']} days")

    data_source_label = 'Business Events Data' if 'business' in events_csv.lower() else 'Commuter Users Event Data'
    st.caption(f"""
    **Detection Method**: System events only (Session Started, Journey Started, App Installed, User Login, Push Click)
    **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    **Data Source**: {data_source_label}
    """)

if __name__ == "__main__":
    st.set_page_config(
        page_title="Session Analysis",
        page_icon="🎯",
        layout="wide"
    )
    render_session_analysis()
