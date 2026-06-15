"""Tests for the style profile memory utility."""

import os
import tempfile

from utils.style_profile import (
    load_style_profile,
    save_style_profile,
    update_style_profile,
)


def test_load_default_profile():
    profile = load_style_profile()
    assert "preferred_styles" in profile
    assert "preferred_colors" in profile
    assert "preferred_sizes" in profile
    assert "recent_searches" in profile


def test_update_and_save_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Point the profile path to a temp file for this test
        from utils import style_profile

        original_path = style_profile._PROFILE_PATH
        style_profile._PROFILE_PATH = os.path.join(tmpdir, "style_profile.json")

        try:
            profile = load_style_profile()
            selected_item = {
                "id": "lst_001",
                "title": "Vintage Levi's 501 Jeans",
                "category": "bottoms",
                "style_tags": ["vintage", "denim"],
                "colors": ["blue", "indigo"],
                "size": "W30 L30",
                "price": 38.0,
                "platform": "depop",
            }
            updated = update_style_profile(profile, "vintage jeans", selected_item)
            save_style_profile(updated)

            reloaded = load_style_profile()
            assert "vintage" in reloaded["preferred_styles"]
            assert "blue" in reloaded["preferred_colors"]
            assert "w30 l30" in reloaded["preferred_sizes"]
            assert "vintage jeans" in reloaded["recent_searches"]
        finally:
            style_profile._PROFILE_PATH = original_path
