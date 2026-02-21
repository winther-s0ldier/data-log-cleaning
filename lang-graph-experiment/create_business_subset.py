import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Use the cleaned, deduped, application-only pipeline output so that
# the global report sees the exact same date range as the dashboard.
SOURCE_CSV = os.path.join(PROJECT_ROOT, "pipeline_business_deduplication", "cleaned_events.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "business_analysis_subset.csv")

# Target around 15,000 events for meaningful patterns without overloading LLM
TARGET_EVENTS = 15000
RANDOM_SEED = 42


def create_business_subset():
    print(f"Loading {SOURCE_CSV}...")
    if not os.path.exists(SOURCE_CSV):
        print(f"ERROR: {SOURCE_CSV} not found.")
        return

    # Cleaned CSV already has only application events (system events were filtered
    # out by pipeline_business_deduplication.py).
    df = pd.read_csv(SOURCE_CSV)
    print(f"  Total events: {len(df):,}  |  Event types: {df['event_name'].nunique()}")

    app_df = df.copy()
    print(f"  Application events (cleaned): {len(app_df):,}")

    # cleaned_events.csv already has event_date and event_time_only split columns
    # Use them directly to avoid re-parsing the tz-aware event_time string
    app_df["date"] = pd.to_datetime(app_df["event_date"]).dt.date
    app_df["hour"] = pd.to_datetime(
        app_df["event_time_only"].astype(str).str[:8], format="%H:%M:%S", errors="coerce"
    ).dt.hour.fillna(0).astype(int)

    # Stratified Sampling: Take a slice from every (Date, Hour) block.
    # This ensures we don't just get the first or last few days.
    unique_blocks = app_df.groupby(["date", "hour"]).size().reset_index()
    events_per_block = max(1, TARGET_EVENTS // len(unique_blocks))

    print(f"  Sampling ~{events_per_block} events per hour block across {len(unique_blocks)} blocks...")

    def sample_group(group):
        if len(group) <= events_per_block:
            return group
        return group.sample(n=events_per_block, random_state=RANDOM_SEED)

    subset = app_df.groupby(["date", "hour"], group_keys=False).apply(sample_group)

    # Sort by time to preserve sequence for transition analysis
    subset = subset.sort_values("event_time").reset_index(drop=True)

    # Final size guard
    if len(subset) > TARGET_EVENTS * 1.5:
        print(f"  Subset too large ({len(subset):,}), further reducing...")
        subset = subset.sample(
            n=min(len(subset), int(TARGET_EVENTS * 1.2)),
            random_state=RANDOM_SEED
        ).sort_values("event_time")

    subset.to_csv(OUTPUT_CSV, index=False)

    coverage = subset["event_name"].nunique() / df["event_name"].nunique() * 100
    print(f"  Final Subset: {len(subset):,} events, {coverage:.1f}% event coverage")
    print(f"  Saved to {OUTPUT_CSV}")
    return subset


if __name__ == "__main__":
    create_business_subset()
