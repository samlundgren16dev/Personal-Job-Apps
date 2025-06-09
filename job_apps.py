import tkinter as tk
from tkinter import messagebox, ttk
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import openpyxl
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

EXCEL_FILE = "job_applications.xlsx"
HEADERS = ["Date Applied", "Job Title", "Company", "Location", "Job/Req #", "Link"]

def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Applications"
        ws.append(HEADERS)
        wb.save(EXCEL_FILE)

def parse_job_info(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        time.sleep(5)

        try:
            job_title = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            job_title = "Unknown"

        try:
            company = driver.find_element(By.XPATH, "//meta[@property='og:site_name']").get_attribute("content").strip()
        except:
            company = "Microsoft" if "microsoft" in url else "Unknown"

        location = "Unknown"
        possible_locations = driver.find_elements(By.XPATH, "//*[contains(text(), 'United States') or contains(text(), 'Remote') or contains(text(), 'California')]")
        for loc in possible_locations:
            location = loc.text.strip()
            if location:
                break

        # Try finding a job/req number (heuristic match for strings like "Req #" or IDs)
        job_req = "Unknown"
        try:
            elems = driver.find_elements(By.XPATH, "//*[contains(text(), 'Job Num') or contains(text(), 'Job Req') or contains(text(), 'Req') or contains(text(), 'Job ID') or contains(text(), 'Requisition')]")
            for elem in elems:
                text = elem.text.strip()
                if len(text) > 3:
                    job_req = text
                    break
        except:
            pass

        return {
            "Job Title": job_title,
            "Company": company,
            "Location": location,
            "Job/Req #": job_req
        }

    except Exception as e:
        print("Error parsing job info:", e)
        return None
    finally:
        driver.quit()

def add_job(url, tree):
    info = parse_job_info(url)
    if not info:
        return

    today = datetime.today().strftime('%Y-%m-%d')

    row_data = [
        today,
        info["Job Title"],
        info["Company"],
        info["Location"],
        info["Job/Req #"],
        url
    ]

    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append(row_data)
    wb.save(EXCEL_FILE)

    tree.insert('', tk.END, values=row_data)

def load_jobs(tree):
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active

    for row in ws.iter_rows(min_row=2, values_only=True):
        tree.insert('', tk.END, values=row)

def remove_selected(tree):
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a row to remove.")
        return

    # Get selected row's values
    values = tree.item(selected[0], 'values')
    link_to_remove = values[-1]  # The Link column is the last one

    # Remove from Treeview
    tree.delete(selected[0])

    # Remove from Excel based on Link column
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active

    for row in ws.iter_rows(min_row=2):
        cell_value = str(row[HEADERS.index("Link")].value).strip()
        if cell_value == link_to_remove:
            ws.delete_rows(row[0].row)
            break

    wb.save(EXCEL_FILE)

def edit_selected(tree):
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a row to edit.")
        return

    item_id = selected[0]
    values = list(tree.item(item_id, 'values'))

    edit_win = tk.Toplevel()
    edit_win.title("Edit Job Entry")

    entries = {}

    def save_changes():
        new_values = []
        for idx, col in enumerate(HEADERS):
            new_val = entries[col].get().strip()
            new_values.append(new_val if new_val else "Unknown")

        tree.item(item_id, values=new_values)

        wb = openpyxl.load_workbook(EXCEL_FILE)
        ws = wb.active
        for row in ws.iter_rows(min_row=2):
            row_values = [cell.value if cell.value is not None else "" for cell in row]
            if row_values == [v if v is not None else "" for v in values]:
                for idx, val in enumerate(new_values):
                    row[idx].value = val
                break

        wb.save(EXCEL_FILE)
        edit_win.destroy()

    for idx, col in enumerate(HEADERS):
        tk.Label(edit_win, text=col).grid(row=idx, column=0, padx=5, pady=5, sticky=tk.W)
        entry = tk.Entry(edit_win, width=50)
        entry.grid(row=idx, column=1, padx=5, pady=5)
        entry.insert(0, values[idx])
        entries[col] = entry

    tk.Button(edit_win, text="Save", command=save_changes).grid(row=len(HEADERS), column=0, columnspan=2, pady=10)

def main():
    init_excel()

    root = tk.Tk()
    root.title("Job Tracker")
    root.geometry("1100x500")

    frame_top = tk.Frame(root)
    frame_top.pack(pady=10)

    tk.Label(frame_top, text="Job Posting URL:").pack(side=tk.LEFT, padx=5)
    url_entry = tk.Entry(frame_top, width=80)
    url_entry.pack(side=tk.LEFT, padx=5)

    def on_add():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a job URL.")
            return
        add_job(url, tree)
        url_entry.delete(0, tk.END)

    tk.Button(frame_top, text="Add Job", command=on_add).pack(side=tk.LEFT)

    tree = ttk.Treeview(root, columns=HEADERS, show='headings')
    for col in HEADERS:
        tree.heading(col, text=col)
        tree.column(col, anchor=tk.W, width=200 if col not in ("Date Applied", "Job/Req #") else 120)
    tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    remove_btn = tk.Button(root, text="Remove Selected Job", command=lambda: remove_selected(tree))
    remove_btn.pack(pady=5)

    edit_btn = tk.Button(root, text="Edit Selected Job", command=lambda: edit_selected(tree))
    edit_btn.pack(pady=5)

    load_jobs(tree)

    root.mainloop()

if __name__ == "__main__":
    main()
