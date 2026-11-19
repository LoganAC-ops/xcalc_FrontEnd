"""
Creates loan_model.xlsx - a small workbook the other examples load.

  Inputs   : principal, rate, term, start date
  Schedule : 12-month amortization table (each row depends on the row above)
  Summary  : totals, lookups, dates, IF logic
  Checks   : formulas using INDEX and TEXT, which xlcalc does NOT support -
             left in on purpose so 04_check_workbook.py has something to catch

Run:  python make_sample_workbook.py
"""
from datetime import date

import openpyxl

wb = openpyxl.Workbook()

inp = wb.active
inp.title = "Inputs"
rows = [
    ("Principal", 250000),
    ("Annual rate", 0.065),
    ("Term (years)", 30),
    ("Start date", date(2024, 1, 15)),
]
for r, (label, value) in enumerate(rows, start=1):
    inp.cell(r, 1, label)
    inp.cell(r, 2, value)
inp["B4"].number_format = "yyyy-mm-dd"

sch = wb.create_sheet("Schedule")
sch.append(["Period", "Payment", "Interest", "Principal", "Balance"])
for i in range(12):
    r = i + 2
    prev_balance = "Inputs!$B$1" if i == 0 else f"E{r - 1}"
    sch.append([
        i + 1,
        "=PMT(Inputs!$B$2/12,Inputs!$B$3*12,-Inputs!$B$1)",
        f"={prev_balance}*Inputs!$B$2/12",
        f"=B{r}-C{r}",
        f"={prev_balance}-D{r}",
    ])

summ = wb.create_sheet("Summary")
summary_rows = [
    ("Monthly payment", "=Schedule!B2"),
    ("Year-1 interest", "=SUM(Schedule!C2:C13)"),
    ("Year-1 principal", "=SUM(Schedule!D2:D13)"),
    ("Balance after 1 year", "=Schedule!E13"),
    ("Total paid over term", "=B1*Inputs!B3*12"),
    ("Total interest over term", "=B5-Inputs!B1"),
    ("Interest > principal?", '=IF(B6>Inputs!B1,"Yes","No")'),
    ("Interest in month 6", "=VLOOKUP(6,Schedule!A2:E13,3,FALSE)"),
    ("Months where interest > 1300", '=COUNTIF(Schedule!C2:C13,">1300")'),
    ("Maturity date", "=EDATE(Inputs!B4,Inputs!B3*12)"),
    ("Term in years (YEARFRAC act/act)", "=YEARFRAC(Inputs!B4,B10,1)"),
]
for r, (label, formula) in enumerate(summary_rows, start=1):
    summ.cell(r, 1, label)
    summ.cell(r, 2, formula)
summ["B10"].number_format = "yyyy-mm-dd"

chk = wb.create_sheet("Checks")
chk["A1"], chk["B1"] = "Interest in month 3 (INDEX)", "=INDEX(Schedule!C2:C13,3)"
chk["A2"], chk["B2"] = "Payment as text (TEXT)", '=TEXT(Summary!B1,"$#,##0.00")'

for ws in wb.worksheets:
    ws.column_dimensions["A"].width = 34
    for col in "BCDE":
        ws.column_dimensions[col].width = 14

wb.save("loan_model.xlsx")
print("Wrote loan_model.xlsx")
