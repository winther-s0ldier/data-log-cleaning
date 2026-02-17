import sys
import os
# Mocking the path setup done in server.py
# Add lang-graph-experiment to sys.path to allow importing agents
sys.path.insert(0, os.path.join(os.getcwd(), "lang-graph-experiment"))

print(f"Testing imports from {os.path.join(os.getcwd(), 'lang-graph-experiment')}")

try:
    from agents.graph import build_graph
    print("Successfully imported build_graph from agents.graph")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
