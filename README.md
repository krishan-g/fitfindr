# FitFindr

![tests](https://github.com/krishan-g/fitfindr/actions/workflows/tests.yml/badge.svg)

FitFindr is an AI agent that helps users find secondhand clothing and style it. Given a natural language query, it searches a mock thrift dataset, suggests outfit combinations using the user's wardrobe, and generates a shareable fit card caption.

## What's Included

```
fitfindr/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── tools.py                   # The three agent tools
├── agent.py                   # Planning loop and session management
├── app.py                     # Gradio UI
├── tests/
│   └── test_tools.py          # pytest tests for all three tools
└── planning.md                # Spec written before implementation
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

Run the app:
```bash
python app.py
```

Run tests:
```bash
python -m pytest tests/
```

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Searches the mock listings dataset for items matching the description, optional size, and optional price ceiling.

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `str` | Keywords describing the item (e.g. `"vintage graphic tee"`) |
| `size` | `str \| None` | Size to filter by, or `None` to skip size filtering |
| `max_price` | `float \| None` | Maximum price inclusive, or `None` to skip price filtering |

**Returns:** `list[dict]` — matching listing dicts sorted by keyword relevance (best match first). Each dict has: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform`. Returns an empty list if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Given a thrifted item and the user's wardrobe, suggests 1–2 complete outfit combinations using the LLM.

| Parameter | Type | Description |
|-----------|------|-------------|
| `new_item` | `dict` | A listing dict for the item the user is considering |
| `wardrobe` | `dict` | Wardrobe dict with an `items` key containing a list of wardrobe item dicts |

**Returns:** `str` — a non-empty string with outfit suggestions. If the wardrobe is empty, returns general styling advice instead of outfit combinations.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Generates a short, casual Instagram-style caption for the thrifted outfit using the LLM.

| Parameter | Type | Description |
|-----------|------|-------------|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit()` |
| `new_item` | `dict` | The listing dict for the thrifted item |

**Returns:** `str` — a 2–4 sentence caption. If `outfit` is empty or whitespace-only, returns a descriptive error message string instead of raising an exception.

---

## Planning Loop

The agent follows a fixed sequential pipeline where each tool's output is required as input for the next. The only branching point is after `search_listings`.

1. **Parse query** — the LLM extracts `description`, `size`, and `max_price` from the user's natural language input and stores them in `session["parsed"]`.

2. **Search listings** — `search_listings()` is called with the parsed parameters. If the result is an empty list, `session["error"]` is set with a helpful message and the session is returned immediately. `suggest_outfit` is never called with empty input.

3. **Select top result** — the first result is stored in `session["selected_item"]`.

4. **Suggest outfit** — `suggest_outfit()` is called with the selected item and wardrobe. Result stored in `session["outfit_suggestion"]`.

5. **Create fit card** — `create_fit_card()` is called with the outfit suggestion and selected item. Result stored in `session["fit_card"]`.

6. **Return session** — the complete session dict is returned to the caller.

---

## State Management

All state is stored in a single `session` dict initialized by `_new_session()` at the start of each interaction. No tool receives output from a previous tool directly — the planning loop reads values out of the session and passes them as arguments to each tool call.

| Field | Set by | Used by |
|-------|--------|---------|
| `session["parsed"]` | Step 1 (LLM query parsing) | `search_listings()` |
| `session["search_results"]` | `search_listings()` | Step 3 result selection |
| `session["selected_item"]` | Step 3 (top result) | `suggest_outfit()`, `create_fit_card()` |
| `session["wardrobe"]` | Initialized from UI selection | `suggest_outfit()` |
| `session["outfit_suggestion"]` | `suggest_outfit()` | `create_fit_card()` |
| `session["fit_card"]` | `create_fit_card()` | Final output |
| `session["error"]` | Step 2 on empty results | Returned to UI instead of output fields |

---

## Interaction Walkthrough

**User query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — Tool called:** `_parse_query()` (LLM)
- Input: the raw user query
- Why: extract structured parameters from natural language before calling `search_listings`
- Output: `{"description": "vintage graphic tee", "size": null, "max_price": 30.0}`

**Step 2 — Tool called:** `search_listings`
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why: find listings matching the user's item description within their budget
- Output: list of matching listing dicts sorted by relevance; top result is `Y2K Baby Tee — Butterfly Print` ($18, depop)

**Step 3 — Tool called:** `suggest_outfit`
- Input: `new_item=<Y2K Baby Tee dict>`, `wardrobe=<example wardrobe with 10 items>`
- Why: use the found item and the user's existing wardrobe to generate specific outfit combinations
- Output: "Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a casual chic look. Layer a vintage black denim jacket for a 90s-inspired outfit."

**Step 4 — Tool called:** `create_fit_card`
- Input: `outfit=<suggestion above>`, `new_item=<Y2K Baby Tee dict>`
- Why: turn the outfit suggestion into a shareable, casual caption
- Output: "just scored the cutest y2k baby tee with a butterfly print on depop for $18 🦋 and i'm obsessed — paired it with my baggy jeans and chunky sneakers and adding my vintage denim jacket takes it to a whole new level 💖"

**Final output to user:** The top listing details appear in the first panel, the outfit suggestion in the second, and the fit card caption in the third.

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match the query | `session["error"]` is set with a message telling the user what to try differently (e.g. remove size filter, raise price limit). The session is returned immediately — `suggest_outfit` is never called with empty input. |
| `suggest_outfit` | Wardrobe is empty | The LLM is prompted for general styling advice for the item instead of specific wardrobe combinations. Always returns a non-empty string. |
| `create_fit_card` | `outfit` is empty or whitespace-only | Returns a descriptive error message string instead of raising an exception. No LLM call is made. |

**Concrete example tested:** Running `search_listings("designer ballgown", size="XXS", max_price=5)` returns `[]`. When passed through the full agent, `session["error"]` is set to `"No listings found matching your search. Try loosening your requirements — for example, remove the size filter or increase your price limit."` and both `session["fit_card"]` and `session["outfit_suggestion"]` remain `None`.

---

## Spec Reflection

**One way planning.md helped during implementation:**

Writing the state management table in planning.md — mapping each session field to what sets it and what reads it — made implementing `run_agent()` straightforward. Because I had already defined which step owned each field, there was no ambiguity about where to store results or where to read them from. The planning loop steps in planning.md translated almost directly into the numbered comments in the implementation.

**One divergence from your spec, and why:**

The spec described the wardrobe as coming from "the user's existing items (or an example wardrobe)", which was intentionally vague. In the actual implementation, the wardrobe is a fixed choice: either `get_example_wardrobe()` or `get_empty_wardrobe()`, selected by a UI radio button in `app.py`. There is no mechanism for users to describe or add their own items in the base implementation — that would require the "Style profile memory" stretch feature. The spec was written before the UI was fully understood, so this was updated once the code was explored.

---

## AI Usage

**Instance 1 — Implementing `search_listings`:**
I gave Claude the Tool 1 spec block from planning.md (inputs, return value, failure mode) along with the TODO steps from the `tools.py` stub. I asked it to implement the function using `load_listings()`. Before running the generated code, I reviewed the size filtering logic against the actual `data/listings.json` and found that a simple substring match (e.g. `"L" in "XL"`) would produce false positives. I overrode the generated logic with a tokenization approach using `re.split()` so that `"L"` only matches listings where `"L"` is its own size token, not part of `"XL"` or `"US 7"`.

**Instance 2 — Implementing `run_agent` and query parsing:**
I gave Claude the Planning Loop, State Management, and Architecture sections from planning.md along with the `agent.py` stub. I asked it to implement `run_agent()` following the numbered steps. I reviewed the generated code to confirm it branched on the empty-results case before calling `suggest_outfit`, and verified that session fields were written in the right order. I also added the `_parse_query()` helper to use the LLM for natural language parsing rather than regex, and added a markdown code-fence strip in case the LLM wrapped the JSON response in backticks. After testing, I noticed that queries like "size medium" caused no results — the LLM was returning `"medium"` as the size, which didn't match the `"M"` tokens in the listings. I updated the `_parse_query` prompt to explicitly instruct the LLM to normalize sizes to standard abbreviations (e.g. `"medium"` → `"M"`, `"large"` → `"L"`, `"size 8"` → `"US 8"`), which fixed the issue.
