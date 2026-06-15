"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card, compare_price, check_trends
from utils.style_profile import load_style_profile, save_style_profile, update_style_profile


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "price_comparison": None,    # string from compare_price
        "trend_note": None,          # string from check_trends
        "retry_note": None,          # note about loosened search constraints
        "style_profile": None,       # loaded user style profile
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _search_with_retry(description, size, max_price):
    """
    Try searching with the original constraints, then loosen them if no results.

    Returns a tuple: (results, retry_note). retry_note is None if the first
    attempt succeeded, otherwise a string explaining what was adjusted.
    """
    results = search_listings(description=description, size=size, max_price=max_price)
    if results:
        return results, None

    # Retry 1: remove size filter
    if size is not None:
        results = search_listings(description=description, size=None, max_price=max_price)
        if results:
            return results, f"No exact matches in size {size}; showing results across all sizes."

    # Retry 2: increase max_price by 50%
    if max_price is not None:
        relaxed_price = max_price * 1.5
        results = search_listings(description=description, size=size, max_price=relaxed_price)
        if results:
            return results, f"Nothing under ${max_price:.2f}; expanded budget to ${relaxed_price:.2f}."

    # Retry 3: remove size and increase price
    if size is not None and max_price is not None:
        relaxed_price = max_price * 1.5
        results = search_listings(description=description, size=None, max_price=relaxed_price)
        if results:
            return (
                results,
                f"No matches in size {size} under ${max_price:.2f}; showing all sizes up to ${relaxed_price:.2f}.",
            )

    return [], None


def _parse_query(query: str) -> dict:
    """Parse a natural-language query into description, size, and max_price."""
    cleaned_query = query.strip()

    # Extract max_price: "under $30", "under 30", "less than $40", "< $50"
    max_price = None
    price_match = re.search(
        r"(?:under|less than|<)\s*\$?(\d+(?:\.\d+)?)", cleaned_query, re.IGNORECASE
    )
    if price_match:
        max_price = float(price_match.group(1))
        cleaned_query = cleaned_query[: price_match.start()] + cleaned_query[price_match.end() :]

    # Extract size: "size M", "size S/M", "size W30 L30", "size US 8"
    size = None
    size_match = re.search(
        r"size\s+(.+?)(?:,|\s+(?:under|less than|<)|$)", cleaned_query, re.IGNORECASE
    )
    if size_match:
        size = size_match.group(1).strip()
        cleaned_query = cleaned_query[: size_match.start()] + cleaned_query[size_match.end() :]

    # Remaining text is the description
    description = re.sub(r"\s+", " ", cleaned_query).strip(" ,")

    return {"description": description, "size": size, "max_price": max_price}


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    session = _new_session(query, wardrobe)

    # Load style profile memory
    profile = load_style_profile()
    session["style_profile"] = profile

    # Parse the query
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # Search with retry logic
    results, retry_note = _search_with_retry(
        parsed["description"], parsed["size"], parsed["max_price"]
    )
    session["search_results"] = results
    session["retry_note"] = retry_note

    if not session["search_results"]:
        session["error"] = (
            "I couldn't find anything matching that, even with looser constraints. "
            "Try broadening your search with more general keywords."
        )
        return session

    # Select top result
    session["selected_item"] = session["search_results"][0]

    # Stretch: price comparison
    session["price_comparison"] = compare_price(session["selected_item"])

    # Stretch: trend awareness
    style_for_trends = session["selected_item"].get("style_tags", ["vintage"])[0]
    session["trend_note"] = check_trends(style_for_trends, parsed["size"])

    # Suggest outfit
    session["outfit_suggestion"] = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=session["wardrobe"],
    )

    # Create fit card
    session["fit_card"] = create_fit_card(
        outfit=session["outfit_suggestion"],
        new_item=session["selected_item"],
    )

    # Stretch: update style profile memory
    updated_profile = update_style_profile(profile, query, session["selected_item"])
    save_style_profile(updated_profile)
    session["style_profile"] = updated_profile

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
