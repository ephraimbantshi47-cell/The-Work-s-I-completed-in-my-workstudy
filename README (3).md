# Enrollment Dashboard Aggregator

Merges several weekly Excel exports (student detail, sections, applicants,
FTE-by-campus) into pivot-table summaries: headcount/FTE by student type,
campus, gender, residency, instructional method, and applicant yield.

**Run it:**
```bash
pip install --break-system-packages pandas openpyxl
python enrollment_dashboard.py
```
Point `input_dir` at a folder containing the five source spreadsheets
(see the file names referenced near the top of the script).

**Highlights:** multi-file ingestion, term-based filtering, merge/join across
datasets, multiple pivot-table aggregations.
