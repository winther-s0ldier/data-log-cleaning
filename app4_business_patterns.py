"""
Business Analytics — Pattern Discovery Replacement

This module provides event-level pattern analysis for the operator event stream.
Instead of per-user clustering (impossible without user IDs), it provides:
1. Event transition flows (what follows what)
2. Friction detection (repetition in close time proximity)
3. Daily trend analysis (growth/decline of key event types)
4. Event co-occurrence patterns
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np


@st.cache_data
def load_business_events(csv_path: str = "Business Events data.csv"):
    """Load business event data."""
    try:
        df = pd.read_csv(csv_path)
        df['event_time'] = pd.to_datetime(df['event_time'], format='mixed')
        df['date'] = df['event_time'].dt.date
        return df
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        return None


@st.cache_data
def compute_transitions(df: pd.DataFrame, top_n: int = 20):
    """Compute global event transition matrix from time-ordered events."""
    app_df = df[df['category'] == 'application'].sort_values('event_time').copy()

    # Vectorized: use shift to get next event and time diff
    app_df['next_event'] = app_df['event_name'].shift(-1)
    app_df['time_to_next'] = app_df['event_time'].shift(-1).sub(app_df['event_time']).dt.total_seconds()

    # Filter to transitions within 60 seconds
    valid = app_df[(app_df['time_to_next'] >= 0) & (app_df['time_to_next'] <= 60)].copy()

    # Group and count
    trans_counts = valid.groupby(['event_name', 'next_event']).size().reset_index(name='count')

    # Build dict structure
    transitions = {}
    for _, row in trans_counts.iterrows():
        src = row['event_name']
        if src not in transitions:
            transitions[src] = {}
        transitions[src][row['next_event']] = int(row['count'])

    return transitions


@st.cache_data
def compute_friction(df: pd.DataFrame):
    """Detect friction events — events that repeat in close time proximity."""
    app_df = df[df['category'] == 'application'].sort_values('event_time').copy()

    # Consecutive same events within short time intervals
    app_df['prev_event'] = app_df['event_name'].shift(1)
    app_df['time_gap'] = app_df['event_time'].diff().dt.total_seconds()

    # A repeat = same event name as previous within 30 seconds
    repeats = app_df[
        (app_df['event_name'] == app_df['prev_event']) &
        (app_df['time_gap'] <= 30) &
        (app_df['time_gap'] >= 0)
    ]

    repeat_counts = repeats['event_name'].value_counts()
    total_counts = app_df['event_name'].value_counts()

    friction = []
    for event in repeat_counts.index:
        friction.append({
            'event': event,
            'repeats': repeat_counts[event],
            'total': total_counts.get(event, 0),
            'repeat_rate': repeat_counts[event] / total_counts.get(event, 1),
            'friction_score': repeat_counts[event] * (repeat_counts[event] / total_counts.get(event, 1)),
        })

    return pd.DataFrame(friction).sort_values('friction_score', ascending=False)


@st.cache_data
def compute_daily_trends(df: pd.DataFrame, top_n: int = 10):
    """Compute daily trends for top events — identify growth/decline."""
    app_df = df[df['category'] == 'application']
    top_events = app_df['event_name'].value_counts().head(top_n).index.tolist()

    daily = app_df[app_df['event_name'].isin(top_events)].groupby(
        ['date', 'event_name']
    ).size().reset_index(name='count')

    return daily, top_events


def render_business_pattern_discovery(csv_path: str = "Business Events data.csv"):
    """Render business-specific pattern analysis."""
    df = load_business_events(csv_path)
    if df is None:
        return

    app_df = df[df['category'] == 'application']

    st.title("🔍 Business Event Pattern Analysis")
    st.markdown("*Event-level patterns, transitions, and friction analysis for aggregate operator data*")

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Application Events", f"{len(app_df):,}")
    c2.metric("Unique Event Types", f"{app_df['event_name'].nunique()}")
    c3.metric("Days Analyzed", f"{df['date'].nunique()}")
    c4.metric("Avg Events/Day", f"{len(app_df) // max(df['date'].nunique(), 1):,}")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔀 Event Transitions",
        "🔥 Friction Detection",
        "📈 Daily Trends",
        "🔗 Co-occurrence",
    ])

    # ========================================================================
    # TAB 1: EVENT TRANSITIONS
    # ========================================================================
    with tab1:
        st.header("🔀 Event Transition Analysis")
        st.markdown("*What events typically follow other events? (within 60-second window)*")

        transitions = compute_transitions(df)

        # Let user pick a source event
        top_events = app_df['event_name'].value_counts().head(20).index.tolist()
        source_event = st.selectbox("Select starting event:", top_events, key="trans_source")

        if source_event in transitions:
            next_events = transitions[source_event]
            sorted_next = sorted(next_events.items(), key=lambda x: x[1], reverse=True)[:15]

            col1, col2 = st.columns([2, 1])

            with col1:
                next_df = pd.DataFrame(sorted_next, columns=['Next Event', 'Count'])
                total = next_df['Count'].sum()
                next_df['Percentage'] = (next_df['Count'] / total * 100).round(1)

                fig = px.bar(
                    next_df, x='Count', y='Next Event', orientation='h',
                    title=f"What follows '{source_event}'?",
                    color='Percentage', color_continuous_scale='Blues',
                    text='Percentage',
                )
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.subheader("Transition Probabilities")
                for event, count in sorted_next[:10]:
                    pct = count / total * 100
                    st.markdown(f"**{event}**")
                    st.progress(min(pct / 100, 1.0))
                    st.caption(f"{count:,} ({pct:.1f}%)")
        else:
            st.info("No transitions found for this event.")

        st.divider()

        # Global transition heatmap (top 12 events)
        st.subheader("Transition Heatmap (Top 12 Events)")
        top12 = app_df['event_name'].value_counts().head(12).index.tolist()

        matrix = pd.DataFrame(0, index=top12, columns=top12)
        for src in top12:
            if src in transitions:
                for dst in top12:
                    matrix.loc[src, dst] = transitions[src].get(dst, 0)

        # Normalize rows
        row_sums = matrix.sum(axis=1).replace(0, 1)
        matrix_pct = matrix.div(row_sums, axis=0) * 100

        fig = px.imshow(
            matrix_pct.values,
            x=[e[:30] for e in top12],
            y=[e[:30] for e in top12],
            color_continuous_scale='Blues',
            labels=dict(x="To Event", y="From Event", color="Probability (%)"),
            title="Transition Probability Matrix (Row-Normalized %)",
            aspect="auto"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")

    # ========================================================================
    # TAB 2: FRICTION DETECTION
    # ========================================================================
    with tab2:
        st.header("🔥 Friction Detection")
        st.markdown("*Events that repeat in close succession (within 30 seconds) indicate user friction or errors*")

        friction_df = compute_friction(df)

        if friction_df.empty:
            st.info("No friction patterns detected.")
        else:
            col1, col2 = st.columns([2, 1])

            with col1:
                # Friction score chart
                top_friction = friction_df.head(15)
                fig = px.bar(
                    top_friction, x='friction_score', y='event', orientation='h',
                    title="Top Friction Events (Higher Score = More Problematic)",
                    color='repeat_rate',
                    color_continuous_scale='Reds',
                    hover_data=['repeats', 'total', 'repeat_rate'],
                    labels={'friction_score': 'Friction Score', 'repeat_rate': 'Repeat Rate'},
                )
                fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.subheader("🎯 Priority Fixes")
                for _, row in top_friction.head(8).iterrows():
                    rr = row['repeat_rate']
                    if rr > 0.5:
                        st.error(f"🔴 **{row['event'][:35]}**")
                    elif rr > 0.3:
                        st.warning(f"🟡 **{row['event'][:35]}**")
                    else:
                        st.info(f"🟢 **{row['event'][:35]}**")
                    st.caption(f"{row['repeats']:,.0f} repeats / {row['total']:,.0f} total ({rr:.1%})")
                    st.markdown("---")

            # Detailed friction table
            st.subheader("Full Friction Report")
            display_df = friction_df[['event', 'repeats', 'total', 'repeat_rate', 'friction_score']].copy()
            display_df['repeat_rate'] = display_df['repeat_rate'].apply(lambda x: f"{x:.1%}")
            display_df['friction_score'] = display_df['friction_score'].apply(lambda x: f"{x:,.0f}")
            display_df.columns = ['Event', 'Repeats', 'Total Occurrences', 'Repeat Rate', 'Friction Score']
            st.dataframe(display_df, width="stretch", height=400)

    # ========================================================================
    # TAB 3: DAILY TRENDS
    # ========================================================================
    with tab3:
        st.header("📈 Event Trend Analysis")
        st.markdown("*How are key events trending over time? Identify growth or decline.*")

        n_events = st.slider("Number of top events to show", 5, 20, 10, key="trend_n")
        daily_trends, top_events = compute_daily_trends(df, top_n=n_events)

        fig = px.line(
            daily_trends, x='date', y='count', color='event_name',
            title=f"Daily Volume — Top {n_events} Events",
            labels={"date": "Date", "count": "Events", "event_name": "Event"},
        )
        fig.update_layout(height=500, hovermode='x unified')
        st.plotly_chart(fig, width="stretch")

        st.divider()

        # Growth analysis — compare periods
        st.subheader("Growth Analysis")
        period_option = st.selectbox(
            "Compare period",
            ["First 7 days vs Last 7 days", "First 14 days vs Last 14 days", "First month vs Last month"],
            key="growth_period"
        )

        period_map = {
            "First 7 days vs Last 7 days": 7,
            "First 14 days vs Last 14 days": 14,
            "First month vs Last month": 30,
        }
        n_days = period_map[period_option]

        dates = sorted(df['date'].unique())
        if len(dates) > n_days * 2:
            first_period = dates[:n_days]
            last_period = dates[-n_days:]

            first_counts = app_df[app_df['date'].isin(first_period)]['event_name'].value_counts()
            last_counts = app_df[app_df['date'].isin(last_period)]['event_name'].value_counts()

            growth_data = []
            for event in top_events:
                f = first_counts.get(event, 0)
                l = last_counts.get(event, 0)
                if f > 0:
                    change = (l - f) / f * 100
                else:
                    change = 100 if l > 0 else 0
                growth_data.append({
                    'Event': event,
                    f'First {n_days}d': f,
                    f'Last {n_days}d': l,
                    'Change (%)': round(change, 1),
                })

            growth_df = pd.DataFrame(growth_data)

            fig = px.bar(
                growth_df, x='Change (%)', y='Event', orientation='h',
                title=f"Event Growth: {period_option}",
                color='Change (%)',
                color_continuous_scale='RdYlGn',
                color_continuous_midpoint=0,
            )
            fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, width="stretch")

            st.dataframe(growth_df, width="stretch")
        else:
            st.warning(f"Not enough data for {period_option} comparison (need at least {n_days * 2} days, have {len(dates)})")

    # ========================================================================
    # TAB 4: CO-OCCURRENCE
    # ========================================================================
    with tab4:
        st.header("🔗 Event Co-occurrence Analysis")
        st.markdown("*Which events frequently appear together within short time windows?*")

        st.markdown("""
        Events that co-occur within a **5-minute window** likely belong to the same 
        operator session. This reveals which features/workflows are used together.
        """)

        # Filter to top 15 events FIRST, then compute — much faster
        top15 = app_df['event_name'].value_counts().head(15).index.tolist()
        app_top = app_df[app_df['event_name'].isin(top15)].copy()
        app_top['time_bucket'] = app_top['event_time'].dt.floor('5min')

        # Vectorized co-occurrence via crosstab + matrix multiply
        # Create presence matrix: (bucket × event) with 1/0
        presence = app_top.groupby(['time_bucket', 'event_name']).size().unstack(fill_value=0)
        presence = (presence > 0).astype(int)

        # Co-occurrence = presence^T × presence (gives count of shared buckets)
        cooccurrence = presence.T.dot(presence)

        # Zero out diagonal (self-co-occurrence not meaningful)
        for e in cooccurrence.index:
            cooccurrence.loc[e, e] = 0

        # Normalize by max for display
        if cooccurrence.values.max() > 0:
            cooc_norm = cooccurrence / cooccurrence.values.max() * 100

            fig = px.imshow(
                cooc_norm.values,
                x=[e[:25] for e in cooc_norm.columns],
                y=[e[:25] for e in cooc_norm.index],
                color_continuous_scale='YlOrRd',
                labels=dict(color="Co-occurrence (%)"),
                title="Event Co-occurrence Matrix (5-min windows)",
                aspect="auto"
            )
            fig.update_layout(height=550)
            st.plotly_chart(fig, width="stretch")

            # Top co-occurring pairs
            st.subheader("Top Co-occurring Event Pairs")
            pairs = []
            events_list = cooccurrence.columns.tolist()
            for i, e1 in enumerate(events_list):
                for j, e2 in enumerate(events_list):
                    if i < j and cooccurrence.loc[e1, e2] > 0:
                        pairs.append({
                            'Event A': e1,
                            'Event B': e2,
                            'Co-occurrences': int(cooccurrence.loc[e1, e2]),
                        })

            pairs_df = pd.DataFrame(pairs).sort_values('Co-occurrences', ascending=False).head(20)
            st.dataframe(pairs_df, width="stretch")
        else:
            st.info("Not enough data to compute co-occurrence.")

    # ---- Footer ----
    st.divider()
    st.caption(f"""
    **Data Source**: {csv_path} | **Analysis Type**: Event-level pattern mining
    **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)


if __name__ == "__main__":
    st.set_page_config(page_title="Business Pattern Analysis", page_icon="🔍", layout="wide")
    render_business_pattern_discovery()
