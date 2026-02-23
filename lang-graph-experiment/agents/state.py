from typing import TypedDict, Annotated
import operator


def merge_dicts(a: dict, b: dict) -> dict:
    merged = a.copy()
    merged.update(b)
    return merged


class AnalyticsState(TypedDict):
    dataset_path: str
    pipeline_type: str  # "commuter" or "business"
    dataset_summary: dict
    analysis_plan: list[str]  # List of task descriptions
    agent_specs: dict  # Dynamic configs for agents
    metric_results: Annotated[dict, merge_dicts]
    compiled_report: dict
    errors: Annotated[list, operator.add]
    dynamic_code_registry: dict  # Stores generated analysis code
