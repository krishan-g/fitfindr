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
<!-- Describe what this tool does in 1–2 sentences -->
This tool searches the listings dataset (found in `data/listings.json`) for items that match the description, optional size, and optional price ceiling.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords that describe what item the user is looking for
- `size` (str): Specifies the size/dimensions, or None (which applies no filter)
- `max_price` (float): The maximum price (inclusive), or None (which applies no filter)

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
It returns a list of matching items sorted by relevance (the first item in the list is the most relevant), where each item is represented as a dictionary. Each item has the following fields: id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If no listings match or it fails, the agent should notify the user and ask for more information. It should also suggest what the user can try differently like making the requirements less strict or suggesting a different item.
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool suggests 1–2 outfits for the user, given a thrifted item and the user's wardrobe.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): An item that the user is considering
- `wardrobe` (dict): The user's wardrobe in the format of the wardrobe schema defined in `data/wardrobe_schema.json`

**What it returns:**
<!-- Describe the return value -->
It returns a non-empty string with outfit suggestions.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty or no outfit can be suggested, the agent should offer general styling advice for the item.
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool creates a short outfit caption for the thrifted find.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit string from suggest_outfit()
- `new_item` (dict): The listing dict for the thrifted item

**What it returns:**
<!-- Describe the return value -->
It returns a non-empty, 2–4 sentence string that can be used as a caption on social media.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If it fails (the output string is empty or missing), a descriptive error message should be returned instead.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

1. **Parse query:** The agent extracts `description`, `size` and `max_price` from the user's query using the LLM and stores these in `session["parsed"]`.

2. **Search listings:** Call `search_listings()` with the parsed parameters. If the result is an empty list, set `session["error"]` to a message explaining what the user can try differently and return the session (the next steps are not reached). Otherwise, the agent should select the top result and store it in `session["selected_item"]`.

3. **Suggest outfit:** Call `suggest_outfit(new_item=selected_item, wardrobe=wardrobe)` and store the output in `session["outfit_suggestion"]`. If the wardrobe is empty, FitFindr just gives general styling advice and returns.

4. **Create fit card:** Call `create_fit_card(outfit=outfit_suggestion, new_item=selected_item)` and store the result in `session["fit_card"]`.

5. **Return the session.** The loop terminates when `fit_card` is set, or when an early return is triggered by an empty search result (as in step 2).
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

All state is stored in a single `session` dict initialized at the start of each interaction by `_new_session()`. The dict tracks the following fields:

| Field | Set by | Used by |
|-------|--------|---------|
| `session["parsed"]` | Step 1 (LLM query parsing) | `search_listings()` |
| `session["search_results"]` | `search_listings()` | Step 2 result selection |
| `session["selected_item"]` | Step 2 (top result) | `suggest_outfit()`, `create_fit_card()` |
| `session["wardrobe"]` | Initialized from UI selection | `suggest_outfit()` |
| `session["outfit_suggestion"]` | `suggest_outfit()` | `create_fit_card()` |
| `session["fit_card"]` | `create_fit_card()` | Final output |
| `session["error"]` | Step 2 on empty results | Returned to UI instead of output fields |

No tool receives output from a previous tool directly — each tool reads only its own arguments, and the planning loop is responsible for pulling values out of the session and passing them in as arguments to the next tool call.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set `session["error"]` with a message telling the user no matches were found and suggesting them to loosen the requirements. Returns the session without calling subsequent tools. |
| suggest_outfit | Wardrobe is empty | Call the LLM with a prompt for general styling advice for the item rather than referencing specific wardrobe pieces. Always returns a non-empty string. |
| create_fit_card | Outfit input is empty or missing | Return a descriptive error message string instead of raising an exception. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     Use ASCII art or a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html).
     Do NOT embed an image — graders need to read your diagram directly in the file;
     an embedded image or screenshot cannot be evaluated.
     You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
User query
    │
    ▼
Planning Loop ──────────────────────────────────────────────────┐
    │                                                           │
    │  Step 1: Parse query (LLM)                                │
    │    session["parsed"] = {description, size, max_price}     │
    │                                                           │
    │  Step 2: search_listings(description, size, max_price)    │
    │       │                                                   │
    │       │ results = []                                      │
    │       ├──► session["error"] = "No matches. Try..."        │
    │       │         └──► return                               │
    │       │                                                   │
    │       │ results = [item, ...]                             │
    │       ▼                                                   │
    │   session["search_results"] = results                     │
    │   session["selected_item"]  = results[0]                  │
    │                                                           │
    │  Step 3: suggest_outfit(new_item=selected_item, wardrobe) │
    │       │                                                   │
    │       │ wardrobe["items"] = []                            │
    │       ├──► LLM returns general styling advice             │
    │       │                                                   │
    │       ▼                                                   │
    │   session["outfit_suggestion"] = "..."                    │
    │                                                           │
    │  Step 4: create_fit_card(outfit_suggestion, selected_item)│
    │       │                                                   │
    │       ▼                                                   │
    │   session["fit_card"] = "..."                             │
    │       │                                                   └──► error path returns
    │       ▼
    └──► return session
```

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

**Individual tool implementations:**
I will use Claude, giving it one tool at a time: the relevant tool block from the ## Tools section (inputs, return value, failure mode) plus the corresponding row from the ## Error Handling table, along with the TODO steps already in the `tools.py` stub. I expect it to produce a working function that filters correctly, calls the LLM where needed, and handles its failure mode without raising an exception. To verify each tool before moving on, I will run three specific test cases: (1) a query that should return results to confirm the happy path, (2) an impossible query that should return an empty list or empty string to confirm the failure mode, and (3) a filtered query (e.g. price cap or size) to confirm the filters are applied correctly. For `suggest_outfit` and `create_fit_card`, I will also check that the LLM output varies across runs to confirm temperature is set appropriately.

**Planning loop and state management:**
I will use Claude, giving it the ## Planning Loop section, the ## State Management section, the ## Architecture diagram, and the ## A Complete Interaction (Step by Step) section from this file, along with the `agent.py` stub. I expect it to produce a `run_agent()` function that initializes the session, parses the query, calls each tool in order, stores results in the correct session fields, and returns early if `search_listings` returns an empty list. To verify against the spec, I will print `session["selected_item"]` and confirm it matches the dict passed into `suggest_outfit`, print `session["outfit_suggestion"]` and confirm it matches what went into `create_fit_card`, and run the impossible query test case to confirm `session["fit_card"]` and `session["outfit_suggestion"]` remain `None` when no results are found.

---

## A Complete Interaction (Step by Step)

**Function:**
FitFindr helps users search for clothing items and gives recommendations on how they can wear them in outfits. It does this by searching the database (`search_listings()`), suggesting potential outfits containing a specific item based on the user's wardrobe (`suggest_outfit()`), and creating outfit captions for the user to share (`create_fit_card()`).

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent must search for the specified item using `search_listings("vintage graphic tee", size=None, max_price=30.0)`. This would return a list of matchings sorted by relevance, for which FitFindr will pick the top result (<top_item>).

If nothing matches (an empty list is returned), then the agent should communicate this to the user and ask for more information: it should not proceed to step 2. For instance, FitFindr can tell the user what to try differently based on the user's message or make the requirements less strict. 

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
Using the top item returned from step 1 and the user's existing items (or an example wardrobe), the agent should suggest an outfit using `suggest_outfit(new_item=<top_item>, wardrobe=<user's wardrobe>)`. This would return a non-empty string (<outfit_str>) with outfit suggestions.

**Step 3:**
<!-- Continue until the full interaction is complete -->
Finally, the agent can create an outfit caption for the thrifted find using `create_fit_card(outfit=<outfit_str>, new_item=<top_item>)`. This would return a non-empty string with the outfit caption.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The user should see a few of the top matches found in step 1 (even though the agent will only use the top match). Then, they should see the results of step 2 and 3 using the top match found. This gives the user knowledge of items matching the description as well as a suggested outfit and caption.

If no match is found in step 1, FitFindr should tell the user what to try differently, like loosening up the requirements or offering the user to search for something else based on the user's information.