# CASE Statement Pattern Analyzer

Extracts SQL `CASE...END` blocks from report expressions and detects logic
that's been duplicated across multiple reports, to support standardizing
repeated business logic into shared lookup tables.

**Run the demo (no real files needed):**
```bash
python case_pattern_analyzer.py
```
For real use, point `xml_folder` at a folder of report files and call
`analyze_reports()` + `build_pattern_report()` from `__main__` instead of `run_demo()`.

**Highlights:** regex extraction across multi-line SQL, text normalization
for duplicate detection, pattern frequency ranking.
