"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Optional hard filters
    if max_price is not None:
        listings = [item for item in listings if item["price"] <= max_price]

    if size is not None:
        size_lower = size.lower()
        listings = [
            item for item in listings if size_lower in item.get("size", "").lower()
        ]

    # Keyword scoring
    query_tokens = set(description.lower().split())
    scored = []

    for item in listings:
        score = 0

        # Title and description text
        title = item.get("title", "").lower()
        desc = item.get("description", "").lower()
        for token in query_tokens:
            if token in title:
                score += 2
            if token in desc:
                score += 1

        # Category
        category = item.get("category", "").lower()
        for token in query_tokens:
            if token == category:
                score += 2

        # Style tags
        style_tags = [tag.lower() for tag in item.get("style_tags", [])]
        for token in query_tokens:
            if token in style_tags:
                score += 2

        # Colors
        colors = [color.lower() for color in item.get("colors", [])]
        for token in query_tokens:
            if token in colors:
                score += 1

        if score > 0:
            scored.append((score, item))

    # Sort by score descending, then by price ascending as a tiebreaker
    scored.sort(key=lambda x: (-x[0], x[1]["price"]))
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    item_name = new_item.get("title", "this item")
    item_category = new_item.get("category", "clothing")
    item_style_tags = ", ".join(new_item.get("style_tags", []))
    item_colors = ", ".join(new_item.get("colors", []))
    item_description = new_item.get("description", "")

    wardrobe_items = wardrobe.get("items", [])

    if wardrobe_items:
        wardrobe_text = "\n".join(
            f"- {w['name']} ({w['category']}) — colors: {', '.join(w.get('colors', []))}; style: {', '.join(w.get('style_tags', []))}; notes: {w.get('notes') or 'none'}"
            for w in wardrobe_items
        )
        prompt = (
            f"You are a personal stylist. A user is considering buying this secondhand item:\n"
            f"Name: {item_name}\n"
            f"Category: {item_category}\n"
            f"Colors: {item_colors}\n"
            f"Style tags: {item_style_tags}\n"
            f"Description: {item_description}\n\n"
            f"They already own these wardrobe items:\n{wardrobe_text}\n\n"
            f"Suggest 1-2 complete outfits that incorporate the new item with specific pieces from their wardrobe. "
            f"Reference wardrobe items by name. Keep it concise, practical, and stylish."
        )
    else:
        prompt = (
            f"You are a personal stylist. A user is considering buying this secondhand item:\n"
            f"Name: {item_name}\n"
            f"Category: {item_category}\n"
            f"Colors: {item_colors}\n"
            f"Style tags: {item_style_tags}\n"
            f"Description: {item_description}\n\n"
            f"Their wardrobe is empty. Give general styling advice: what kinds of items pair well with this piece, "
            f"what vibe it suits, and 1-2 complete outfit ideas using common clothing categories. Keep it concise."
        )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful, fashion-savvy stylist."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        suggestion = response.choices[0].message.content.strip()
        if not suggestion:
            raise ValueError("Empty LLM response")
        return suggestion
    except Exception:
        return (
            f"This {item_category} is versatile — try styling it with pieces that match its "
            f"{item_colors} color palette and {item_style_tags} vibe."
        )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Couldn't generate a fit card because the outfit suggestion was missing."

    item_name = new_item.get("title", "this item")
    item_price = new_item.get("price", 0.0)
    item_platform = new_item.get("platform", "a secondhand platform")

    prompt = (
        f"Write a casual, authentic Instagram/TikTok outfit caption (OOTD style) for this thrifted find.\n\n"
        f"Item: {item_name}\n"
        f"Price: ${item_price}\n"
        f"Platform: {item_platform}\n"
        f"Outfit idea: {outfit}\n\n"
        f"Requirements:\n"
        f"- 2-4 sentences\n"
        f"- Sound like a real person, not a product description\n"
        f"- Mention the item name, price, and platform naturally, once each\n"
        f"- Capture the outfit vibe in specific terms\n"
        f"- No hashtags\n\n"
        f"Caption:"
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a Gen Z fashion creator writing casual social media captions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=150,
        )
        caption = response.choices[0].message.content.strip()
        if not caption:
            raise ValueError("Empty LLM response")
        return caption
    except Exception:
        return f"Found {item_name} on {item_platform} for ${item_price} — styled with the outfit above. ✨"
