import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkFont
import webbrowser
from datetime import datetime
from constants import *
from excel_handler import *
from job_parser import parse_job_info

class JobTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.setup_gui()
        self.last_deleted_row = None
        self.last_edited_row = None
        self.last_edited_item_id = None

    def setup_gui(self):
        self.root.title("Job Tracker")
        self.root.configure(bg=PRIMARY_BG)
        self.root.minsize(1000, 600)
        self.root.geometry("1200x700")

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview",
                            background="#ecf0f1",
                            foreground="black",
                            rowheight=25,
                            fieldbackground="#ecf0f1")
        self.style.map("Treeview",
                      background=[('selected', '#3498db')],
                      foreground=[('selected', 'white')])

    def create_widgets(self):
        self.create_url_entry_frame()
        self.create_search_frame()
        self.create_treeview_frame()
        self.create_control_buttons_frame()
        self.create_info_frame()

        self.refresh_treeview()

    def create_url_entry_frame(self):
        frame_top = tk.Frame(self.root, bg=SECONDARY_BG)
        frame_top.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(frame_top, text="Job Posting URL:", bg=SECONDARY_BG, fg=TEXT_COLOR,
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        self.url_entry = tk.Entry(frame_top, width=60, font=('Arial', 10))
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.url_entry.bind("<Return>", lambda event: self.add_job_from_ui())

        tk.Button(frame_top, text="Add Job", bg=BUTTON_BG, fg=BUTTON_FG,
                font=('Arial', 10, 'bold'), command=self.add_job_from_ui).pack(side=tk.RIGHT, padx=5)

    def create_search_frame(self):
        frame_search = tk.Frame(self.root, bg=SECONDARY_BG)
        frame_search.pack(pady=5, fill=tk.X, padx=10)

        self.search_var = tk.StringVar()
        tk.Label(frame_search, text="Search:", bg=SECONDARY_BG, fg=TEXT_COLOR,
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        search_entry = tk.Entry(frame_search, textvariable=self.search_var, width=40, font=('Arial', 10))
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        search_entry.bind("<Return>", self.do_search)

        search_btn_frame = tk.Frame(frame_search, bg=SECONDARY_BG)
        search_btn_frame.pack(side=tk.RIGHT, padx=5)

        tk.Button(search_btn_frame, text="Search", bg=BUTTON_BG, fg=BUTTON_FG,
                 font=('Arial', 9), command=self.do_search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_btn_frame, text="Clear", bg=BUTTON_BG, fg=BUTTON_FG,
                 font=('Arial', 9), command=self.clear_search).pack(side=tk.LEFT, padx=2)

    def create_treeview_frame(self):
        tree_frame = tk.Frame(self.root, bg=PRIMARY_BG)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=(10, 5))

        self.tree = ttk.Treeview(tree_frame, columns=HEADERS, show='headings')
        self.treeview_sort_column(self.tree, "Date Applied", True)

        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        for col in HEADERS:
            self.tree.heading(col, text=col, command=lambda c=col: self.treeview_sort_column(self.tree, c, False))
            self.tree.column(col, anchor=tk.W, width=200)

        self.tree.bind("<Double-1>", lambda event: self.show_row_details())
        self.tree.bind("<Delete>", lambda event: self.remove_selected())

    def create_control_buttons_frame(self):
        main_btn_frame = tk.Frame(self.root, bg=PRIMARY_BG)
        main_btn_frame.pack(pady=(5, 10), padx=10, fill=tk.X)

        # Primary action buttons
        primary_frame = tk.Frame(main_btn_frame, bg=PRIMARY_BG)
        primary_frame.pack(fill=tk.X, pady=2)

        tk.Button(primary_frame, text="Remove Selected Job", bg="#e74c3c", fg="white",
                 font=('Arial', 10, 'bold'), width=18,
                 command=self.remove_selected).pack(side=tk.LEFT, padx=5)

        tk.Button(primary_frame, text="Edit Selected Job", bg=BUTTON_BG, fg=BUTTON_FG,
                 font=('Arial', 10, 'bold'), width=18,
                 command=self.edit_selected).pack(side=tk.LEFT, padx=5)

        # Delete action buttons
        delete_frame = tk.Frame(main_btn_frame, bg=PRIMARY_BG)
        delete_frame.pack(fill=tk.X, pady=1)

        tk.Label(delete_frame, text="Delete Actions:", bg=PRIMARY_BG, fg=TEXT_COLOR,
                font=('Arial', 9, 'italic')).pack(side=tk.LEFT, padx=5)

        self.undo_btn = tk.Button(delete_frame, text="Undo Delete", bg="#acae27", fg="white",
                                font=('Arial', 9, 'bold'), width=15, state='disabled',
                                command=self.undo_delete)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        self.confirm_btn = tk.Button(delete_frame, text="Confirm Delete", bg="#e74c3c", fg="white",
                                   font=('Arial', 9, 'bold'), width=15, state='disabled',
                                   command=self.confirm_deletion)
        self.confirm_btn.pack(side=tk.LEFT, padx=5)

        # Edit action buttons
        edit_frame = tk.Frame(main_btn_frame, bg=PRIMARY_BG)
        edit_frame.pack(fill=tk.X, pady=1)

        tk.Label(edit_frame, text="Edit Actions:", bg=PRIMARY_BG, fg=TEXT_COLOR,
                font=('Arial', 9, 'italic')).pack(side=tk.LEFT, padx=5)

        self.undo_edit_btn = tk.Button(edit_frame, text="Undo Edit", bg="#acae27", fg="white",
                                     font=('Arial', 9, 'bold'), width=15, state='disabled',
                                     command=self.undo_edit)
        self.undo_edit_btn.pack(side=tk.LEFT, padx=5)

        self.confirm_edit_btn = tk.Button(edit_frame, text="Confirm Edit", bg="#42e73c", fg="white",
                                        font=('Arial', 9, 'bold'), width=15, state='disabled',
                                        command=self.confirm_edit)
        self.confirm_edit_btn.pack(side=tk.LEFT, padx=5)

    def create_info_frame(self):
        info_frame = tk.Frame(self.root, bg=PRIMARY_BG)
        info_frame.pack(pady=(0, 5), padx=10, fill=tk.X)

        shortcuts_text = "• Double-click row for details • Delete key to remove • Enter to add/search"
        tk.Label(info_frame, text=shortcuts_text, bg=PRIMARY_BG, fg="#95a5a6",
                font=('Arial', 8), justify=tk.CENTER).pack()

    # Core functionality methods
    def treeview_sort_column(self, tree, col, reverse):
        data = [(tree.set(item, col), item) for item in tree.get_children('')]

        try:
            data.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)

        for index, (val, item) in enumerate(data):
            tree.move(item, '', index)

        for c in tree['columns']:
            heading_text = tree.heading(c)['text']
            if ' ↑' in heading_text or ' ↓' in heading_text:
                heading_text = heading_text.replace(' ↑', '').replace(' ↓', '')
                tree.heading(c, text=heading_text)

        sort_symbol = ' ↓' if reverse else ' ↑'
        heading_text = tree.heading(col)['text'].replace(' ↑', '').replace(' ↓', '')
        tree.heading(col, text=heading_text + sort_symbol)
        tree.heading(col, command=lambda: self.treeview_sort_column(tree, col, not reverse))

    def add_job_from_ui(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a job URL.")
            return

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
            url,
        ]

        save_to_excel(row_data)
        self.tree.insert('', tk.END, values=row_data)
        self.url_entry.delete(0, tk.END)
        self.refresh_treeview()

    def refresh_treeview(self, filter_text=None):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in get_all_applications():
            row_vals = list(row)
            if filter_text:
                if not any(filter_text.lower() in str(cell).lower() for cell in row_vals):
                    continue
            self.tree.insert('', tk.END, values=row_vals)
        self.root.update_idletasks()

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a row to remove.")
            return

        values = self.tree.item(selected[0], 'values')
        self.last_deleted_row = values
        self.tree.delete(selected[0])

        found = delete_from_excel(values)
        if not found:
            print("Full row not found in Excel for deletion.")

        self.undo_btn.config(state='normal')
        self.confirm_btn.config(state='normal')

    def undo_delete(self):
        if not self.last_deleted_row:
            messagebox.showinfo("Undo Delete", "No deleted job to undo.")
            return

        save_to_excel(self.last_deleted_row)
        self.tree.insert('', tk.END, values=self.last_deleted_row)

        self.last_deleted_row = None
        self.undo_btn.config(state='disabled')
        self.confirm_btn.config(state='disabled')

    def confirm_deletion(self):
        self.last_deleted_row = None
        self.undo_btn.config(state='disabled')
        self.confirm_btn.config(state='disabled')

    def show_row_details(self):
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], 'values')

        details_win = tk.Toplevel()
        details_win.title("Job Application Details")
        details_win.geometry("600x400")
        details_win.configure(bg=PRIMARY_BG)
        details_win.resizable(False, False)
        details_win.lift()
        details_win.focus_force()
        details_win.bind("<Escape>", lambda event: details_win.destroy())

        for idx, col in enumerate(HEADERS):
            tk.Label(
                details_win,
                text=f"{col}:",
                font=('Arial', 10, 'bold'),
                bg=PRIMARY_BG,
                fg=TEXT_COLOR
            ).grid(row=idx, column=0, sticky=tk.W, padx=10, pady=5)

            if col == "Link":
                url = values[idx]

                def open_url(event, link=url):
                    webbrowser.open_new(link)

                link_label = tk.Label(
                    details_win,
                    text=url,
                    fg="skyblue",
                    cursor="hand2",
                    bg=PRIMARY_BG,
                    wraplength=450,
                    justify=tk.LEFT
                )
                link_label.grid(row=idx, column=1, sticky=tk.W, padx=10, pady=5)
                link_label.bind("<Button-1>", open_url)

            else:
                text = tk.Text(
                    details_win,
                    height=2,
                    wrap=tk.WORD,
                    width=60,
                    font=('Arial', 10),
                    bg=SECONDARY_BG,
                    fg=TEXT_COLOR,
                    relief='flat',
                    bd=0
                )
                text.insert(tk.END, values[idx])
                text.config(state='disabled')
                text.grid(row=idx, column=1, sticky=tk.W, padx=10, pady=5)

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a row to edit.")
            return

        item_id = selected[0]
        values = list(self.tree.item(item_id, 'values'))

        edit_win = tk.Toplevel()
        edit_win.title("Edit Job Entry")
        edit_win.geometry("600x400")
        edit_win.configure(bg=PRIMARY_BG)
        edit_win.resizable(False, False)

        entries = {}

        def save_changes():
            new_values = []
            for idx, col in enumerate(HEADERS):
                new_val = entries[col].get().strip()
                new_values.append(new_val if new_val else "Unknown")

            self.last_edited_row = values.copy()
            self.last_edited_item_id = item_id

            self.tree.item(item_id, values=new_values)
            update_excel_row(values, new_values)

            self.undo_edit_btn.config(state='normal')
            self.confirm_edit_btn.config(state='normal')
            edit_win.destroy()

        for idx, col in enumerate(HEADERS):
            tk.Label(
                edit_win,
                text=col,
                font=('Arial', 10, 'bold'),
                bg=PRIMARY_BG,
                fg=TEXT_COLOR
            ).grid(row=idx, column=0, padx=10, pady=5, sticky=tk.W)

            entry = tk.Entry(
                edit_win,
                width=50,
                bg=SECONDARY_BG,
                fg=TEXT_COLOR,
                insertbackground=TEXT_COLOR,
                relief='flat',
                highlightthickness=1,
                highlightbackground=BUTTON_BG,
                highlightcolor=BUTTON_BG,
                font=('Arial', 10)
            )
            entry.grid(row=idx, column=1, padx=10, pady=5)
            entry.insert(0, values[idx])
            entries[col] = entry

        tk.Button(
            edit_win,
            text="Save",
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            font=('Arial', 10, 'bold'),
            command=save_changes
        ).grid(row=len(HEADERS), column=0, columnspan=2, pady=15)

        entries[HEADERS[0]].focus_set()

    def undo_edit(self):
        if not self.last_edited_row or not self.last_edited_item_id:
            messagebox.showinfo("Undo Edit", "No edits to undo.")
            return

        self.tree.item(self.last_edited_item_id, values=self.last_edited_row)
        update_excel_row(self.tree.item(self.last_edited_item_id, 'values'), self.last_edited_row)

        self.last_edited_row = None
        self.last_edited_item_id = None
        self.undo_edit_btn.config(state='disabled')
        self.confirm_edit_btn.config(state='disabled')

    def confirm_edit(self):
        self.last_edited_row = None
        self.last_edited_item_id = None
        self.undo_edit_btn.config(state='disabled')
        self.confirm_edit_btn.config(state='disabled')

    def do_search(self, event=None):
        query = self.search_var.get().strip()
        if query == "":
            self.refresh_treeview()
        else:
            self.refresh_treeview(query)

    def clear_search(self):
        self.search_var.set("")
        self.refresh_treeview()
