"""
CASE Statement Pattern Analyzer
---------------------------------
Scans a folder of Cognos/SQL report files, extracts every CASE...END
statement, and identifies duplicate logic patterns reused across the
report library.

This was built to support a code standardization effort: dozens of
reports had near-identical CASE statements written independently by
different people over time, with no way to detect the overlap. This
tool surfaces those patterns automatically so logic can be consolidated
into shared lookup tables instead of copy-pasted across reports.

Note: sample data below uses fictional categories/codes for demonstration.
In production this pointed at real Cognos report files on a shared drive.

Author: Ephraim
"""

import os
import re
import xml.etree.ElementTree as ET
from html import escape
from collections import defaultdict

# === CONFIG ===
xml_folder = r"C:\path\to\your\reports"
output_html = r"C:\path\to\output\case_analysis.html"


def clean_text(text: str) -> str:
    """Normalize smart quotes/dashes and HTML-escape the result."""
    replacements = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "--"}
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return escape(text, quote=False)


def _get_text(elem) -> str:
    if elem is None:
        return ""
    return clean_text("".join(elem.itertext()).strip())


def find_case_statements(text):
    """Extract all CASE...END blocks from a chunk of SQL/expression text."""
    return re.findall(r'\bCASE\b.*?\bEND\b', text, re.IGNORECASE | re.DOTALL)


def normalize_case_statement(case_text):
    """Strip whitespace/casing differences so identical logic can be matched."""
    return re.sub(r'\s+', ' ', case_text.strip().lower())


def collect_all_files(root_folder):
    found = []
    for dirpath, _, filenames in os.walk(root_folder):
        for fname in filenames:
            if fname.lower().endswith((".xml", ".txt")):
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, root_folder)
                found.append((abs_path, rel_path))
    return found


def analyze_reports(xml_folder):
    """Walk the report folder, extract CASE statements, and group duplicates."""
    all_cases = []
    for abs_path, rel_path in sorted(collect_all_files(xml_folder)):
        try:
            tree = ET.parse(abs_path)
            root = tree.getroot()
            ns = {'c': root.tag.split('}')[0].strip('{')}
            report_name = _get_text(root.find(".//c:reportName", ns)) or os.path.basename(abs_path)

            for q in root.findall(".//c:query", ns):
                qname = q.attrib.get("name", "Unnamed Query")
                items = [(i.attrib.get("name", ""), _get_text(i.find("c:expression", ns)))
                         for i in q.findall(".//c:dataItem", ns)]

                for field, expr in items:
                    for case in find_case_statements(expr):
                        all_cases.append({
                            'report': report_name,
                            'query': qname,
                            'field': field,
                            'case_statement': case,
                            'normalized': normalize_case_statement(case),
                            'rel_path': rel_path,
                        })
        except Exception as e:
            print(f"Error parsing {rel_path}: {e}")

    return all_cases


def build_pattern_report(all_cases, output_html):
    """Group by normalized pattern and generate an HTML report of reused logic."""
    patterns = defaultdict(list)
    for c in all_cases:
        patterns[c['normalized']].append(c)

    duplicate_patterns = {k: v for k, v in patterns.items() if len(v) > 1}
    sorted_patterns = sorted(duplicate_patterns.items(), key=lambda x: len(x[1]), reverse=True)

    pattern_html = [f"<h2>Reused Logic Patterns ({len(sorted_patterns)} found)</h2>"]
    for norm, instances in sorted_patterns:
        pattern_html.append("<div class='pattern-card'>")
        pattern_html.append(f"<b>Used {len(instances)} times across:</b><ul>")
        for inst in instances:
            pattern_html.append(f"<li>{clean_text(inst['report'])} ({clean_text(inst['query'])}) — {clean_text(inst['rel_path'])}</li>")
        pattern_html.append("</ul>")
        pattern_html.append(f"<pre>{clean_text(instances[0]['case_statement'])}</pre>")
        pattern_html.append("</div>")

    final_html = f"""
    <html><head><meta charset='UTF-8'><title>CASE Statement Pattern Analysis</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f4f7f9; color: #333; margin: 20px; }}
        h2 {{ color: #2c3e50; }}
        .pattern-card {{ background: white; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        pre {{ background: #273039; color: #e0e0e0; padding: 10px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; }}
    </style></head><body>
    {"".join(pattern_html)}
    </body></html>
    """
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"Pattern analysis written to: {output_html}")
    print(f"Total CASE statements found: {len(all_cases)}")
    print(f"Duplicate patterns found: {len(sorted_patterns)}")


# === DEMO MODE ===
# Fictional sample data (not real institutional data) showing the kind of
# CASE statement this tool was built to analyze at scale.
DEMO_CASE_TEXT = """
CASE
    WHEN [REGION] IN ('R001') THEN ('North District')
    WHEN [REGION] IN ('R002', 'R003') THEN ('South District')
    WHEN [REGION] IN ('R004') THEN ('East District')
    ELSE ('Unclassified Region')
END
"""


def run_demo():
    """Run the extractor/normalizer against fictional sample text (no folder needed)."""
    cases = find_case_statements(DEMO_CASE_TEXT)
    print(f"Found {len(cases)} CASE block(s) in demo text.")
    for c in cases:
        print(normalize_case_statement(c))


if __name__ == "__main__":
    # Swap to `analyze_reports(xml_folder)` + `build_pattern_report(...)` for real use.
    run_demo()
