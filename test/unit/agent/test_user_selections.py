"""
Test Suite: UserSelections Model & Helper Functions
Mapping: src/agent/state/schema.py (UserSelections), src/agent/nodes/planner/node.py (_summarise_user_selections),
         src/agent/nodes/manager/node.py (_summarise_recommendation_data)
Priority: P0 — User selection flow correctness
"""

import pytest

from src.agent.state.schema import (
    ExecutionSigns,
    RecommenderOutput,
    UserSelections,
)


# =============================================================================
# P0 — UserSelections model
# =============================================================================


@pytest.mark.priority("P0")
def test_user_selections_default():
    """Default UserSelections has all None fields and needs_reselect=False."""
    sel = UserSelections()
    assert sel.chosen_destination is None
    assert sel.chosen_accommodation is None
    assert sel.chosen_dining is None
    assert sel.needs_reselect is False
    assert sel.reselection_feedback is None


@pytest.mark.priority("P0")
def test_user_selections_agent_choice():
    """agent_choice sentinel accepted for all fields."""
    sel = UserSelections(
        chosen_destination="agent_choice",
        chosen_accommodation="agent_choice",
        chosen_dining="agent_choice",
    )
    assert sel.chosen_destination == "agent_choice"
    assert sel.chosen_accommodation == "agent_choice"
    assert sel.chosen_dining == "agent_choice"


@pytest.mark.priority("P0")
def test_user_selections_specific_choices():
    """User picks specific items from recommendation list."""
    sel = UserSelections(
        chosen_destination="东京",
        chosen_accommodation="浅草民宿",
        chosen_dining="agent_choice",
    )
    assert sel.chosen_destination == "东京"
    assert sel.chosen_accommodation == "浅草民宿"
    assert sel.chosen_dining == "agent_choice"


@pytest.mark.priority("P0")
def test_user_selections_needs_reselect():
    """When user is unsatisfied, needs_reselect=True with feedback."""
    sel = UserSelections(
        needs_reselect=True,
        reselection_feedback="太贵了，有没有更经济的选择？",
    )
    assert sel.needs_reselect is True
    assert "经济" in sel.reselection_feedback


@pytest.mark.priority("P0")
def test_user_selections_serialization():
    """UserSelections round-trips through model_dump()."""
    sel = UserSelections(
        chosen_destination="大阪",
        chosen_accommodation="agent_choice",
        chosen_dining="道顿堀拉面店",
        needs_reselect=False,
    )
    d = sel.model_dump()
    assert d["chosen_destination"] == "大阪"
    assert d["chosen_dining"] == "道顿堀拉面店"
    # model_dump → dict → reconstruct
    sel2 = UserSelections(**d)
    assert sel2.chosen_destination == "大阪"
    assert sel2.chosen_accommodation == "agent_choice"


# =============================================================================
# P0 — _summarise_user_selections (Planner helper)
# =============================================================================


@pytest.mark.priority("P0")
def test_summarise_user_selections_none():
    """No user_selections → message says user hasn't chosen yet."""
    from src.agent.nodes.planner.node import _summarise_user_selections

    state = {}
    result = _summarise_user_selections(state)
    assert "尚未做出选择" in result


@pytest.mark.priority("P0")
def test_summarise_user_selections_all_agent_choice():
    """All fields = agent_choice → Planner has free rein."""
    from src.agent.nodes.planner.node import _summarise_user_selections

    state = {
        "user_selections": {
            "chosen_destination": "agent_choice",
            "chosen_accommodation": "agent_choice",
            "chosen_dining": "agent_choice",
        }
    }
    result = _summarise_user_selections(state)
    assert "随便" in result or "都行" in result or "自由选取" in result


@pytest.mark.priority("P0")
def test_summarise_user_selections_specific():
    """User selected specific items → Planner must respect them."""
    from src.agent.nodes.planner.node import _summarise_user_selections

    state = {
        "user_selections": {
            "chosen_destination": "京都",
            "chosen_accommodation": "agent_choice",
            "chosen_dining": "祇园怀石料理",
        }
    }
    result = _summarise_user_selections(state)
    assert "京都" in result
    assert "祇园怀石料理" in result
    assert "严格遵守" in result


# =============================================================================
# P1 — _summarise_recommendation_data (Manager helper)
# =============================================================================


@pytest.mark.priority("P1")
def test_summarise_recommendation_data_none():
    """No recommendation data → '暂无'."""
    from src.agent.nodes.manager.node import _summarise_recommendation_data

    state = {}
    result = _summarise_recommendation_data(state)
    assert "暂无" in result


@pytest.mark.priority("P1")
def test_summarise_recommendation_data_with_content():
    """Recommendation data summarized for Manager context."""
    from src.agent.nodes.manager.node import _summarise_recommendation_data

    state = {
        "recommendation_data": {
            "destinations": [{"name": "东京"}],
            "accommodations": [{"name": "浅草民宿"}, {"name": "新宿酒店"}],
            "dining": [
                {"name": "寿司店"}, {"name": "拉面店"}, {"name": "天妇罗店"}
            ],
        }
    }
    result = _summarise_recommendation_data(state)
    assert "东京" in result
    assert "住宿(2)" in result
    assert "餐饮(3)" in result
    assert "浅草民宿" in result


# =============================================================================
# P1 — ExecutionSigns with is_selection_made
# =============================================================================


@pytest.mark.priority("P1")
def test_execution_signs_is_selection_made_default():
    """is_selection_made defaults to False."""
    signs = ExecutionSigns()
    assert signs.is_selection_made is False


@pytest.mark.priority("P1")
def test_execution_signs_is_selection_made_true():
    """is_selection_made can be set to True."""
    signs = ExecutionSigns(is_selection_made=True)
    assert signs.is_selection_made is True
