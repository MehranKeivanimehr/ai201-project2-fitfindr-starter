"""Tests for the FitFindr planning loop in agent.py."""

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


def test_run_agent_happy_path():
    session = run_agent(
        query="vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["outfit_suggestion"] is not None
    assert session["fit_card"] is not None
    assert session["parsed"]["max_price"] == 30.0


def test_run_agent_no_results():
    session = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is not None
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None


def test_run_agent_empty_wardrobe():
    session = run_agent(
        query="vintage graphic tee",
        wardrobe=get_empty_wardrobe(),
    )
    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["outfit_suggestion"] is not None
    assert session["fit_card"] is not None


def test_run_agent_parses_size():
    session = run_agent(
        query="90s track jacket in size M",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is None
    assert session["parsed"]["size"] == "M"
    assert "track jacket" in session["parsed"]["description"].lower()


def test_run_agent_retry_with_looser_constraints():
    """A query with an impossible size should still find results after retry."""
    session = run_agent(
        query="vintage graphic tee size XXS under $30",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["retry_note"] is not None
    assert "XXS" in session["retry_note"]
