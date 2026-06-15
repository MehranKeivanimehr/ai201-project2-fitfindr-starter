"""
tools.py

The required FitFindr tools plus stretch-feature tools. Each function is a
standalone tool that can be called and tested independently before being wired
into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
    compare_price(item)                              → str
    check_trends(style, size)                        → str
"""

import os
from statistics import mean

import requests
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


# ── Stretch Tool 1: compare_price ─────────────────────────────────────────────

def compare_price(item: dict) -> str:
    """
    Estimate whether an item's price is fair based on comparable listings.

    Comparable listings are defined as items in the same category that share
    at least one style tag or color with the target item. The function computes
    the average, minimum, and maximum prices of those comparables and returns
    a short verdict.

    Args:
        item: A listing dict with `category`, `style_tags`, `colors`, and `price`.

    Returns:
        A short string verdict such as "fair price", "great deal", or "pricey".
        If no comparable listings exist, returns a message explaining that.
    """
    listings = load_listings()

    item_category = item.get("category", "").lower()
    item_styles = {tag.lower() for tag in item.get("style_tags", [])}
    item_colors = {color.lower() for color in item.get("colors", [])}
    item_price = item.get("price", 0.0)

    comparable = []
    for listing in listings:
        if listing.get("id") == item.get("id"):
            continue
        if listing.get("category", "").lower() != item_category:
            continue

        listing_styles = {tag.lower() for tag in listing.get("style_tags", [])}
        listing_colors = {color.lower() for color in listing.get("colors", [])}

        if item_styles & listing_styles or item_colors & listing_colors:
            comparable.append(listing)

    if not comparable:
        return "No comparable listings found in the dataset — can't judge this price."

    prices = [c["price"] for c in comparable]
    avg_price = mean(prices)
    min_price = min(prices)
    max_price = max(prices)

    if item_price < avg_price * 0.8:
        verdict = "great deal"
    elif item_price > avg_price * 1.2:
        verdict = "pricey"
    else:
        verdict = "fair price"

    return (
        f"${item_price:.2f} is a {verdict}. Comparable {item_category} range from "
        f"${min_price:.2f} to ${max_price:.2f}, averaging ${avg_price:.2f}."
    )


# ── Stretch Tool 2: check_trends ──────────────────────────────────────────────

def check_trends(style: str, size: str | None = None) -> str:
    """
    Check what's currently being discussed for a given style on public fashion
    subreddits. Uses Reddit's public JSON API (no API key required).

    Args:
        style: A style keyword such as "vintage", "y2k", or "streetwear".
        size: Optional size string to include in the search context.

    Returns:
        A short summary of recent posts related to the style. If the fetch
        fails or no relevant posts are found, returns a graceful fallback message.
    """
    subreddits = ["fashion", "streetwear", "thriftstorehauls"]
    style_lower = style.lower()
    size_lower = size.lower() if size else None

    matched_titles = []

    try:
        for subreddit in subreddits:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
            headers = {"User-Agent": "FitFindrTrendBot/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            for post in data.get("data", {}).get("children", []):
                title = post.get("data", {}).get("title", "").lower()
                if style_lower in title:
                    if size_lower is None or size_lower in title:
                        matched_titles.append(post["data"]["title"])
    except Exception:
        return "Couldn't fetch trend data right now, but this style is always worth exploring."

    if not matched_titles:
        return f"No recent Reddit posts specifically mentioning '{style}' right now — you're ahead of the curve."

    summary = "; ".join(matched_titles[:5])
    size_note = f" in size {size}" if size else ""
    return (
        f"Recent Reddit buzz around '{style}'{size_note}: {summary}. "
        f"These posts suggest the style is currently active in fashion communities."
    )
