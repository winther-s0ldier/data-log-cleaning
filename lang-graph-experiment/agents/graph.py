from langgraph.graph import StateGraph, START, END
from agents.state import AnalyticsState
from agents.orchestrator import orchestrator_node
from agents.compiler import compiler_node

# Commuter Agents
from agents.metrics.funnel_analysis import funnel_analysis_node
from agents.metrics.dropoff_analysis import dropoff_analysis_node
from agents.metrics.friction_points import friction_points_node
from agents.metrics.session_metrics import session_metrics_node
from agents.metrics.retention_analysis import retention_analysis_node
from agents.metrics.user_segmentation import user_segmentation_node
from agents.metrics.conversion_rates import conversion_rates_node
from agents.metrics.time_to_action import time_to_action_node
from agents.metrics.event_frequency import event_frequency_node
from agents.metrics.temporal_patterns import temporal_patterns_node
from agents.metrics.user_journey_insights import user_journey_insights_node

# Business Agents
from agents.metrics.workflow_funnels import workflow_funnels_node
from agents.metrics.event_transitions import event_transitions_node
from agents.metrics.operational_volume import operational_volume_node
from agents.metrics.growth_trends import growth_trends_node
from agents.metrics.feature_adoption import feature_adoption_node
from agents.metrics.push_roi import push_roi_node
from agents.metrics.business_friction_points import business_friction_points_node


COMMUTER_NODES = {
    "funnel_analysis": funnel_analysis_node,
    "dropoff_analysis": dropoff_analysis_node,
    "friction_points": friction_points_node,
    "session_metrics": session_metrics_node,
    "retention_analysis": retention_analysis_node,
    "user_segmentation": user_segmentation_node,
    "conversion_rates": conversion_rates_node,
    "time_to_action": time_to_action_node,
    "event_frequency": event_frequency_node,
    "temporal_patterns": temporal_patterns_node,
    "user_journey_insights": user_journey_insights_node,
}

BUSINESS_NODES = {
    "workflow_funnels": workflow_funnels_node,
    "event_transitions": event_transitions_node,
    "operational_volume": operational_volume_node,
    "growth_trends": growth_trends_node,
    "feature_adoption": feature_adoption_node,
    "push_roi": push_roi_node,
    "business_friction_points": business_friction_points_node,
    "event_frequency": event_frequency_node,
    "temporal_patterns": temporal_patterns_node,
}


def build_graph(pipeline_type: str = "commuter") -> StateGraph:
    graph = StateGraph(AnalyticsState)
    graph.add_node("orchestrator", orchestrator_node)
    
    nodes = BUSINESS_NODES if pipeline_type == "business" else COMMUTER_NODES
    
    for name, func in nodes.items():
        graph.add_node(name, func)
        
    graph.add_node("compiler", compiler_node)

    graph.add_edge(START, "orchestrator")
    for name in nodes:
        graph.add_edge("orchestrator", name)
    for name in nodes:
        graph.add_edge(name, "compiler")
    graph.add_edge("compiler", END)

    return graph.compile()
