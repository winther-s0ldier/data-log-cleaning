import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCE_CSV = os.path.join(PROJECT_ROOT, "Business Events data.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "business_analysis_subset.csv")

# Target around 15,000 events for meaningful patterns without overloading LLM
TARGET_EVENTS = 15000
RANDOM_SEED = 42

def create_business_subset():
    print(f"Loading {SOURCE_CSV}...")
    if not os.path.exists(SOURCE_CSV):
        print(f"ERROR: {SOURCE_CSV} not found.")
        return

    # Load only necessary columns to save memory during processing
    df = pd.read_csv(SOURCE_CSV)
    print(f"  Total events: {len(df):,}  |  Event types: {df['event_name'].nunique()}")

    # 1. Focus on application events (where the real business logic is)
    app_df = df[df["category"].str.lower() == "application"].copy()
    print(f"  Application events: {len(app_df):,}")

    # 2. Add time features for stratified sampling
    app_df["event_time"] = pd.to_datetime(app_df["event_time"], format='mixed')
    app_df["date"] = app_df["event_time"].dt.date
    app_df["hour"] = app_df["event_time"].dt.hour
    
    # 3. Stratified Sampling: Take a slice from every (Date, Hour) block
    # This ensures we don't just get the first or last few days
    unique_blocks = app_df.groupby(["date", "hour"]).size().reset_index()
    events_per_block = max(1, TARGET_EVENTS // len(unique_blocks))
    
    print(f"  Sampling ~{events_per_block} events per hour block across {len(unique_blocks)} blocks...")
    
    rng = np.random.RandomState(RANDOM_SEED)
    
    def sample_group(group):
        if len(group) <= events_per_block:
            return group
        return group.sample(n=events_per_block, random_state=RANDOM_SEED)

    subset = app_df.groupby(["date", "hour"], group_keys=False).apply(sample_group)
    
    # Sort by time to preserve sequence for transition analysis
    subset = subset.sort_values("event_time").reset_index(drop=True)
    
    # Final check on size
    if len(subset) > TARGET_EVENTS * 1.5:
        print(f"  Subset too large ({len(subset):,}), further reducing...")
        subset = subset.sample(n=min(len(subset), int(TARGET_EVENTS * 1.2)), random_state=RANDOM_SEED).sort_values("event_time")

    # Save
    subset.to_csv(OUTPUT_CSV, index=False)
    
    coverage = subset["event_name"].nunique() / df["event_name"].nunique() * 100
    print(f"  Final Subset: {len(subset):,} events, {coverage:.1f}% event coverage")
    print(f"  Saved to {OUTPUT_CSV}")
    return subset

if __name__ == "__main__":
    create_business_subset()
