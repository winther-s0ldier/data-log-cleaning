import os
import sys
import time
import argparse

# Ensure this script works from any cwd by setting paths relative to itself
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def main():
    parser = argparse.ArgumentParser(description="Run LangGraph Analytics Pipeline")
    parser.add_argument("--type", type=str, choices=["commuter", "business"], default="commuter",
                        help="Pipeline type: commuter (default) or business")
    args = parser.parse_args()
    
    pipeline_type = args.type
    os.chdir(SCRIPT_DIR)
    sys.path.insert(0, SCRIPT_DIR)
    os.environ["PYTHONIOENCODING"] = "utf-8"

    filename = "analysis_subset.csv" if pipeline_type == "commuter" else "business_analysis_subset.csv"
    subset_path = os.path.join(SCRIPT_DIR, filename)

    if not os.path.exists(subset_path):
        print("=" * 60)
        print(f"Step 1: Creating {pipeline_type} analysis subset...")
        print("=" * 60)
        if pipeline_type == "commuter":
            from create_subset import create_subset
            create_subset()
        else:
            from create_business_subset import create_business_subset
            create_business_subset()
        print()

    if not os.path.exists(subset_path):
        print(f"ERROR: {subset_path} not found.")
        sys.exit(1)

    print("=" * 60)
    print(f"Step 2: Building {pipeline_type.capitalize()} LangGraph pipeline...")
    print("=" * 60)

    from agents.graph import build_graph
    graph = build_graph(pipeline_type=pipeline_type)

    initial_state = {
        "dataset_path": subset_path,
        "pipeline_type": pipeline_type,
        "dataset_summary": {},
        "metric_results": {},
        "compiled_report": {},
        "errors": [],
    }

    print()
    print("=" * 60)
    print(f"Step 3: Executing {pipeline_type} pipeline...")
    print("=" * 60)

    start = time.time()
    result = graph.invoke(initial_state)
    elapsed = time.time() - start

    print()
    print("=" * 60)
    print(f"Pipeline complete in {elapsed:.1f}s")
    print("=" * 60)

    compiled = result.get("compiled_report", {})
    metrics = compiled.get("metrics_completed", [])
    errors = compiled.get("metrics_failed", [])
    html_path = compiled.get("html_path", "")

    print(f"\nMetrics completed: {len(metrics)}")
    for m in sorted(metrics):
        print(f"  [OK] {m}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  [FAIL] {e}")

    if html_path:
        abs_path = os.path.abspath(html_path)
        print(f"\n>> Open the report:")
        print(f"   {abs_path}")


if __name__ == "__main__":
    main()
