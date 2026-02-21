"""
Run Pattern Discovery on Commuter Event Data

This script executes the Pattern Discovery engine on actual event data
to find behavioral patterns, user segments, and intervention opportunities.

Usage:
    python run_pattern_discovery.py
"""

import pandas as pd
import json
from pattern_discovery import PatternDiscovery


def add_session_ids(events_df: pd.DataFrame, profile_data: dict) -> pd.DataFrame:
    """
    Add session IDs to event data using system event markers.

    Uses the same logic as DataProfiler to ensure consistency.
    """
    events_df = events_df.copy()
    events_df = events_df.sort_values(['user_id', 'timestamp'])

    # System events that mark session boundaries
    session_markers = [
        'Session Started',
        'Journey Started',
        'App Installed',
        'User Login',
        'Push Click'
    ]

    # Mark session boundaries
    events_df['is_session_marker'] = events_df['event_name'].isin(session_markers)

    # Create session IDs (increment on each marker)
    events_df['session_id'] = events_df.groupby('user_id')['is_session_marker'].cumsum()

    # Create unique session identifier
    events_df['session_id'] = (
        events_df['user_id'].astype(str) + '_' +
        events_df['session_id'].astype(str)
    )

    return events_df


def main():
    print("🔍 Pattern Discovery Pipeline")
    print("=" * 60)

    # Load data
    print("\n📂 Loading data...")
    events_df = pd.read_csv('Commuter Users Event data.csv')

    # Standardize column names
    events_df = events_df.rename(columns={
        'user_uuid': 'user_id',
        'event_time': 'timestamp'
    })
    events_df['timestamp'] = pd.to_datetime(events_df['timestamp'], format='mixed')

    print(f"   ✓ Loaded {len(events_df):,} events")
    print(f"   ✓ {events_df['user_id'].nunique():,} unique users")

    # Load profile data for context
    try:
        with open('data_profile_report.json', 'r') as f:
            profile_data = json.load(f)
        print(f"   ✓ Loaded DataProfiler output")
    except FileNotFoundError:
        print("   ⚠️  DataProfiler output not found - run data_profiler.py first")
        profile_data = None

    # Add session IDs
    print("\n🔗 Adding session IDs...")
    events_df = add_session_ids(events_df, profile_data)
    print(f"   ✓ Created {events_df['session_id'].nunique():,} sessions")

    # Filter to application events only
    app_events = events_df[events_df['category'].str.lower() == 'application'].copy()
    print(f"   ✓ {len(app_events):,} application events ({len(app_events)/len(events_df)*100:.1f}%)")

    # Create discovery engine
    print("\n⚙️  Initializing Pattern Discovery Engine...")
    discovery = PatternDiscovery(
        min_pattern_support=0.03,  # 3% minimum (flexible for smaller patterns)
        min_confidence=0.6         # 60% confidence for rules
    )

    # Discover patterns
    print("\n" + "=" * 60)
    patterns = discovery.discover(app_events, profile_data)

    # Apply LLM synthesis for enhanced insights
    print("\n" + "=" * 60)
    print("🤖 Applying LLM Synthesis Layer...")
    print("=" * 60)
    synthesized_patterns = discovery.synthesize_with_llm(
        patterns,
        business_context="bus ticket booking mobile app"
    )

    # Print summary
    discovery.print_summary(synthesized_patterns)

    # Save results
    discovery.save_patterns(synthesized_patterns, 'pattern_discovery_report.json')

    # Generate insights report
    print("\n" + "=" * 60)
    print("📋 KEY INSIGHTS")
    print("=" * 60)

    # Insight 1: Top Friction Points
    friction = patterns.get('friction_points', {}).get('high_friction_events', {})
    if friction:
        print("\n🔴 CRITICAL FRICTION POINTS:")
        for event, metrics in list(friction.items())[:3]:
            print(f"\n   {event}")
            print(f"   └─ {metrics['repetition_rate']:.1%} of occurrences are repeats")
            print(f"   └─ {metrics['users_affected']:,} users affected")
            print(f"   └─ Recommendation: Simplify this step or add inline help")

    # Insight 2: User Segments
    segments = patterns.get('user_segments', {}).get('segments', {})
    if segments:
        print("\n\n👥 USER SEGMENTS:")
        strugglers = segments.get('strugglers', {})
        if strugglers:
            print(f"\n   STRUGGLERS ({strugglers['percentage']:.1f}% of users)")
            print(f"   └─ High repetition rate: {strugglers['characteristics'].get('avg_repetition', 0):.1%}")
            print(f"   └─ {strugglers['count']:,} users need help")
            print(f"   └─ Recommendation: Proactive in-app guidance for this segment")

        explorers = segments.get('explorers', {})
        if explorers:
            print(f"\n   EXPLORERS ({explorers['percentage']:.1f}% of users)")
            print(f"   └─ High event diversity: {explorers['characteristics'].get('avg_diversity', 0):.1%}")
            print(f"   └─ Recommendation: Provide advanced filters and comparison tools")

    # Insight 3: Dropout Sequences
    seq_patterns = patterns.get('sequential_patterns', {})
    dropout_seq = seq_patterns.get('dropout_sequences', {})
    if dropout_seq:
        print("\n\n⚠️  COMMON DROPOUT SEQUENCES:")
        for seq, count in list(dropout_seq.items())[:5]:
            print(f"   • {seq} ({count} sessions)")
            if 'select_seat' in seq.lower():
                print(f"     └─ ACTION: Optimize seat selection UX")
            elif 'login' in seq.lower():
                print(f"     └─ ACTION: Reduce authentication friction")
            elif 'search' in seq.lower():
                print(f"     └─ ACTION: Improve search results quality")

    # Insight 4: Survival Analysis
    survival = patterns.get('survival_analysis', {})
    critical_drops = survival.get('critical_dropoffs', [])
    if critical_drops:
        print("\n\n📉 CRITICAL DROP-OFF STEPS:")
        for drop in critical_drops[:3]:
            print(f"   Step {drop['step']}: {drop['drop_percentage']:.1f}% of users drop")
            print(f"   └─ Survival: {drop['survival_before']:.1%} → {drop['survival_after']:.1%}")

    # Insight 5: Intervention Rules
    rules = patterns.get('intervention_rules', {}).get('intervention_triggers', [])
    if rules:
        print("\n\n🎯 AUTOMATED INTERVENTION TRIGGERS:")
        for rule in rules[:5]:
            print(f"\n   RULE: {rule['condition']}")
            print(f"   └─ Dropout risk: {rule['confidence']:.0%}")
            print(f"   └─ Support: {rule['support']} sessions")
            print(f"   └─ {rule['recommendation']}")

    print("\n" + "=" * 60)
    print("✅ Pattern Discovery Complete!")
    print("\nGenerated Files:")
    print("   • pattern_discovery_report.json - Full pattern data")
    print("\nNext Steps:")
    print("   1. Review friction points and prioritize fixes")
    print("   2. Design targeted interventions for each user segment")
    print("   3. Implement automated triggers based on discovered rules")
    print("   4. A/B test interventions and measure impact")
    print("=" * 60)


if __name__ == "__main__":
    main()
