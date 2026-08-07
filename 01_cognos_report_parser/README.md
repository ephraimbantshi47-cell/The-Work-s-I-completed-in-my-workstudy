# Cognos Report Intelligence Dashboard

The most feature-complete tool in this toolkit. Recursively parses a folder of
Cognos XML report files and builds a single tabbed HTML dashboard combining
several kinds of analysis in one place.

## What it does

- **Full report documentation** — every query, field, filter, and join operation
- **List of Values (LOV) extraction** — finds every `[List of Values].[...]`
  reference and its full path across the entire report library
- **Custom function call extraction** — finds every `F_GET_*` / `F_CALC_*` call,
  using paren-depth tracking so nested function calls are captured correctly
  (a naive regex would grab the wrong closing parenthesis)
- **Duplicate logic detection** — normalizes and groups `CASE` statements to
  surface logic that's been reused (or copy-pasted) across multiple reports
- **Field reference tracing** — configurable lookup showing every report that
  references a given field, useful for impact analysis before making a change
- **Per-report tabs** — every report also gets its own dedicated tab
- **Scoped live search** — search box only highlights matches in the active tab

## Why I built it

The earlier, simpler parsers in this repo each solved one problem at a time.
This version came out of needing to answer more complex questions in practice —
"which reports call this custom function?" or "if I change this field, what
else breaks?" — which meant combining several kinds of static analysis into
one tool instead of running four separate scripts.

## Run it

```bash
python cognos_report_dashboard.py
```

Update `xml_folder`, `output_html`, and `FIELD_TO_TRACE` at the top of the
script first. `FIELD_TO_TRACE` controls the "Field Trace" tab — set it to
whatever field you're investigating.

## Technical highlights

- **Paren-depth tracking** for function call extraction — walks character by
  character, incrementing/decrementing a depth counter, so `F_CALC(F_GET(x), y)`
  is captured as one complete call instead of stopping at the first `)`
- Namespace-aware XML parsing across differing Cognos report versions
- Pattern normalization (whitespace/casing collapse) for duplicate detection
- Single-page tabbed UI with vanilla JS (no frameworks) — search scoped to
  the currently active tab only, to keep results relevant
