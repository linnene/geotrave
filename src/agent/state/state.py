"""
Module: src.agent.state
Responsibility: Defines the typed dictionaries for LangGraph state management in Agent 2.0.
Parent Module: src.agent
Dependencies: typing, langgraph, src.agent.schema

This module serves as the global blueprint (State) for the agent. It strictly follows
the decoupling principle: raw data is stored externally, while this state carries
references, metadata, and control flags.
"""

from typing import Annotated, List, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from src.agent.state.schema import UserProfile, ResearchManifest, RouteMetadata, TraceLog

class TravelState(TypedDict):
    """
    Agent 2.0 Global Blackboard State.
    
    Attributes:
        messages: Full conversation history, using add_messages for automatic appending.
        user_profile: Structured constraints and preferences extracted by the Analyst.
        research_data: Status of the current research loop, including queries and KV hashes.
        route_metadata: Control flow metadata used by Manager and conditional edges.
        trace_history: Audit trail of node executions for observability and debugging.
        needs_exit: Global termination signal.
    """
    # [Conversation & Context]
    messages: Annotated[List[BaseMessage], add_messages]
    
    # [Structured Business Data]
    user_profile: UserProfile
    research_data: ResearchManifest
    
    # [Orchestration & Control]
    route_metadata: RouteMetadata
    
    # [Observability & Audit]
    trace_history: List[TraceLog]
    
    # [Safety & Signals]
    needs_exit: bool
