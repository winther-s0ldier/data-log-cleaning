import pandas as pd
import os
from pathlib import Path

INPUT_FILE = "Business Events data.csv"

SCRIPT_NAME = Path(__file__).stem
BASE_DIR = SCRIPT_NAME
PER_USER_DIR = os.path.join(BASE_DIR, "per_user_cleaned_events")

if os.path.exists(BASE_DIR):
    raise RuntimeError(f"Output folder '{BASE_DIR}' already exists.")

os.makedirs(PER_USER_DIR)

# ---- Load ----
# Business CSV: id, event_name, category, event_time, external_event_id, source
# No user_uuid column — 'id' is a sequential row ID, 'external_event_id' is per-event unique.
# We keep 'id' renamed to 'user_uuid' so downstream app1 code works unchanged.
# Deduplication is done globally (consecutive duplicate event_names by time order).

df = pd.read_csv(INPUT_FILE)

# ---- Filter: keep APPLICATION events only (exclude system events) ----
before_filter = len(df)
df = df[df["category"] == "application"].copy()
print(f"Filtered out {before_filter - len(df)} system events, kept {len(df)} application events")

# Rename 'id' -> 'user_uuid' for downstream compatibility
df = df.rename(columns={"id": "user_uuid"})

# Drop columns not needed downstream
df = df.drop(columns=["external_event_id", "source"], errors="ignore")

# ---- Parse time ----
df["event_time"] = pd.to_datetime(
    df["event_time"],
    format="%Y-%m-%d %H:%M:%S.%f %z",
    errors="coerce"
)

# Drop rows where time couldn't be parsed
before = len(df)
df = df.dropna(subset=["event_time"])
dropped = before - len(df)
if dropped:
    print(f"Dropped {dropped} rows with unparseable event_time")

# ---- Derived time columns ----
df["event_date"] = df["event_time"].dt.strftime("%Y-%m-%d")
df["event_day"] = df["event_time"].dt.day_name()
df["event_time_only"] = (
    df["event_time"]
    .dt.strftime("%H:%M:%S.%f")
    .apply(lambda x: f"'{x}")
)

# ---- Sort by time ----
df = df.sort_values(
    by=["event_time"],
    kind="mergesort"
).reset_index(drop=True)

# ---- Consecutive dedup (global, since no per-user grouping) ----
df["prev_event_name"] = df["event_name"].shift(1)

df["is_canonical"] = (
    df["prev_event_name"].isna() | (df["event_name"] != df["prev_event_name"])
)

df = df.drop(columns=["prev_event_name"])

cleaned_events = df[df["is_canonical"]].drop(
    columns=["is_canonical"]
)

df["is_consecutive_dup"] = ~df["is_canonical"]

consecutive_dups = df[df["is_consecutive_dup"]].copy()

if len(consecutive_dups) > 0:
    repetition_summary = (
        consecutive_dups.groupby(["event_name", "category", "event_date"], as_index=False)
          .agg(
              start_time=("event_time", "min"),
              end_time=("event_time", "max"),
              frequency=("event_time", "size")
          )
    )
    # Add user_uuid column (empty string) for schema compatibility
    repetition_summary["user_uuid"] = ""
    repetition_summary["repetitions_removed"] = repetition_summary["frequency"]
else:
    repetition_summary = pd.DataFrame(columns=[
        "user_uuid", "event_name", "category", "event_date", "start_time", "end_time",
        "frequency", "repetitions_removed"
    ])

if len(repetition_summary) > 0:
    repetition_summary["start_time"] = (
        repetition_summary["start_time"].dt.strftime("%H:%M:%S.%f")
    )
    repetition_summary["end_time"] = (
        repetition_summary["end_time"].dt.strftime("%H:%M:%S.%f")
    )
    repetition_summary["event_day"] = (
        pd.to_datetime(repetition_summary["event_date"]).dt.day_name()
    )

# ---- Unique "users" (unique IDs) ----
unique_users = cleaned_events[["user_uuid"]].drop_duplicates()

unique_users_report = pd.DataFrame({
    "metric": ["total_unique_users"],
    "value": [len(unique_users)]
})

# ---- Save outputs ----

cleaned_events.to_csv(
    os.path.join(BASE_DIR, "cleaned_events.csv"),
    index=False
)

repetition_summary.to_csv(
    os.path.join(BASE_DIR, "repetition_summary.csv"),
    index=False
)

unique_users.to_csv(
    os.path.join(BASE_DIR, "unique_users_list.csv"),
    index=False
)

unique_users_report.to_csv(
    os.path.join(BASE_DIR, "unique_users_count.csv"),
    index=False
)

# Per-user CSVs (each 'id' is unique so each file = 1 row, but keeping for compatibility)
# Skip per-user export for business data since ids are row-level, not user-level
# for uid, udf in cleaned_events.groupby("user_uuid", sort=False):
#     safe_uid = str(uid).replace("/", "_").replace("\\", "_")
#     udf.to_csv(
#         os.path.join(PER_USER_DIR, f"user_{safe_uid}.csv"),
#         index=False
#     )

print(f"Done! Original rows: {before}")
print(f"Cleaned events: {len(cleaned_events)}")
print(f"Duplicates removed: {len(consecutive_dups)}")
print(f"Unique IDs: {len(unique_users)}")
