# AI Bug Report Analyzer (LangGraph + Gemini)

Turns a natural-language bug description into a structured bug report.

```
START -> bug_analysis -> severity_detection -> root_cause -> format_report -> END
```

| Node | Job | Writes to state |
|------|-----|-----------------|
| `bug_analysis` | Extract title, affected feature, summary | `title`, `affected_feature`, `summary` |
| `severity_detection` | Classify Critical / High / Medium / Low | `severity`, `severity_reason` |
| `root_cause` | Suggest possible causes | `root_causes` |
| `format_report` | Build the final readable report | `final_report` |

## Setup

1. Get a free API key from https://aistudio.google.com/apikey
2. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in this folder:
   ```
   GOOGLE_API_KEY=your_key_here
   ```
4. Run the command-line version:
   ```bash
   python bug_analyzer.py
   ```
   or the web UI:
   ```bash
   python app.py
   ```
   then open http://127.0.0.1:5000

## Web UI

A Streamlit interface is included. It shows the four pipeline steps ticking off live
as each LangGraph node finishes, then renders the report as a severity-coloured ticket
with a Markdown download.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Your API key can come from `.env` or be pasted into the sidebar. The command-line
version (`python bug_analyzer.py`) still works.

Optional: set `GEMINI_MODEL` in `.env` to use a different Gemini model (default: `gemini-3.8-flash`). Google retires older models for new users, so if you get a 404 `NOT_FOUND`, check the current model name in the error message or at https://ai.google.dev/gemini-api/docs/models.

## Example

**Input**
```
When I click "Pay Now" on the checkout page with a saved card, the page
freezes and I get charged twice. Happens on Chrome and Safari for every order.
```

**Output (approximate)**
```
============================================================
BUG REPORT
============================================================

Title:             Checkout freezes and double-charges on Pay Now
Affected Feature:  Checkout / Payment processing
Severity:          CRITICAL

Summary:
  Clicking "Pay Now" with a saved card freezes the page and charges
  the customer twice, reproducibly across browsers.

Severity Rationale:
  Customers are financially harmed on every order, with no workaround.

Possible Root Causes:
  1. Missing idempotency key, so retried payment requests create duplicate charges
  2. Submit button not disabled after first click, allowing repeated submissions
  3. Frontend blocks on an unresolved promise/timeout from the payment API
  4. Payment webhook and client callback both finalizing the same order

============================================================
```

## Design notes

- **Structured output**: each LLM node uses `with_structured_output` with a Pydantic
  model, so Gemini returns validated fields instead of free text that needs parsing.
  Severity is a `Literal`, so it can only be one of the four allowed values.
- **Shared state**: `BugState` is a `TypedDict`; each node returns only the keys it
  updates and LangGraph merges them.
- **Node 4 uses no LLM**: formatting is deterministic, so it's plain Python. This is
  faster, free, and can't hallucinate.

## Web UI

```
bug_analyzer/
  app.py            Flask server (POST /api/analyze streams one JSON line per node)
  bug_analyzer.py   LangGraph pipeline
  static/
    index.html  style.css  script.js
```

The progress bar above the report advances as each LangGraph node finishes, because the server streams the graph's `updates` as they happen.