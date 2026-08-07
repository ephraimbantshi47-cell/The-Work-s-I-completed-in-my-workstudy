"""
Cognos Report Intelligence Dashboard
---------------------------------------
The most feature-complete tool in this toolkit. Recursively parses a folder
of Cognos XML report files and builds a single tabbed HTML dashboard with:

  - Full documentation of every report's queries, fields, filters, and joins
  - Extraction of every "List of Values" (LOV) reference and its full path
  - Extraction of every custom function call (e.g. F_GET_*, F_CALC_*),
    using paren-depth tracking so nested function calls are captured
    correctly instead of cutting off at the first closing parenthesis
  - Detection of duplicate CASE-statement logic reused across reports
  - A configurable field-reference finder (e.g. "show me every report
    that references FIELD_X") for data lineage / impact-analysis work
  - One tab per individual report, plus a live search box scoped to
    whichever tab is active

This was the "everything" version I built after the simpler single-purpose
parsers, once I needed to answer questions like "which reports call this
custom function?" or "if I change this field, what breaks?"

Note: file paths and the demo field name below are genericized for public
sharing. In production this pointed at a real internal report library.

Author: Ephraim
"""

import xml.etree.ElementTree as ET
import os
import re
from html import escape
from collections import defaultdict, Counter

# === CONFIG ===
xml_folder = r"C:\path\to\your\cognos\reports"
output_html = r"C:\path\to\output\report_dashboard.html"

# Field to look up across all reports — swap this to whatever field you're
# investigating (e.g. tracing where a specific data element is used).
FIELD_TO_TRACE = "ENROLLMENT_STATUS"


def clean_text(text: str) -> str:
    """Normalize smart quotes/dashes for cleaner HTML display."""
    replacements = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "--"}
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text


def _get_text(elem) -> str:
    if elem is None:
        return ""
    return escape(clean_text("".join(elem.itertext()).strip()))


def _raw_text(elem) -> str:
    if elem is None:
        return ""
    return clean_text("".join(elem.itertext()).strip())


def find_all_filters(q, ns):
    filters = []
    for tag in ["detailFilter", "summaryFilter", "groupFilter"]:
        filters.extend(q.findall(f".//c:{tag}", ns))
    if q.find("c:filterExpression", ns) is not None:
        filters.append(q.find("c:filterExpression", ns))
    seen, unique = set(), []
    for f in filters:
        expr = _get_text(f.find("c:filterExpression", ns) if f.tag.endswith("Filter") else f)
        if expr not in seen:
            seen.add(expr)
            unique.append(f)
    return unique


# ============================================================
# List of Values (LOV) extraction
# ============================================================

def extract_lov_paths(expr_text):
    """Pull every [List of Values].[...] reference chain out of an expression."""
    pattern = r'\[List of Values\](?:\.\[[^\]]*\])+'
    matches = re.findall(pattern, expr_text)
    return list(dict.fromkeys(matches))


def collect_lov_for_query(q, ns):
    mentions = []
    for item in q.findall(".//c:dataItem", ns):
        field_name = item.attrib.get("name", "")
        expr_elem = item.find("c:expression", ns)
        if expr_elem is not None:
            expr_text = "".join(expr_elem.itertext()).strip()
            if "[List of Values].[" in expr_text:
                mentions.append({
                    "location": f"Field: {field_name}",
                    "expression": expr_text,
                    "paths": extract_lov_paths(expr_text),
                })
    for tag in ["detailFilter", "summaryFilter", "groupFilter", "filterExpression"]:
        for f in q.findall(f".//c:{tag}", ns):
            expr_elem = f.find("c:filterExpression", ns) if f.tag.endswith("Filter") else f
            if expr_elem is not None:
                expr_text = "".join(expr_elem.itertext()).strip()
                if "[List of Values].[" in expr_text:
                    mentions.append({
                        "location": "Filter",
                        "expression": expr_text,
                        "paths": extract_lov_paths(expr_text),
                    })
    return mentions


def build_lov_summary(all_mentions):
    html = ["<div class='section-box lov-box'>", "<h2>List of Values References</h2>"]
    if not all_mentions:
        html.append("<p>No List of Values references found in any report.</p>")
    else:
        html.append(f"<p><b>{len(all_mentions)}</b> reference(s) found across all reports.</p>")
        html.append("<table><tr><th>Report</th><th>Query</th><th>Location</th><th>Path(s)</th><th>Expression</th></tr>")
        for m in all_mentions:
            paths_html = "<br>".join(f"<code>{escape(p)}</code>" for p in m["paths"]) or "<em>none extracted</em>"
            html.append(
                f"<tr><td>{escape(m['report'])}</td><td>{escape(m['query'])}</td>"
                f"<td>{escape(m['location'])}</td><td>{paths_html}</td>"
                f"<td><pre>{escape(m['expression'])}</pre></td></tr>"
            )
        html.append("</table>")
    html.append("</div>")
    return "\n".join(html)


# ============================================================
# Custom function call extraction (F_GET_* / F_CALC_*)
# with paren-depth tracking for correct nested-call handling
# ============================================================

FUNC_PATTERN = re.compile(r'\b(F_(?:GET|CALC)_\w+)\s*\(', re.IGNORECASE)


def extract_function_calls(expr_text):
    """
    Find every F_GET_xxx(...) / F_CALC_xxx(...) call, correctly matching the
    closing parenthesis even when the call contains nested function calls
    or nested parentheses inside its arguments.
    """
    results = []
    for m in FUNC_PATTERN.finditer(expr_text):
        start = m.start()
        paren_start = expr_text.index('(', start)
        depth = 0
        end = paren_start
        for i in range(paren_start, len(expr_text)):
            if expr_text[i] == '(':
                depth += 1
            elif expr_text[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        results.append(expr_text[start:end + 1])
    return results


def collect_functions_for_report(xml_path, ns, rel_path=""):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    mentions = []
    report_name_elem = root.find(".//c:reportName", ns)
    report_name = _raw_text(report_name_elem) or os.path.basename(xml_path)

    for q in root.findall(".//c:query", ns):
        qname = q.attrib.get("name", "Unnamed Query")
        for item in q.findall(".//c:dataItem", ns):
            field_name = item.attrib.get("name", "")
            expr_elem = item.find("c:expression", ns)
            if expr_elem is not None:
                raw = _raw_text(expr_elem)
                calls = extract_function_calls(raw)
                if calls:
                    mentions.append({"report": report_name, "query": qname, "location": f"Field: {field_name}",
                                      "expression": raw, "calls": calls, "rel_path": rel_path})
        for tag in ["detailFilter", "summaryFilter", "groupFilter", "filterExpression"]:
            for f in q.findall(f".//c:{tag}", ns):
                expr_elem = f.find("c:filterExpression", ns) if f.tag.endswith("Filter") else f
                if expr_elem is not None:
                    raw = _raw_text(expr_elem)
                    calls = extract_function_calls(raw)
                    if calls:
                        mentions.append({"report": report_name, "query": qname, "location": "Filter",
                                          "expression": raw, "calls": calls, "rel_path": rel_path})
    return mentions


def build_function_summary(all_mentions):
    html = ["<div class='section-box func-box'>", "<h2>Custom Function Call Summary (F_GET / F_CALC)</h2>"]
    if not all_mentions:
        html.append("<p>No F_GET / F_CALC function references found in any report.</p>")
    else:
        seen, deduped = set(), []
        for m in all_mentions:
            key = (m["report"], m["query"], m["location"], m["expression"])
            if key not in seen:
                seen.add(key)
                deduped.append(m)

        all_func_names = [c.split('(')[0].strip().upper() for m in deduped for c in m["calls"]]
        func_counts = Counter(all_func_names).most_common()

        html.append(f"<p><b>{len(deduped)}</b> expression(s) containing custom function calls.</p>")
        html.append("<h3>Function Frequency</h3><table style='width:auto;'><tr><th>Function</th><th>Count</th></tr>")
        for fname, count in func_counts:
            html.append(f"<tr><td><code>{escape(fname)}</code></td><td>{count}</td></tr>")
        html.append("</table>")

        html.append("<h3>Full Detail</h3><table><tr><th>Report</th><th>Query</th><th>Location</th><th>Call(s)</th><th>Expression</th></tr>")
        for m in deduped:
            calls_html = "<br><br>".join(f"<code>{escape(c)}</code>" for c in m["calls"])
            html.append(
                f"<tr><td>{escape(m['report'])}</td><td>{escape(m['query'])}</td>"
                f"<td>{escape(m['location'])}</td><td>{calls_html}</td>"
                f"<td><pre>{escape(m['expression'])}</pre></td></tr>"
            )
        html.append("</table>")
    html.append("</div>")
    return "\n".join(html)


# ============================================================
# CASE statement extraction, field tracing, and pattern reuse
# ============================================================

def find_case_statements(text):
    return re.findall(r'\bCASE\b.*?\bEND\b', text, re.IGNORECASE | re.DOTALL)


def normalize_case_statement(case_text):
    return re.sub(r'\s+', ' ', case_text.strip().lower())


def contains_field_reference(text, field_name):
    """Whole-word match so 'STATUS' doesn't false-positive inside 'SUBSTATUS'."""
    pattern = rf'(?:^|[\s\[\(\_\.\,\<\>])({re.escape(field_name)})(?=[\s\]\)\_\.\,\<\>\=]|$)'
    return bool(re.search(pattern, text, re.IGNORECASE))


def collect_case_analysis(xml_path, ns, rel_path, field_name):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    report_name = _raw_text(root.find(".//c:reportName", ns)) or os.path.basename(xml_path)
    all_cases = []

    for q in root.findall(".//c:query", ns):
        qname = q.attrib.get("name", "Unnamed Query")
        for item in q.findall(".//c:dataItem", ns):
            fname = item.attrib.get("name", "")
            expr_elem = item.find("c:expression", ns)
            if expr_elem is not None:
                expr = _raw_text(expr_elem)
                for case in find_case_statements(expr):
                    all_cases.append({
                        'report': report_name, 'query': qname, 'field': fname, 'type': 'DataItem',
                        'case_statement': case, 'normalized': normalize_case_statement(case),
                        'contains_field': contains_field_reference(case, field_name), 'rel_path': rel_path,
                    })
        for tag in ["detailFilter", "summaryFilter", "groupFilter"]:
            for f in q.findall(f".//c:{tag}", ns):
                expr_elem = f.find("c:filterExpression", ns)
                if expr_elem is not None:
                    expr = _raw_text(expr_elem)
                    for case in find_case_statements(expr):
                        all_cases.append({
                            'report': report_name, 'query': qname, 'field': tag, 'type': 'Filter',
                            'case_statement': case, 'normalized': normalize_case_statement(case),
                            'contains_field': contains_field_reference(case, field_name), 'rel_path': rel_path,
                        })
    return all_cases


def build_field_trace_analysis(all_cases, field_name):
    html = ["<div class='section-box trace-box'>", f"<h2>Field Reference Trace: '{escape(field_name)}'</h2>"]
    matches = [c for c in all_cases if c['contains_field']]
    if not matches:
        html.append(f"<p>No CASE statements referencing '<b>{escape(field_name)}</b>' found.</p>")
    else:
        html.append(f"<p>Found <b>{len(matches)}</b> CASE statement(s) referencing '<b>{escape(field_name)}</b>'.</p>")
        html.append("<table><tr><th>Report</th><th>Query</th><th>Field/Filter</th><th>File</th><th>CASE Statement</th></tr>")
        for c in matches:
            html.append(
                f"<tr><td>{escape(c['report'])}</td><td>{escape(c['query'])}</td>"
                f"<td>{escape(c['field'])}</td><td class='file-path'>{escape(c['rel_path'])}</td>"
                f"<td><pre>{escape(c['case_statement'])}</pre></td></tr>"
            )
        html.append("</table>")
    html.append("</div>")
    return "\n".join(html)


def build_pattern_reuse_analysis(all_cases):
    html = ["<div class='section-box pattern-box'>", "<h2>Logic Reuse Analysis</h2>"]
    if not all_cases:
        html.append("<p>No CASE statements found to analyze.</p>")
    else:
        patterns = defaultdict(list)
        for c in all_cases:
            patterns[c['normalized']].append(c)
        reused = sorted([(k, v) for k, v in patterns.items() if len(v) > 1], key=lambda x: len(x[1]), reverse=True)

        if not reused:
            html.append("<p>No duplicate CASE statement logic found.</p>")
        else:
            html.append(f"<p>Found <b>{len(reused)}</b> pattern(s) reused across multiple reports.</p>")
            for norm, instances in reused:
                html.append("<div class='pattern-card'>")
                html.append(f"<h4>Used {len(instances)} times:</h4>")
                html.append(f"<pre>{escape(instances[0]['case_statement'])}</pre>")
                html.append("<p><b>Used in:</b></p><ul>")
                for inst in instances:
                    html.append(f"<li>{escape(inst['report'])} → {escape(inst['query'])} "
                                f"<span class='file-path'>({escape(inst['rel_path'])})</span></li>")
                html.append("</ul></div>")
    html.append("</div>")
    return "\n".join(html)


# ============================================================
# Full per-report detail + join operations (existing base parser)
# ============================================================

def parse_single_report(xml_path, rel_path, ns):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    html = []
    report_name = _get_text(root.find(".//c:reportName", ns)) or os.path.basename(xml_path)
    html.append(f"<h2>{report_name}</h2><p class='file-path'>{escape(rel_path)}</p>")

    for q in root.findall(".//c:query", ns):
        qname = q.attrib.get("name", "Unnamed Query")
        html.append(f"<h3>Query: {escape(qname)}</h3>")

        meta_elem = q.find(".//c:metadataPath", ns)
        if meta_elem is not None:
            html.append(f"<p><b>Source:</b> <code>{escape(meta_elem.attrib.get('path', ''))}</code></p>")

        html.append('<div class="query-block"><div class="field-table"><table><tr><th>Field</th><th>Expression</th></tr>')
        for i in q.findall(".//c:dataItem", ns):
            html.append(f"<tr><td>{escape(i.attrib.get('name',''))}</td><td><pre>{_get_text(i.find('c:expression', ns))}</pre></td></tr>")
        html.append("</table></div>")

        q_filters = find_all_filters(q, ns)
        html.append(f"<div class='filter-box'><h4>Filters ({len(q_filters)})</h4>")
        if q_filters:
            html.append("<ul>")
            for f in q_filters:
                expr = _get_text(f.find("c:filterExpression", ns) if f.tag.endswith("Filter") else f)
                html.append(f"<li><pre>{expr}</pre></li>")
            html.append("</ul>")
        else:
            html.append("<p>No filters found.</p>")
        html.append("</div></div>")

        join_ops = q.findall(".//c:joinOperation", ns)
        if join_ops:
            html.append(f"<div class='join-section'><h4>Join Operations ({len(join_ops)})</h4>")
            for join_op in join_ops:
                html.append("<div class='join-item'>")
                html.append(f"<p><b>Type:</b> {escape(join_op.attrib.get('type', 'unknown'))}</p>")
                cardinality = join_op.attrib.get("cardinality", "")
                if cardinality:
                    html.append(f"<p><b>Cardinality:</b> {escape(cardinality)}</p>")
                operands = join_op.findall(".//c:joinOperand", ns)
                if operands:
                    html.append("<p><b>Joined Queries:</b></p><ul>")
                    for op in operands:
                        ref = op.find("c:queryRef", ns)
                        if ref is not None:
                            html.append(f"<li>{escape(ref.attrib.get('refQuery', 'unknown'))}</li>")
                    html.append("</ul>")
                html.append("</div>")
            html.append("</div>")

        lov_mentions = collect_lov_for_query(q, ns)
        if lov_mentions:
            html.append("<div class='lov-section'><h4>List of Values References</h4>")
            for m in lov_mentions:
                html.append(f"<div class='lov-item'><p><b>{escape(m['location'])}</b></p>")
                for p in m['paths']:
                    html.append(f"<code>{escape(p)}</code><br>")
                html.append("</div>")
            html.append("</div>")

    return "\n".join(html)


def collect_all_files(root_folder):
    found = []
    for dirpath, _, filenames in os.walk(root_folder):
        for fname in filenames:
            if fname.lower().endswith((".xml", ".txt")):
                abs_path = os.path.join(dirpath, fname)
                found.append((abs_path, os.path.relpath(abs_path, root_folder)))
    return found


# ============================================================
# Main orchestrator: builds the full tabbed dashboard
# ============================================================

def build_dashboard(xml_folder, output_html, field_to_trace=FIELD_TO_TRACE):
    all_files = collect_all_files(xml_folder)

    reports, all_lov, all_funcs, all_cases, tabs = [], [], [], [], []

    for abs_path, rel_path in sorted(all_files):
        try:
            tree = ET.parse(abs_path)
            root = tree.getroot()
            ns = {'c': root.tag.split('}')[0].strip('{')}
            report_name = _raw_text(root.find(".//c:reportName", ns)) or os.path.basename(abs_path)

            tab_id = f"tab_{len(tabs)}"
            content = parse_single_report(abs_path, rel_path, ns)
            all_lov.extend([{**m, "report": report_name, "query": q.attrib.get("name", "")}
                            for q in root.findall(".//c:query", ns) for m in collect_lov_for_query(q, ns)])
            all_funcs.extend(collect_functions_for_report(abs_path, ns, rel_path))
            all_cases.extend(collect_case_analysis(abs_path, ns, rel_path, field_to_trace))

            tabs.append({"tab_id": tab_id, "label": report_name, "content": content})
            print(f"Parsed: {rel_path}")
        except Exception as e:
            print(f"Error parsing {rel_path}: {e}")

    tab_buttons = [
        '<button class="tab-btn active" onclick="showTab(\'tab_lov\', this)">List of Values</button>',
        f'<button class="tab-btn" onclick="showTab(\'tab_trace\', this)">Field Trace: {escape(field_to_trace)}</button>',
        '<button class="tab-btn" onclick="showTab(\'tab_patterns\', this)">Logic Patterns</button>',
        '<button class="tab-btn" onclick="showTab(\'tab_funcs\', this)">Function Calls</button>',
    ]
    tab_buttons += [f'<button class="tab-btn" onclick="showTab(\'{t["tab_id"]}\', this)">{escape(t["label"])}</button>' for t in tabs]

    tab_panels = [
        f'<div id="tab_lov" class="tab-panel active">{build_lov_summary(all_lov)}</div>',
        f'<div id="tab_trace" class="tab-panel">{build_field_trace_analysis(all_cases, field_to_trace)}</div>',
        f'<div id="tab_patterns" class="tab-panel">{build_pattern_reuse_analysis(all_cases)}</div>',
        f'<div id="tab_funcs" class="tab-panel">{build_function_summary(all_funcs)}</div>',
    ]
    tab_panels += [f'<div id="{t["tab_id"]}" class="tab-panel">{t["content"]}</div>' for t in tabs]

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Cognos Report Dashboard</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; background: #f0f2f5; color: #333; }}
.top-bar {{ background: #1e3799; color: white; padding: 16px 24px; font-size: 1.4em; font-weight: bold; }}
.search-bar {{ background: #fff; padding: 10px 24px; border-bottom: 1px solid #ddd; }}
.search-bar input {{ width: 400px; padding: 8px 12px; font-size: 14px; border: 1px solid #ccc; border-radius: 6px; }}
.tab-bar {{ background: #fff; border-bottom: 2px solid #2980b9; padding: 8px 16px 0; display: flex; flex-wrap: wrap; gap: 4px; position: sticky; top: 0; z-index: 100; }}
.tab-btn {{ padding: 8px 16px; border: 1px solid #ccc; border-bottom: none; background: #f0f2f5; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 13px; }}
.tab-btn.active {{ background: #2980b9; color: white; }}
.tab-panel {{ display: none; padding: 24px; }}
.tab-panel.active {{ display: block; }}
.section-box {{ background: white; border-radius: 10px; padding: 20px; }}
h2 {{ color: #34495e; border-bottom: 2px solid #95a5a6; padding-bottom: 5px; }}
h3 {{ color: #2c3e50; margin-top: 30px; }}
.query-block {{ display: flex; gap: 20px; margin-bottom: 30px; }}
.field-table {{ flex: 2; }}
.filter-box {{ flex: 1; background: #ecf0f1; padding: 15px; border-radius: 8px; }}
.join-section {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 15px 0; }}
.join-item {{ background: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
.lov-section {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; }}
.lov-item {{ background: white; padding: 10px; border-radius: 5px; border-left: 4px solid #1e88e5; margin-bottom: 10px; }}
.pattern-card {{ background: #fafafa; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #ff9800; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background-color: #2980b9; color: white; }}
pre {{ white-space: pre-wrap; word-wrap: break-word; background: #273039; color: #e0e0e0; padding: 8px; border-radius: 4px; font-size: 0.88em; }}
code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }}
.file-path {{ color: #7f8c8d; font-size: 0.85em; }}
.highlight {{ background-color: yellow; }}
</style>
<script>
function showTab(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
function highlight() {{
  const input = document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('.highlight').forEach(el => el.outerHTML = el.innerHTML);
  if (!input) return;
  const panel = document.querySelector('.tab-panel.active');
  const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT, null, false);
  const nodes = [];
  while (walker.nextNode()) if (walker.currentNode.nodeValue.toLowerCase().includes(input)) nodes.push(walker.currentNode);
  nodes.forEach(node => {{
    const span = document.createElement('span');
    span.innerHTML = node.nodeValue.replace(new RegExp(input, 'gi'), m => `<span class="highlight">${{m}}</span>`);
    node.replaceWith(span);
  }});
}}
</script></head><body>
<div class="top-bar">Cognos Report Dashboard</div>
<div class="search-bar"><input id="searchInput" onkeyup="highlight()" placeholder="Search current tab..."></div>
<div class="tab-bar">{''.join(tab_buttons)}</div>
{''.join(tab_panels)}
</body></html>"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDashboard written to: {output_html}")


if __name__ == "__main__":
    build_dashboard(xml_folder, output_html, field_to_trace=FIELD_TO_TRACE)
