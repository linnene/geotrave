"""
Module: src.agent.schema
Responsibility: Defines all Pydantic models for structured LLM data extraction and validation.
Parent Module: src.agent
Dependencies: pydantic, typing

These robust data transfer objects (DTOs) bridge the output from Analyzer and Researcher 
nodes with the downstream internal State representation. 
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# ==============================================================================
# Analyzer Node Schemas
# ==============================================================================

class UserProfile(BaseModel):
    """
    Flattened representation of user travel demands and preferences.
    Used by the Analyzer to aggregate multi-turn dialogue into structured constraints.
    """
    destination: List[str] = Field(default_factory=list, description="List of destinations")
    days: Optional[int] = Field(default=None, description="Number of travel days")
    date: Optional[List[Optional[str]]] = Field(default=None, min_length=2, max_length=2, description="Start and end dates")
    people_count: Optional[int] = Field(default=1, description="Total number of travelers")
    budget_limit: Optional[int] = Field(default=0, description="Maximum budget limit")
    
    accommodation: Optional[str] = Field(default=None, description="Accommodation preferences (e.g., 5-star, hostel)")
    dining: Optional[str] = Field(default=None, description="Dining preferences or restrictions (e.g., vegetarian, no seafood)")
    transportation: Optional[str] = Field(default=None, description="Transportation preferences (e.g., train, self-driving)")
    pace: Optional[str] = Field(default=None, description="Travel pace (e.g., relaxed, intensive)")
    activities: List[str] = Field(default_factory=list, description="Explicit activities the user wants to experience")
    
    preferences: List[str] = Field(default_factory=list, description="Additional unstructured positive interests")
    avoidances: List[str] = Field(default_factory=list, description="Negative options or constraints the user wants to strictly avoid")

class TravelInfo(BaseModel):
    """
    Payload emitted by the Analyzer node after processing user input.
    """
    user_profile: UserProfile = Field(default_factory=UserProfile)
    needs_research: bool = Field(default=False, description="Flag indicating if the Researcher node should be triggered")
    reply: str = Field(description="The response/clarification question directed back to the user")

# ==============================================================================
# Researcher Node Schemas
# ==============================================================================

class ResearchPlan(BaseModel):
    """
    Search plan formulated by the Researcher node to acquire external knowledge.
    """
    local_query: Optional[str] = Field(default=None, description="Query string for local knowledge base")
    web_queries: List[str] = Field(default_factory=list, description="List of queries for external web search")
    need_weather: bool = Field(default=False, description="Flag indicating if weather information is required")
    need_api: List[str] = Field(default_factory=list, description="Optional third-party APIs to invoke")