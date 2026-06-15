# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Loads the mock secondhand listings dataset and returns the items that best match the user's description, optionally filtered by size and maximum price. Results are ranked by keyword relevance so the most relevant items appear first.

**Input parameters:**
- `description` (str, required): Keywords describing the item the user wants, e.g. `"vintage graphic tee"` or `"90s track jacket"`. This is tokenized into individual words for scoring.
- `size` (str | None, optional): A size string to filter by, e.g. `"M"`, `"S/M"`, or `"W30 L30"`. Matching is case-insensitive and substring-based so that `"M"` matches `"S/M"` or `"M/L"`. If `None`, no size filtering is applied.
- `max_price` (float | None, optional): A maximum price ceiling (inclusive), e.g. `30.0`. If `None`, no price filtering is applied.

**What it returns:**
A `list[dict]` of matching listing dictionaries, sorted by relevance score from highest to lowest. Each dict contains the exact fields from `data/listings.json`:
- `id` (str)
- `title` (str)
- `description` (str)
- `category` (str): one of `tops`, `bottoms`, `outerwear`, `shoes`, `accessories`
- `style_tags` (list[str])
- `size` (str)
- `condition` (str): `excellent`, `good`, or `fair`
- `price` (float)
- `colors` (list[str])
- `brand` (str | None)
- `platform` (str): `depop`, `thredUp`, or `poshmark`

The list may be empty if no listings match.

**What happens if it fails or returns nothing:**
The tool itself returns an empty list and does not raise exceptions. The agent checks the returned list; if it is empty, the agent sets `session["error"]` to a helpful message such as "I couldn't find anything matching that. Try broadening your search — remove the size filter, increase the price limit, or use more general keywords." and returns the session early without calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
Takes the listing selected by `search_listings` and the user's existing wardrobe, then suggests 1–2 complete outfits that incorporate the new item with pieces the user already owns. Uses the Groq LLM when the wardrobe is populated so suggestions reference actual wardrobe items by name.

**Input parameters:**
- `new_item` (dict, required): The selected listing dict from `search_listings`, containing all listing fields (`title`, `category`, `colors`, `style_tags`, `price`, `platform`, etc.).
- `wardrobe` (dict, required): A wardrobe dict with an `items` key containing a list of wardrobe item dicts. Each wardrobe item has:
  - `id` (str)
  - `name` (str)
  - `category` (str): one of `tops`, `bottoms`, `outerwear`, `shoes`, `accessories`
  - `colors` (list[str])
  - `style_tags` (list[str])
  - `notes` (str | None)

**What it returns:**
A non-empty `str` containing 1–2 outfit suggestions. If the wardrobe has items, the string names specific pieces from the wardrobe (e.g. "Pair this with your baggy straight-leg jeans and chunky white sneakers..."). If the wardrobe is empty, the string gives general styling advice for the new item (e.g. "This tee works great with baggy jeans and chunky sneakers...").

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty, the tool does not fail; it calls the LLM with a prompt that asks for general styling advice instead of specific wardrobe combinations. If the LLM returns an empty string, the tool falls back to a generic but useful message: "This piece is versatile — try styling it with items you already own that match its color and vibe."

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, casual, shareable outfit caption — the kind someone would post on Instagram or TikTok — using the outfit suggestion from `suggest_outfit` and the selected item's details. The caption should feel authentic, mention the item name, price, and platform naturally, and capture the outfit vibe.

**Input parameters:**
- `outfit` (str, required): The outfit suggestion string returned by `suggest_outfit()`.
- `new_item` (dict, required): The selected listing dict from `search_listings`, used to pull `title`, `price`, and `platform` into the caption.

**What it returns:**
A `str` containing 2–4 sentences suitable as a social-media caption. The caption should:
- Sound casual and personal, not like a product description
- Mention the item name, price, and platform exactly once each, in a natural way
- Reference the overall outfit vibe in specific terms
- Be different for different inputs (achieved by using a higher LLM temperature)

**What happens if it fails or returns nothing:**
If `outfit` is empty, whitespace-only, or missing, the tool returns a descriptive fallback string such as "Couldn't generate a fit card because the outfit suggestion was missing." It does not raise an exception. If the LLM call fails due to an API error, the tool catches the exception and returns a fallback caption such as "Found [title] on [platform] for $[price] — styled with the outfit above. ✨".

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The planning loop is implemented in `run_agent(query, wardrobe)` in `agent.py`. It runs tools in a fixed but conditional sequence, checking the output of each step before deciding whether to proceed.

The exact logic is:

1. **Initialize session.** Call `_new_session(query, wardrobe)` to create a fresh session dict with keys for the query, parsed parameters, search results, selected item, wardrobe, outfit suggestion, fit card, and error.

2. **Parse the query.** Extract three values from the user's natural-language query:
   - `description` (str): the item description
   - `size` (str | None): size if mentioned
   - `max_price` (float | None): price limit if mentioned
   Store these in `session["parsed"]`.

3. **Call `search_listings(description, size, max_price)`.** Store the returned list in `session["search_results"]`.
   - **Branch A:** If `search_results` is empty, set `session["error"]` to a helpful "no matches" message and return the session immediately. Do not call `suggest_outfit` or `create_fit_card`.
   - **Branch B:** If `search_results` is not empty, set `session["selected_item"] = search_results[0]` and continue.

4. **Call `suggest_outfit(selected_item, wardrobe)`.** Store the returned string in `session["outfit_suggestion"]`.

5. **Call `create_fit_card(outfit_suggestion, selected_item)`.** Store the returned string in `session["fit_card"]`.

6. **Return the completed session.** The agent is done when either (a) an error is set early, or (b) all three tools have run successfully and the session contains `selected_item`, `outfit_suggestion`, and `fit_card`.

---

## State Management

**How does information from one tool get passed to the next?**

All state for a single user interaction is stored in one `session` dict returned by `_new_session(query, wardrobe)`. This dict is the single source of truth inside `run_agent()` and is passed between steps by reading and writing its keys.

The session dict tracks:

| Key | Initial value | Updated after step | Purpose |
|-----|---------------|--------------------|---------|
| `query` | user's raw input | never | Original request, used for context and debugging |
| `parsed` | `{}` | query parsing | Extracted `description`, `size`, `max_price` |
| `search_results` | `[]` | `search_listings` | All matching listings sorted by relevance |
| `selected_item` | `None` | search result selection | The top listing chosen for styling |
| `wardrobe` | user's wardrobe dict | never | Passed into `suggest_outfit` |
| `outfit_suggestion` | `None` | `suggest_outfit` | The outfit idea returned by the tool |
| `fit_card` | `None` | `create_fit_card` | The final shareable caption |
| `error` | `None` | any early failure | Set to a string if the interaction ends early |

Because the same session dict is used throughout `run_agent()`, each tool has access to the results of previous steps. For example, `create_fit_card` receives `outfit_suggestion` and `selected_item` directly from the session values set in earlier steps.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set `session["error"]` to: "I couldn't find anything matching that. Try broadening your search — remove the size filter, increase the price limit, or use more general keywords." Return the session early; do not call `suggest_outfit`. |
| suggest_outfit | Wardrobe is empty | Do not treat this as an error. Call the LLM with a prompt asking for general styling advice for the new item. Return the advice as `outfit_suggestion` so the flow continues to `create_fit_card`. |
| create_fit_card | Outfit input is missing or incomplete | Return a fallback string: "Couldn't generate a fit card because the outfit suggestion was missing." If the LLM API call fails, return a pre-formatted fallback caption: "Found [title] on [platform] for $[price] — styled with the outfit above. ✨" |

---

## Architecture

```
User query
    │
    ▼
Planning Loop (run_agent)
    │
    ├─► Parse query
    │       │
    │       ▼
    │   Session: parsed = {description, size, max_price}
    │       │
    ├─► search_listings(description, size, max_price)
    │       │ results = []
    │       ├──► [ERROR] "I couldn't find anything matching that..."
    │       │       │
    │       │       ▼
    │       │   Return session early
    │       │
    │       │ results = [item, ...]
    │       ▼
    │   Session: search_results = results
    │   Session: selected_item = results[0]
    │       │
    ├─► suggest_outfit(selected_item, wardrobe)
    │       │
    │       ▼
    │   Session: outfit_suggestion = "..."
    │       │
    └─► create_fit_card(outfit_suggestion, selected_item)
            │
            ▼
        Session: fit_card = "..."
            │
            ▼
        Return session
```

**How to read the diagram:** The user query enters the Planning Loop. The loop first parses the query, then calls `search_listings`. If that tool returns no results, the error branch triggers and the session is returned early. Otherwise, the top result is stored in the session, and the loop proceeds to `suggest_outfit` and then `create_fit_card`. Each tool reads from and writes to the shared session state, so data flows naturally from one step to the next.

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

- **AI tool:** Kimi Code CLI
- **Input:** The Tool 1, Tool 2, and Tool 3 sections from `planning.md`, plus the function signatures and docstrings already present in `tools.py`. I will point to the data loader helpers in `utils/data_loader.py` and the Groq client helper in `tools.py`.
- **Expected output:** Complete implementations of `search_listings()`, `suggest_outfit()`, and `create_fit_card()` in `tools.py`.
- **Verification:**
  - For `search_listings`: test with 3 queries — (1) a broad query that returns many results, (2) a query with size and price filters, (3) a query that returns no results. Confirm results are sorted by relevance and empty results are handled.
  - For `suggest_outfit`: test with the example wardrobe and with an empty wardrobe. Confirm it returns specific outfit suggestions for the populated wardrobe and general advice for the empty wardrobe.
  - For `create_fit_card`: test with a sample outfit and item. Confirm the output is 2–4 sentences, mentions the item name/price/platform naturally, and sounds like a social caption.

**Milestone 4 — Planning loop and state management:**

- **AI tool:** Kimi Code CLI
- **Input:** The Planning Loop, State Management, Error Handling, and Architecture sections from `planning.md`, plus the existing `_new_session()` and `run_agent()` stubs in `agent.py`.
- **Expected output:** A complete `run_agent()` implementation that follows the branching logic described in the Planning Loop section, and a complete `handle_query()` implementation in `app.py` that maps session results to the three Gradio output panels.
- **Verification:**
  - Run `python agent.py` and confirm both the happy path and the no-results path produce correct output.
  - Run `python app.py`, submit the example query with the example wardrobe, and confirm all three panels populate correctly.
  - Test the no-results example query in the UI and confirm the error appears only in the first panel.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**What FitFindr does:** FitFindr takes a natural-language shopping request, searches the mock secondhand listings for matching items, picks the best result, and then suggests how to wear that item with pieces from the user's wardrobe. Each tool is triggered only when the previous step produces valid output; if the search returns nothing, the agent stops and tells the user what to try instead.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query to extract `description="vintage graphic tee"`, `size=None`, and `max_price=30.0`. It calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`, which returns matching listings sorted by relevance. The agent selects the top result, for example a "Faded Band Tee" priced at $22 on Depop in good condition.

**Step 2:**
Using the selected item, the agent calls `suggest_outfit(new_item=<band tee>, wardrobe=<user's wardrobe>)`. The wardrobe includes baggy jeans and chunky sneakers, so the tool returns a specific outfit suggestion such as pairing the tee with the baggy jeans and chunky sneakers, rolled sleeves and a slight front tuck for shape.

**Step 3:**
The agent calls `create_fit_card(outfit=<suggestion>, new_item=<band tee>)`, which generates a casual, shareable caption mentioning the item name, price, and platform naturally, for example: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories."

**Final output to user:**
The user sees three panels: the top listing found (title, description, size, condition, price, platform), the outfit idea styled with their wardrobe, and the fit card caption they could share on social media. If no listings matched, the user would see only a helpful error message suggesting they broaden their search.
