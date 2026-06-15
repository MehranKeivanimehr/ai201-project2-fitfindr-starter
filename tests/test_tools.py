"""Tests for the FitFindr tools."""

import pytest

from tools import search_listings, suggest_outfit, create_fit_card, compare_price, check_trends
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe, load_listings


# ── search_listings tests ────────────────────────────────────────────────────


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    # Each result should be a listing dict with the expected fields.
    assert "title" in results[0]
    assert "price" in results[0]


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("vintage", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


# ── suggest_outfit tests ─────────────────────────────────────────────────────


def test_suggest_outfit_with_wardrobe():
    listings = load_listings()
    new_item = listings[0]
    wardrobe = get_example_wardrobe()
    suggestion = suggest_outfit(new_item, wardrobe)
    assert isinstance(suggestion, str)
    assert len(suggestion.strip()) > 0


def test_suggest_outfit_empty_wardrobe():
    listings = load_listings()
    new_item = listings[0]
    wardrobe = get_empty_wardrobe()
    suggestion = suggest_outfit(new_item, wardrobe)
    assert isinstance(suggestion, str)
    assert len(suggestion.strip()) > 0


# ── create_fit_card tests ────────────────────────────────────────────────────


def test_create_fit_card_returns_caption():
    listings = load_listings()
    new_item = listings[0]
    outfit = "Pair this with baggy jeans and chunky sneakers for a 90s look."
    caption = create_fit_card(outfit, new_item)
    assert isinstance(caption, str)
    assert len(caption.strip()) > 0


def test_create_fit_card_empty_outfit():
    listings = load_listings()
    new_item = listings[0]
    caption = create_fit_card("", new_item)
    assert isinstance(caption, str)
    assert "missing" in caption.lower() or "couldn't" in caption.lower()


# ── stretch feature tool tests ───────────────────────────────────────────────


def test_compare_price_returns_verdict():
    listings = load_listings()
    item = listings[0]
    verdict = compare_price(item)
    assert isinstance(verdict, str)
    assert len(verdict.strip()) > 0
    assert "$" in verdict


def test_check_trends_returns_string():
    note = check_trends("vintage", size=None)
    assert isinstance(note, str)
    assert len(note.strip()) > 0

