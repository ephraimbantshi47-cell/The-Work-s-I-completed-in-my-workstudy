# CASE Statement to Excel Converter

Parses SQL `CASE...WHEN...THEN` mapping logic and converts it into a
styled, readable Excel lookup table — useful for handing technical
mapping logic to non-technical stakeholders.

**Run it:**
```bash
pip install --break-system-packages openpyxl
python case_to_excel_converter.py
```
Edit the `case_input` string at the top to paste in your own CASE statement.

**Highlights:** regex parsing of IN-clause and equality CASE patterns,
styled Excel generation with openpyxl (headers, alternating rows, frozen panes).
