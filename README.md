# FitFindr 🛍️

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to style it with what they already own. Given a natural-language request like "vintage graphic tee under $30, size M," the agent searches a mock dataset of secondhand listings, picks the best match, suggests outfits using the user's wardrobe, generates a shareable fit card caption, and includes stretch features for price comparison, style memory, trend awareness, and search retry logic.

---
## Demo Video

[Watch the 5-minute project demo on Loom](https://www.loom.com/share/8deb5a770e56495d86c4e1ac29abb0b7)

---

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example/empty wardrobes
├── tests/
│   ├── conftest.py            # Adds project root to PYTHONPATH for pytest
│   ├── test_agent.py          # Tests for the planning loop
│   └── test_tools.py          # Tests for the three tools
├── utils/
│   ├── data_loader.py         # Helper functions for loading data
│   └── style_profile.py       # Style preference memory across sessions
├── agent.py                   # Planning loop and session management
├── app.py                     # Gradio web interface
├── planning.md                # Design spec for the agent
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your Groq API key:

```env
GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

---

## Tool Inventory

### `search_listings(description, size=None, max_price=None)`

- **Purpose:** Search the mock secondhand listings dataset and return matching items ranked by relevance.
- **Inputs:**
  - `description` (str, required): keywords describing the desired item, e.g. `"vintage graphic tee"`.
  - `size` (str | None, optional): size filter, matched as a case-insensitive substring, e.g. `"M"` matches `"S/M"`.
  - `max_price` (float | None, optional): maximum price ceiling (inclusive).
- **Output:** `list[dict]` of listing dictionaries, sorted by relevance score from highest to lowest. Returns `[]` if nothing matches.

### `suggest_outfit(new_item, wardrobe)`

- **Purpose:** Given a selected listing and the user's wardrobe, suggest 1–2 complete outfits.
- **Inputs:**
  - `new_item` (dict, required): the selected listing dict from `search_listings`.
  - `wardrobe` (dict, required): a wardrobe dict with an `items` key containing wardrobe pieces.
- **Output:** `str` with outfit suggestions. If the wardrobe is empty, returns general styling advice instead of specific combinations.

### `create_fit_card(outfit, new_item)`

- **Purpose:** Generate a short, casual, shareable outfit caption for social media.
- **Inputs:**
  - `outfit` (str, required): the outfit suggestion from `suggest_outfit`.
  - `new_item` (dict, required): the selected listing dict.
- **Output:** `str` containing a 2–4 sentence caption. Returns a fallback message if the outfit input is empty or the LLM call fails.

### `compare_price(item)` *(stretch)*

- **Purpose:** Estimate whether a selected item's price is fair by comparing it to comparable listings in the dataset.
- **Inputs:**
  - `item` (dict, required): the selected listing dict.
- **Output:** `str` verdict such as "fair price", "great deal", or "pricey", with comparable price range and average.

### `check_trends(style, size=None)` *(stretch)*

- **Purpose:** Check recent public fashion posts on Reddit for a given style and optional size.
- **Inputs:**
  - `style` (str, required): the style keyword to search for.
  - `size` (str | None, optional): size string for additional context.
- **Output:** `str` summary of recent posts, or a fallback message if the fetch fails.

---

## Planning Loop

The planning loop lives in `run_agent(query, wardrobe)` in `agent.py`. It runs tools in a fixed but conditional sequence, checking each result before deciding whether to proceed.

1. **Initialize session.** Create a fresh `session` dict that will hold every intermediate result.
2. **Parse the query.** Use regex to extract `description`, `size`, and `max_price` from the user's natural-language input.
3. **Search listings.** Call `search_listings(description, size, max_price)`.
   - If the result is an empty list, the agent sets `session["error"]` to a helpful message and returns immediately. It does **not** call `suggest_outfit` or `create_fit_card`.
   - Otherwise, it stores the top result in `session["selected_item"]` and continues.
4. **Suggest outfit.** Call `suggest_outfit(selected_item, wardrobe)` and store the result.
5. **Create fit card.** Call `create_fit_card(outfit_suggestion, selected_item)` and store the result.
6. **Return session.** The session now contains either a complete result or an early-error message.

This branching behavior is what makes it a planning loop rather than a fixed pipeline: the agent responds to the search result rather than blindly running all three tools.

---

## State Management

All state for one user interaction is stored in a single `session` dict returned by `_new_session()`:

| Key | Holds |
|-----|-------|
| `query` | Original user input |
| `parsed` | Extracted `description`, `size`, `max_price` |
| `search_results` | List of matching listings |
| `selected_item` | Top listing chosen for styling |
| `wardrobe` | User's wardrobe dict |
| `outfit_suggestion` | Result from `suggest_outfit` |
| `fit_card` | Result from `create_fit_card` |
| `error` | Set to a string if the interaction ends early |

Because the same dict is passed through `run_agent()`, each tool has access to the results of previous steps without the user re-entering anything.

---

## Error Handling

Every tool handles its own failure mode so the agent stays useful when something breaks.

| Tool | Failure mode | Agent response |
|------|--------------|----------------|
| `search_listings` | No listings match | Returns `[]`. The agent sets `session["error"]` and returns early with a message like: "I couldn't find anything matching that. Try broadening your search — remove the size filter, increase the price limit, or use more general keywords." |
| `suggest_outfit` | Wardrobe is empty | Returns general styling advice instead of specific combinations. The flow continues normally. |
| `create_fit_card` | Empty outfit string or LLM failure | Returns a fallback message string instead of raising an exception. |

### Concrete example from testing

Query: `designer ballgown size XXS under $5`

Result:

```text
error: I couldn't find anything matching that. Try broadening your search — remove the size filter, increase the price limit, or use more general keywords.
selected_item: None
outfit_suggestion: None
fit_card: None
```

The agent did not call `suggest_outfit` or `create_fit_card` because there was nothing to style.

---

## AI Usage

I used Claude Code as an implementation assistant for this project. Two specific examples:

### Instance 1: Implementing the three tools in `tools.py`

- **Input:** I gave Claude Code the Tool 1, Tool 2, and Tool 3 sections from `planning.md`, including exact inputs, return values, and failure modes. I also pointed to the existing function stubs and the data loader helpers in `utils/data_loader.py`.
- **Output:** Implementations of `search_listings()`, `suggest_outfit()`, and `create_fit_card()`.
- **What I changed/verified:** I reviewed each function against the spec, then wrote pytest tests in `tests/test_tools.py` covering normal use and each failure mode. I ran `pytest tests/` and confirmed all tests passed before moving on.

### Instance 2: Implementing the planning loop in `agent.py`

- **Input:** I gave Claude Code the Planning Loop, State Management, Error Handling, and Architecture sections from `planning.md`, plus the existing `_new_session()` and `run_agent()` stubs in `agent.py`.
- **Output:** A `run_agent()` implementation that initializes the session, parses the query, conditionally branches on search results, and wires the tools together.
- **What I changed/verified:** I checked that the generated code branched on empty search results and did not call all three tools unconditionally. I ran `python agent.py` to verify both the happy path and the no-results path, and confirmed `session["fit_card"]` stayed `None` when no listings matched.

---

## Spec Reflection

The final implementation closely matches the spec in `planning.md`. One small adjustment: I used regex-based query parsing rather than LLM-based parsing because the queries are short and structured enough for regex, making the planning loop faster and more predictable. The empty wardrobe handling in `suggest_outfit` also evolved slightly during implementation — instead of treating it as an error, the tool returns general styling advice and lets the flow continue to `create_fit_card`, which produces a better user experience.

---

## Running the Project

### Run tests

```bash
pytest tests/ -v
```

Expected: 17 tests pass.

### Run the agent from the command line

```bash
python agent.py
```

### Launch the Gradio UI

```bash
python app.py
```

Open the localhost URL shown in your terminal. Submit a query like:

```text
vintage graphic tee under $30
```

The three output panels should populate with:
1. The top listing found
2. An outfit suggestion based on the selected wardrobe
3. A shareable fit card caption

Try the no-results example query to see graceful error handling:

```text
designer ballgown size XXS under $5
```

---

## Stretch Features

In addition to the three required tools, this implementation includes four stretch features:

### 1. Price comparison

After selecting an item, the agent calls `compare_price()` to judge whether the price is fair against comparable listings in the dataset. The result appears in the listing panel.

### 2. Style profile memory

The agent loads `data/style_profile.json` at the start of each run and updates it after a successful search with the user's query and selected item styles, colors, and sizes. This allows future sessions to remember preferences.

### 3. Trend awareness

The agent calls `check_trends()` to fetch recent posts from public fashion subreddits (r/fashion, r/streetwear, r/thriftstorehauls) using Reddit's public JSON API. On networks where Reddit allows the request, it returns a short summary of relevant posts. On networks where Reddit blocks automated requests — such as many university networks — it returns a graceful fallback message instead of crashing.

### 4. Retry logic with fallback

If `search_listings()` returns no results, the agent automatically retries with loosened constraints:
1. Remove the size filter.
2. Increase `max_price` by 50%.
3. Remove size filter and increase price.

If a retry succeeds, a note appears in the listing panel explaining what was adjusted.

---

