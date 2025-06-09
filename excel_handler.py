import openpyxl
import os
from constants import EXCEL_FILE, HEADERS

def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Applications"
        ws.append(HEADERS)
        wb.save(EXCEL_FILE)

def save_to_excel(row_data):
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append(row_data)
    wb.save(EXCEL_FILE)

def delete_from_excel(values):
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active

    found = False
    for idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        def normalize(val):
            return str(val).strip().replace('\n', '').replace('\r', '')

        compare_values = [normalize(val) for val in values]
        row_values = [normalize(cell.value) for cell in row]

        compare_len = min(len(row_values), len(compare_values))
        if row_values[:compare_len] == compare_values[:compare_len]:
            ws.delete_rows(idx)
            found = True
            break

    wb.save(EXCEL_FILE)
    return found

def get_all_applications():
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    return [row for row in ws.iter_rows(min_row=2, values_only=True)]

def update_excel_row(old_values, new_values):
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active

    for row in ws.iter_rows(min_row=2):
        row_values = [cell.value if cell.value is not None else "" for cell in row]
        if row_values == [v if v is not None else "" for v in old_values]:
            for idx, val in enumerate(new_values):
                row[idx].value = val
            break
    wb.save(EXCEL_FILE)
