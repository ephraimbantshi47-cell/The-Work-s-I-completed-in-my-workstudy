# Institutional Research Automation Toolkit

**Author:** Ephraim  
**Context:** Built during a work-study role in Institutional Research at a community college  
**Stack:** Python — ElementTree (XML), Regex, Pandas, openpyxl, HTML/CSS/JS

---

## About This Repo

This is a sanitized public version of a set of Python tools I built to automate report documentation, code-pattern analysis, and enrollment analytics for an institutional research office. All file paths, institution names, codes, and sample data in this repo are **fictional/generic** — the real versions ran against actual internal report files and student data, which aren't shared here for privacy and confidentiality reasons.

## The Problem

The office had 100+ Cognos BI reports with no central documentation, a lot of duplicated SQL logic across reports written by different people over time, and a weekly enrollment dashboard that took about 90 minutes to build by hand from five separate spreadsheets.

## What I Built

| Tool | What it does |
|---|---|
| **[Cognos Report Intelligence Dashboard](01_cognos_report_parser/)** | Recursively parses Cognos XML report files and generates a single tabbed HTML dashboard: query/field/filter/join documentation, List of Values extraction, custom function call parsing (with nested-parenthesis handling), and duplicate-logic detection |
| **[CASE Pattern Analyzer](02_case_pattern_analyzer/)** | Extracts SQL `CASE` statements from report logic and detects duplicate/reused patterns across the report library |
| **[CASE → Excel Converter](03_case_to_excel/)** | Converts SQL `CASE...WHEN...THEN` mapping logic into a clean, styled Excel lookup table for non-technical staff |
| **[Enrollment Dashboard](04_enrollment_dashboard/)** | Merges multiple weekly Excel exports into pivot-table summaries (headcount, FTE, demographics, applicant yield) |

## Impact (real numbers, generic details)

- Cut weekly report documentation from several hours to a few seconds of runtime
- Surfaced dozens of duplicate SQL logic patterns across the report library, supporting a standardization effort
- Reduced a ~90-minute manual weekly dashboard build down to a single script run

## Notes on This Repo

- All paths use placeholders like `C:\path\to\your\reports`
- All sample "institution codes," "regions," and "campuses" are fictional
- The pattern-analyzer and CASE-to-Excel tools include small demo datasets so you can run them without needing real source files
- I kept the pieces that show general-purpose skills (XML parsing, regex pattern matching, Excel generation, Pandas pipelines) — a few internal-only tools built specifically around this employer's compliance workflows aren't included here

## Skills Demonstrated

XML parsing & namespace handling · Regex pattern extraction · Data pipeline design (Pandas) · Excel automation (openpyxl) · HTML/CSS/JS for lightweight interactive dashboards · Working with real, messy institutional data

---

*Feel free to reach out if you have questions about the implementation or want to talk through the design decisions.*
