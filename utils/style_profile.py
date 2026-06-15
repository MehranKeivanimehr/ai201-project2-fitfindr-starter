"""Style profile memory for FitFindr.

Stores and retrieves a user's style preferences across sessions in a JSON file.
The profile is updated after each successful search and can be used to influence
future searches and outfit suggestions.
"""

import json
import os
from collections import Counter

_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "style_profile.json")


def _default_profile() -> dict:
    return {
        "preferred_styles": [],
        "preferred_colors": [],
        "preferred_sizes": [],
        "recent_searches": [],
    }


def load_style_profile() -> dict:
    """Load the user's style profile from disk.

    Returns:
        A dict with preferred_styles, preferred_colors, preferred_sizes,
        and recent_searches. Returns a default empty profile if the file
        does not exist yet.
    """
    if not os.path.exists(_PROFILE_PATH):
        return _default_profile()

    try:
        with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = json.load(f)
            # Ensure all expected keys exist
            for key in _default_profile():
                profile.setdefault(key, [])
            return profile
    except (json.JSONDecodeError, IOError):
        return _default_profile()


def save_style_profile(profile: dict) -> None:
    """Save the user's style profile to disk."""
    try:
        with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
    except IOError:
        pass


def _top_items(counter: Counter, n: int = 5) -> list[str]:
    return [item for item, _ in counter.most_common(n)]


def update_style_profile(profile: dict, query: str, selected_item: dict) -> dict:
    """Update the style profile based on a successful interaction.

    Args:
        profile: The current style profile dict.
        query: The user's original query.
        selected_item: The listing dict selected by the agent.

    Returns:
        The updated profile dict.
    """
    # Update recent searches (keep last 10)
    profile["recent_searches"] = ([query] + profile.get("recent_searches", []))[:10]

    # Collect styles and colors from selected item
    style_counter = Counter(profile.get("preferred_styles", []))
    color_counter = Counter(profile.get("preferred_colors", []))
    size_counter = Counter(profile.get("preferred_sizes", []))

    for style in selected_item.get("style_tags", []):
        style_counter[style.lower()] += 1

    for color in selected_item.get("colors", []):
        color_counter[color.lower()] += 1

    size = selected_item.get("size")
    if size:
        size_counter[size.lower()] += 1

    profile["preferred_styles"] = _top_items(style_counter)
    profile["preferred_colors"] = _top_items(color_counter)
    profile["preferred_sizes"] = _top_items(size_counter)

    return profile
