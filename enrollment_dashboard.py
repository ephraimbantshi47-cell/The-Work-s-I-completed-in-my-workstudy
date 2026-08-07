"""
Enrollment Dashboard Aggregator
----------------------------------
Consolidates several weekly Excel exports (enrollment, sections,
applicants, FTE-by-campus) into a single set of pivot-table summaries:
headcount and FTE by student type, campus, gender, residency,
instructional method, and applicant yield.

Originally built to replace a ~90-minute weekly manual process of
opening five separate spreadsheets and rebuilding the same pivot
tables by hand for a leadership report.

Note: file paths, campus names, and column labels below are genericized
for public sharing. In production this pointed at real institutional
data exports on a shared drive.

Author: Ephraim
"""

import pandas as pd
import os

# === CONFIG ===
term = 202630  # academic term code, e.g. YYYYTT
input_dir = r"C:\path\to\weekly\reports\current_week"

# === LOAD SOURCE FILES ===
df_students = pd.read_excel(os.path.join(input_dir, "Headcount & FTE Report - Weekly.xlsx"), sheet_name="Student Detail")
df_sections = pd.read_excel(os.path.join(input_dir, "Section Enrollment.xlsx"))
df_section_detail = pd.read_excel(os.path.join(input_dir, "Section & Instructor Details.xlsx"), sheet_name="All Sections")
df_applicants = pd.read_excel(os.path.join(input_dir, "Applicants by Term - Weekly.xlsx"), sheet_name="Applicants")
df_fte_by_campus = pd.read_excel(os.path.join(input_dir, "FTE by Campus - Weekly.xlsx"), sheet_name="FTE by Campus")

# === FILTER TO CURRENT TERM ===
df_students = df_students[df_students["Term"] == term]
non_hs_students = df_students[df_students["Student Type"] != "High School Student"]

# === PIVOT TABLES ===
by_student_type = pd.pivot_table(
    df_students, values=["ID", "FTE"], index="Student Type",
    aggfunc={"ID": "count", "FTE": "sum"}
)

by_gender = pd.pivot_table(df_students, values=["ID"], index="Gender", aggfunc="count")
by_time_status = pd.pivot_table(df_students, values=["ID"], index="FT/PT Status", aggfunc="count")
by_pell = pd.pivot_table(df_students, values=["ID"], index="Pell Eligibility", aggfunc="count")
by_residency = pd.pivot_table(df_students, values=["ID"], index="Residency", aggfunc="count")
by_ethnicity = pd.pivot_table(df_students, values=["ID"], index="Ethnicity", aggfunc="count")

merged_sections = pd.merge(
    df_sections,
    df_section_detail[["Term", "CRN", "Instruction Method", "Campus", "Credit Hours"]],
    on=["Term", "CRN"], how="left"
)
merged_sections = merged_sections[merged_sections["Term"] == term]
by_instruction_method = pd.pivot_table(merged_sections, values=["ID"], index=["Instruction Method"], aggfunc="count")

df_applicants = df_applicants[df_applicants["Academic Period"] == term]

# === TOTALS: FTE & HEADCOUNT ===
total_fte = df_students["FTE"].sum()
hs_fte = df_students[df_students["Student Type"] == "High School Student"]["FTE"].sum()
non_hs_fte = total_fte - hs_fte

total_headcount = df_students["ID"].count()
hs_headcount = df_students[df_students["Student Type"] == "High School Student"]["ID"].count()
non_hs_headcount = total_headcount - hs_headcount

print("\n=== Total FTE & Headcount ===")
print(f"Non-HS/CE Student FTE: {non_hs_fte:.2f}")
print(f"HS/CE Student FTE: {hs_fte:.2f}")
print(f"Total FTE: {total_fte:.2f}")
print(f"Non-HS/CE Headcount: {non_hs_headcount}")
print(f"HS/CE Headcount: {hs_headcount}")
print(f"Total Headcount: {total_headcount}")

# === ENROLLMENT BY STUDENT TYPE ===
print("\n=== Enrollment & FTE by Student Type ===")
enrollment_by_type = df_students.pivot_table(
    index="Student Type", values=["ID", "FTE"],
    aggfunc={"ID": "count", "FTE": "sum"}
).sort_values("ID", ascending=False)
print(enrollment_by_type)

# === FTE BY CAMPUS ===
# Generic campus labels — adjust to match your institution's actual
# column layout in the source spreadsheet.
campus_cols = [
    "Campus A (Online)",
    "Campus B",
    "Campus C (Consortium)",
    "Campus D (Online - Alt)",
    "High School Programs",
    "Campus E",
    "Campus F (Main)",
    "Virtual Campus",
]

non_hs_row = df_fte_by_campus.iloc[3, 2:10].values
hs_row = df_fte_by_campus.iloc[4, 2:10].values
total_row = df_fte_by_campus.iloc[5, 2:10].values

fte_by_campus = pd.DataFrame(
    [non_hs_row, hs_row, total_row],
    index=["Non-HS Student", "HS Student", "Total"],
    columns=campus_cols,
)

print("\n=== FTE by Campus ===")
print(fte_by_campus)

# === INSTRUCTIONAL METHOD, DEMOGRAPHICS ===
print("\n=== Headcount by Instructional Method ===")
print(by_instruction_method.sort_values(by="ID", ascending=False))

print("\n=== Headcount by Gender ===")
print(by_gender["ID"])

print("\n=== FT/PT Status ===")
print(by_time_status["ID"])

print("\n=== Pell Eligibility ===")
print(by_pell["ID"])

print("\n=== Residency ===")
print(by_residency["ID"])

print("\n=== Ethnicity ===")
print(by_ethnicity["ID"])

# === APPLICANT YIELD ===
applicant_yield = pd.pivot_table(
    df_applicants, values="ID", index="Student Type",
    columns="Registered for Term?", aggfunc="count", fill_value=0
)
applicant_yield["Total"] = applicant_yield.sum(axis=1)
applicant_yield.columns.name = None
applicant_yield = applicant_yield.rename(columns={"N": "Not Registered", "Y": "Registered"})
applicant_yield = applicant_yield[["Registered", "Not Registered", "Total"]]

print("\n=== Applicant Yield ===")
print(applicant_yield)
