import pandas as pd
import os
from pathlib import Path

INPUT_FILE = "Commuter Users Event data.csv"
THRESHOLD_MS = 50

SCRIPT_NAME = Path(__file__).stem
BASE_DIR = SCRIPT_NAME
PER_USER_DIR = os.path.join(BASE_DIR, "per_user_cleaned_events")

if os.path.exists(BASE_DIR):
    raise RuntimeError(f"Output folder '{BASE_DIR}' already exists.")

os.makedirs(PER_USER_DIR)

df = pd.read_csv(INPUT_FILE)

df["event_time"] = pd.to_datetime(
    df["event_time"],
    format="%Y-%m-%d %H:%M:%S.%f %z",
    errors="raise"
)

df["event_date"] = df["event_time"].dt.strftime("%Y-%m-%d")
df["event_day"] = df["event_time"].dt.day_name()
df["event_time_only"] = (
    df["event_time"]
    .dt.strftime("%H:%M:%S.%f")
    .apply(lambda x: f"'{x}")
)

df = df.sort_values(
    by=["user_uuid", "event_name", "event_date", "event_time_only"],
    kind="mergesort"
).reset_index(drop=True)

df["time_diff_ms"] = (
    df.groupby(["user_uuid", "event_name"])["event_time"]
      .diff()
      .dt.total_seconds()
      .mul(1000)
)

df["is_canonical"] = (
    df["time_diff_ms"].isna() | (df["time_diff_ms"] > THRESHOLD_MS)
)

cleaned_events = df[df["is_canonical"]].drop(
    columns=["time_diff_ms", "is_canonical"]
)

repetition_summary = (
    df.groupby(["user_uuid", "event_name", "event_date"], as_index=False)
      .agg(
          start_time=("event_time", "min"),
          end_time=("event_time", "max"),
          frequency=("event_time", "size")
      )
)

repetition_summary["repetitions_removed"] = (
    repetition_summary["frequency"] - 1
)

repetition_summary = repetition_summary[
    repetition_summary["repetitions_removed"] > 0
]

repetition_summary["start_time"] = (
    repetition_summary["start_time"].dt.strftime("%H:%M:%S.%f")
)
repetition_summary["end_time"] = (
    repetition_summary["end_time"].dt.strftime("%H:%M:%S.%f")
)

repetition_summary["event_day"] = (
    pd.to_datetime(repetition_summary["event_date"]).dt.day_name()
)

unique_users = cleaned_events[["user_uuid"]].drop_duplicates()

unique_users_report = pd.DataFrame({
    "metric": ["total_unique_users"],
    "value": [len(unique_users)]
})

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

for uid, udf in cleaned_events.groupby("user_uuid", sort=False):
    safe_uid = str(uid).replace("/", "_").replace("\\", "_")
    udf.to_csv(
        os.path.join(PER_USER_DIR, f"user_{safe_uid}.csv"),
        index=False
    )
