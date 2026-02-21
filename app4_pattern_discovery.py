
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
import numpy as np

# Load pattern discovery data
@st.cache_data
def load_pattern_data(pattern_json='pattern_discovery_report.json'):
    """Load pattern discovery report"""
    try:
        with open(pattern_json, 'r') as f:
            patterns = json.load(f)
        return patterns
    except FileNotFoundError:
        st.error(f"Pattern discovery report not found: {pattern_json}")
        st.stop()

def render_pattern_discovery(pattern_json='pattern_discovery_report.json'):
    patterns = load_pattern_data(pattern_json)

    # Header
    st.title("🔍 Pattern Discovery Dashboard")
    st.markdown("*Behavioral patterns discovered through machine learning algorithms*")

    metadata = patterns.get('metadata', {})
    st.markdown(f"""
    **Analysis Scope**: {metadata['total_events']:,} events | {metadata['unique_users']:,} users | {metadata['total_sessions']:,} sessions
    """)

    st.divider()

    # ============================================================================
    # TAB 1: SEQUENTIAL PATTERNS
    # ============================================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 Sequential Patterns",
        "👥 User Segments",
        "🔥 Friction Analysis",
        "📉 Survival Analysis",
        "🎯 Intervention Triggers"
    ])

    with tab1:
        st.header("🔄 Sequential Patterns")
        st.markdown("**Most frequent event sequences** - reveals common user journeys and stuck loops")

        seq_patterns = patterns.get('sequential_patterns', {})
        frequent = seq_patterns.get('frequent_patterns', {})
        repetitions = seq_patterns.get('repetition_patterns', {})

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Top 20 Frequent Sequences")

            # Convert to dataframe
            seq_df = pd.DataFrame([
                {'Pattern': k, 'Frequency': v, 'Pattern_Length': len(k.split(' → '))}
                for k, v in list(frequent.items())[:20]
            ])

            # Create bar chart
            fig = px.bar(
                seq_df,
                x='Frequency',
                y='Pattern',
                orientation='h',
                title="Most Common Event Sequences",
                color='Pattern_Length',
                color_continuous_scale='Blues',
                labels={'Frequency': 'Number of Occurrences', 'Pattern_Length': 'Sequence Length'}
            )
            fig.update_layout(height=600, showlegend=True, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, width="stretch")

            # Insights
            with st.expander("📊 Pattern Insights"):
                # Support both new LLM insights and legacy pattern insights
                insights = seq_patterns.get('llm_insights', seq_patterns.get('pattern_insights', {}))
                
                if isinstance(insights, str):
                    # LLM output is a single string
                    st.markdown(insights)
                elif isinstance(insights, dict):
                    # Legacy or structured format
                    for pattern, insight in list(insights.items())[:10]:
                        st.markdown(f"**{pattern}**")
                        st.markdown(f"└─ {insight}")
                        st.markdown("")
                else:
                    st.info("No insights available for this section.")

        with col2:
            st.subheader("Repetition Patterns")
            st.markdown("*Events users repeat → friction signals*")

            # Top repetitions
            rep_df = pd.DataFrame([
                {
                    'Event': k,
                    'Sessions': v['sessions_with_repetition'],
                    'Avg Repeats': v['avg_repetitions'],
                    'Max Repeats': v['max_repetitions']
                }
                for k, v in list(repetitions.items())[:10]
            ])

            # Show as metrics
            for _, row in rep_df.iterrows():
                with st.container():
                    st.metric(
                        row['Event'][:40] + '...' if len(row['Event']) > 40 else row['Event'],
                        f"{row['Avg Repeats']:.1f}x avg"
                    )
                    st.caption(f"{row['Sessions']} sessions")
                    if row['Avg Repeats'] > 5:
                        st.error("🔴 CRITICAL FRICTION")
                    elif row['Avg Repeats'] > 3:
                        st.warning("⚠️ High friction")
                    st.markdown("---")

    with tab2:
        st.header("👥 User Segments")
        st.markdown("**Behavioral clustering** - distinct user groups with different needs")

        segments = patterns.get('user_segments', {}).get('segments', {})
        total_users = patterns.get('user_segments', {}).get('total_users', 0)

        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader("Segment Distribution")

            # Donut chart
            seg_data = []
            colors_map = {
                'strugglers': '#FF4B4B',
                'quick_bookers': '#00CC66',
                'explorers': '#4B9EFF',
                'others': '#CCCCCC'
            }

            for seg_name, seg_info in segments.items():
                seg_data.append({
                    'Segment': seg_name.replace('_', ' ').title(),
                    'Count': seg_info.get('count', 0),
                    'Percentage': seg_info.get('percentage', 0)
                })

            seg_df = pd.DataFrame(seg_data)

            fig = px.pie(
                seg_df,
                values='Count',
                names='Segment',
                title=f"User Segments (Total: {total_users:,})",
                hole=0.5,
                color='Segment',
                color_discrete_map={
                    'Strugglers': '#FF4B4B',
                    'Quick Bookers': '#00CC66',
                    'Explorers': '#4B9EFF',
                    'Others': '#CCCCCC'
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, width="stretch")

        with col2:
            st.subheader("Segment Characteristics")

            # Radar chart comparing segments
            categories = ['Event Diversity', 'Repetition Rate', 'Avg Events']

            fig = go.Figure()

            for seg_name, seg_info in segments.items():
                if 'characteristics' in seg_info:
                    chars = seg_info['characteristics']

                    # Normalize values for radar chart (0-100 scale)
                    diversity = chars.get('avg_diversity', 0) * 100
                    repetition = chars.get('avg_repetition', 0) * 100
                    events = min(chars.get('avg_events', 0) / 3, 100)  # Cap at 300 events = 100%

                    fig.add_trace(go.Scatterpolar(
                        r=[diversity, repetition, events],
                        theta=['Event Diversity', 'Repetition Rate', 'Avg Events'],
                        fill='toself',
                        name=seg_name.replace('_', ' ').title()
                    ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                title="Segment Comparison"
            )
            st.plotly_chart(fig, width="stretch")

        # Detailed segment cards
        st.subheader("Segment Profiles")

        cols = st.columns(4)

        for idx, (seg_name, seg_info) in enumerate(segments.items()):
            with cols[idx % 4]:
                priority = "🔴" if seg_name == 'strugglers' else "🟢" if seg_name == 'quick_bookers' else "🔵" if seg_name == 'explorers' else "⚪"

                st.markdown(f"### {priority} {seg_name.replace('_', ' ').title()}")
                st.metric("Users", f"{seg_info.get('count', 0):,}")
                st.caption(f"{seg_info.get('percentage', 0):.1f}% of total users")

                if 'characteristics' in seg_info:
                    chars = seg_info['characteristics']
                    st.markdown(f"**Avg Events**: {chars.get('avg_events', 0):.0f}")
                    st.markdown(f"**Diversity**: {chars.get('avg_diversity', 0):.1%}")
                    st.markdown(f"**Repetition**: {chars.get('avg_repetition', 0):.1%}")

                st.markdown(f"*{seg_info.get('description', '')}*")

                if seg_name == 'strugglers':
                    st.error("🎯 **HIGH PRIORITY**: Needs intervention")
                elif seg_name == 'quick_bookers':
                    st.success("✅ Target segment - optimize for them")

        # LLM Insights for Segments
        if 'llm_insights' in patterns.get('user_segments', {}):
            st.divider()
            with st.expander("🤖 AI Segment Analysis", expanded=True):
                st.markdown(patterns['user_segments']['llm_insights'])

    with tab3:
        st.header("🔥 Friction Analysis")
        st.markdown("**Events causing user hesitation** - where users get stuck")

        friction = patterns.get('friction_points', {})
        high_friction = friction.get('high_friction_events', {})

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Friction Heatmap")

            # Convert to dataframe
            friction_df = pd.DataFrame([
                {
                    'Event': k[:50] + '...' if len(k) > 50 else k,
                    'Repetition Rate': v['repetition_rate'] * 100,
                    'Users Affected': v['users_affected'],
                    'Friction Score': v['friction_score'],
                    'Total Occurrences': v['total_occurrences']
                }
                for k, v in list(high_friction.items())[:15]
            ])

            if not friction_df.empty:
                # Create heatmap-style bar chart
                fig = px.bar(
                    friction_df,
                    x='Friction Score',
                    y='Event',
                    orientation='h',
                    title="Top Friction Events (Higher = Worse UX)",
                    color='Repetition Rate',
                    color_continuous_scale='Reds',
                    hover_data=['Users Affected', 'Total Occurrences'],
                    labels={'Friction Score': 'Friction Score (Repetition Rate * 100)'}
                )
                fig.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, width="stretch")

        with col2:
            st.subheader("🎯 Priority Fixes")

            if not friction_df.empty:
                # Top 5 friction points
                for idx, row in friction_df.head(5).iterrows():
                    st.markdown(f"### {idx + 1}. {row['Event'][:30]}...")

                    # Severity indicator
                    if row['Repetition Rate'] > 80:
                        st.error(f"🔴 CRITICAL: {row['Repetition Rate']:.1f}% repeats")
                    elif row['Repetition Rate'] > 50:
                        st.warning(f"🟡 HIGH: {row['Repetition Rate']:.1f}% repeats")
                    else:
                        st.info(f"🟢 MEDIUM: {row['Repetition Rate']:.1f}% repeats")

                    st.markdown(f"**Users affected**: {row['Users Affected']:,}")
                    st.markdown("---")

            # Summary
            st.subheader("📊 Friction Summary")
            
            # Support both new LLM insights and legacy summary
            friction_summary = friction.get('llm_insights', friction.get('friction_summary'))
            
            if friction_summary:
                st.markdown(friction_summary)

    with tab4:
        st.header("📉 Survival Analysis")
        st.markdown("**Session survival probability** - likelihood of continuing at each step")

        survival = patterns.get('survival_analysis', {})

        if 'survival_curve' in survival:
            curve_data = survival['survival_curve']

            col1, col2 = st.columns([2, 1])

            with col1:
                # Survival curve
                curve_df = pd.DataFrame(curve_data)

                fig = go.Figure()

                # Survival rate line
                fig.add_trace(go.Scatter(
                    x=curve_df['step'],
                    y=curve_df['survival_rate'] * 100,
                    mode='lines+markers',
                    name='Survival Rate',
                    line=dict(color='#4B9EFF', width=3),
                    marker=dict(size=6)
                ))

                # Dropout rate area
                fig.add_trace(go.Scatter(
                    x=curve_df['step'],
                    y=curve_df['dropout_rate'] * 100,
                    mode='lines',
                    name='Dropout Rate',
                    fill='tozeroy',
                    line=dict(color='#FF4B4B', width=1),
                    opacity=0.3
                ))

                # Add zones
                fig.add_hrect(y0=80, y1=100, fillcolor="green", opacity=0.1, line_width=0, annotation_text="Safe Zone", annotation_position="top left")
                fig.add_hrect(y0=50, y1=80, fillcolor="yellow", opacity=0.1, line_width=0)
                fig.add_hrect(y0=0, y1=50, fillcolor="red", opacity=0.1, line_width=0, annotation_text="Danger Zone", annotation_position="bottom left")

                fig.update_layout(
                    title="Session Survival Curve",
                    xaxis_title="Session Step",
                    yaxis_title="Percentage",
                    height=500,
                    hovermode='x unified'
                )

                st.plotly_chart(fig, width="stretch")

            with col2:
                st.subheader("⚠️ Critical Drop-offs")

                critical_drops = survival.get('critical_dropoffs', [])

                if critical_drops:
                    for drop in critical_drops[:5]:
                        st.markdown(f"### Step {drop['step']}")
                        st.metric(
                            "Drop Rate",
                            f"{drop['drop_percentage']:.1f}%"
                        )
                        st.caption(f"{drop['survival_after']*100:.1f}% surviving after this step")
                        st.progress(1 - drop['survival_after'])
                        st.markdown("---")

                # Summary stats
                st.subheader("📊 Key Metrics")
                st.metric("Median Session Length", f"{survival.get('median_session_length', 0)} events")
                st.metric("Reach Step 10", f"{int(survival.get('sessions_reaching_step_10', 0)):,}")
                st.metric("Reach Step 20", f"{int(survival.get('sessions_reaching_step_20', 0)):,}")

    with tab5:
        st.header("🎯 Intervention Triggers")
        st.markdown("**Automated rules** - conditions that predict user drop-off")

        rules = patterns.get('intervention_rules', {})
        triggers = rules.get('intervention_triggers', [])

        if triggers:
            st.subheader(f"Discovered {len(triggers)} High-Confidence Rules")

            # Group by risk level
            high_risk = [r for r in triggers if r['confidence'] > 0.9]
            medium_risk = [r for r in triggers if 0.7 <= r['confidence'] <= 0.9]
            low_risk = [r for r in triggers if r['confidence'] < 0.7]

            col1, col2, col3 = st.columns(3)
            col1.metric("🔴 High Risk Rules", len(high_risk), f">{90}% dropout")
            col2.metric("🟡 Medium Risk Rules", len(medium_risk), "70-90% dropout")
            col3.metric("🟢 Low Risk Rules", len(low_risk), "<70% dropout")

            st.divider()

            # Display rules as cards
            for trigger in triggers[:10]:
                confidence = trigger['confidence']

                # Color based on risk
                if confidence > 0.9:
                    color = "red"
                    icon = "🔴"
                elif confidence > 0.7:
                    color = "orange"
                    icon = "🟡"
                else:
                    color = "green"
                    icon = "🟢"

                with st.expander(f"{icon} **{trigger['condition']}** ({confidence:.0%} dropout risk)", expanded=False):
                    col_a, col_b, col_c = st.columns([2, 1, 2])

                    with col_a:
                        st.markdown("**📊 Risk Assessment**")
                        st.progress(confidence)
                        st.markdown(f"Confidence: {confidence:.1%}")
                        st.markdown(f"Support: {trigger['support']} sessions")

                    with col_b:
                        st.markdown("**⚠️ Outcome**")
                        st.error("User likely to abandon" if confidence > 0.8 else "Elevated drop risk")

                    with col_c:
                        st.markdown("**💡 Recommendation**")
                        st.markdown(trigger['recommendation'])

                        if confidence > 0.8:
                            st.button(f"🚀 Setup Alert", key=f"alert_{trigger['condition']}")

        else:
            st.info("No intervention triggers discovered. Run pattern discovery with more data.")

        # LLM Insights for Interventions
        if 'llm_insights' in rules:
            st.divider()
            with st.expander("🤖 AI Strategy Recommendations", expanded=True):
                st.markdown(rules['llm_insights'])

    # ============================================================================
    # FOOTER
    # ============================================================================
    st.divider()
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Patterns Analyzed", f"{len(patterns.get('sequential_patterns', {}).get('frequent_patterns', {}))}")
    col2.metric("User Segments", f"{len(patterns.get('user_segments', {}).get('segments', {}))}")
    col3.metric("Friction Points", f"{len(patterns.get('friction_points', {}).get('high_friction_events', {}))}")
    col4.metric("Intervention Rules", f"{len(patterns.get('intervention_rules', {}).get('intervention_triggers', []))}")

    st.caption(f"""
    **Algorithms Used**: Sequential Pattern Mining (PrefixSpan), User Clustering, Survival Analysis, Friction Detection, Association Rule Mining
    **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    **Data Source**: pattern_discovery_report.json
    """)

if __name__ == "__main__":
    st.set_page_config(
        page_title="Pattern Discovery Dashboard",
        page_icon="🔍",
        layout="wide"
    )
    render_pattern_discovery()
