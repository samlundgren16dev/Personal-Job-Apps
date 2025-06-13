import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont
import webbrowser
import sys
import threading
import time
from datetime import datetime

from ..core.constants import (
    PRIMARY_BG, SECONDARY_BG, BUTTON_BG, BUTTON_FG, TEXT_COLOR,
    HEADERS, JOB_STATUS_OPTIONS, STATUS_COLORS
)
from ..core.excel_handler import (
    save_to_excel, delete_from_excel, get_all_applications,
    update_excel_row, flush_changes, export_to_csv, import_from_csv,
    backup_data, get_statistics
)
from ..core.parser import parse_job_info, cleanup_browser_pool

class StreamRedirector:
    def __init__(self, write_callback):
        self.write_callback = write_callback

    def write(self, message):
        if message.strip():
            self.write_callback(message)

    def flush(self):
        pass

class JobTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.last_deleted_row = None
        self.last_edited_row = None
        self.last_edited_item_id = None
        self.is_parsing = False  # Track parsing state
        self.parse_start_time = 0
        self.parse_cancelled = False  # Track if parsing was cancelled
        self.current_parse_thread = None  # Track current parsing thread

        # Initialize GUI components
        self.style = None
        self.url_entry = None
        self.progress_frame = None
        self.add_job_btn = None
        self.progress_bar = None
        self.progress_label = None
        self.search_var = None
        self.tree = None
        self.quick_status_var = None
        self.quick_status_combo = None
        self.undo_btn = None
        self.confirm_btn = None
        self.undo_edit_btn = None
        self.confirm_edit_btn = None
        self.terminal_text = None

        self.setup_gui()
        sys.stdout = StreamRedirector(self.print_to_terminal)
        sys.stderr = StreamRedirector(self.print_to_terminal)

    def setup_gui(self):
        self.root.title("Job Tracker")
        self.root.configure(bg=PRIMARY_BG)
        self.root.minsize(1000, 600)
        self.root.geometry("1200x700")

        self.setup_styles()
        self.create_widgets()

        # Handle window close to cleanup browser pool
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        print("Cleaning up browser pool...")
        cleanup_browser_pool()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.root.destroy()

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

        # Configure status color tags
        for status in JOB_STATUS_OPTIONS:
            if status in STATUS_COLORS:
                self.style.configure(f"status_{status}",
                                   background=STATUS_COLORS[status])

    def create_widgets(self):
        self.create_menu_bar()
        self.create_url_entry_frame()
        self.create_search_frame()
        self.create_treeview_frame()
        self.create_control_buttons_frame()
        self.create_info_frame()
        self.create_terminal_frame()
        self.setup_keyboard_shortcuts()
        self.refresh_treeview()

    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Job", command=self.add_job_from_ui,
                             accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV...", command=self.export_data)
        file_menu.add_command(label="Import from CSV...", command=self.import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Backup Data", command=self.backup_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close,
                             accelerator="Alt+F4")

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Edit Selected", command=self.edit_selected,
                             accelerator="Ctrl+E")
        edit_menu.add_command(label="Delete Selected", command=self.remove_selected,
                             accelerator="Del")
        edit_menu.add_separator()
        edit_menu.add_command(label="Search", command=self.focus_search,
                             accelerator="Ctrl+F")
        edit_menu.add_command(label="Refresh", command=self.refresh_treeview,
                             accelerator="F5")

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Statistics", command=self.show_statistics)
        view_menu.add_command(label="Clear Terminal", command=self.clear_terminal)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts",
                             command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<Control-n>", lambda e: self.add_job_from_ui())
        self.root.bind("<Control-e>", lambda e: self.edit_selected())
        self.root.bind("<Control-f>", lambda e: self.focus_search())
        self.root.bind("<Control-s>", lambda e: self.save_data())
        self.root.bind("<F5>", lambda e: self.refresh_treeview())
        self.root.bind("<Control-x>", lambda e: self.export_data())
        self.root.bind("<Escape>", lambda e: self.stop_parsing() if self.is_parsing else None)

    def focus_search(self):
        """Focus on search entry"""
        # Focus on the search entry widget
        for child in self.root.winfo_children():
            if hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Entry) and hasattr(subchild, 'textvariable'):
                        if hasattr(subchild.textvariable, 'get'):
                            subchild.focus_set()
                            return

    def save_data(self):
        """Manual save (force flush changes)"""
        flush_changes()
        self.print_to_terminal("Data saved successfully")

    def export_data(self):
        """Export data to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Job Applications"
        )

        if filename:
            if export_to_csv(filename):
                messagebox.showinfo("Export Successful",
                                   f"Data exported to {filename}")
            else:
                messagebox.showerror("Export Failed", "Failed to export data")

    def import_data(self):
        """Import data from CSV"""
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Import Job Applications"
        )

        if filename:
            count = import_from_csv(filename)
            if count > 0:
                messagebox.showinfo("Import Successful",
                                   f"Imported {count} job applications")
                self.refresh_treeview()
            else:
                messagebox.showerror("Import Failed", "Failed to import data")

    def backup_data(self):
        """Create data backup"""
        backup_path = backup_data()
        if backup_path:
            messagebox.showinfo("Backup Successful",
                               f"Backup created at:\n{backup_path}")
        else:
            messagebox.showerror("Backup Failed", "Failed to create backup")

    def show_statistics(self):
        """Show application statistics"""
        stats = get_statistics()

        # Create statistics window
        stats_win = tk.Toplevel()
        stats_win.title("Job Application Statistics")
        stats_win.geometry("500x400")
        stats_win.configure(bg=PRIMARY_BG)
        stats_win.resizable(False, False)

        # Total count
        tk.Label(stats_win, text=f"Total Applications: {stats['total']}",
                font=('Arial', 14, 'bold'), bg=PRIMARY_BG,
                fg=TEXT_COLOR).pack(pady=10)

        # Top companies
        if stats['companies']:
            tk.Label(stats_win, text="Top Companies:",
                    font=('Arial', 12, 'bold'), bg=PRIMARY_BG,
                    fg=TEXT_COLOR).pack(pady=(20,5))

            companies_frame = tk.Frame(stats_win, bg=PRIMARY_BG)
            companies_frame.pack(fill=tk.X, padx=20)

            for company, count in stats['companies'][:5]:
                tk.Label(companies_frame,
                        text=f"{company}: {count} applications",
                        bg=SECONDARY_BG, fg=TEXT_COLOR,
                        font=('Arial', 10)).pack(fill=tk.X, pady=2)

        # Top locations
        if stats['locations']:
            tk.Label(stats_win, text="Top Locations:",
                    font=('Arial', 12, 'bold'), bg=PRIMARY_BG,
                    fg=TEXT_COLOR).pack(pady=(20,5))

            locations_frame = tk.Frame(stats_win, bg=PRIMARY_BG)
            locations_frame.pack(fill=tk.X, padx=20)

            for location, count in stats['locations'][:5]:
                tk.Label(locations_frame,
                        text=f"{location}: {count} applications",
                        bg=SECONDARY_BG, fg=TEXT_COLOR,
                        font=('Arial', 10)).pack(fill=tk.X, pady=2)

    def show_shortcuts(self):
        """Show keyboard shortcuts help"""
        shortcuts_win = tk.Toplevel()
        shortcuts_win.title("Keyboard Shortcuts")
        shortcuts_win.geometry("400x300")
        shortcuts_win.configure(bg=PRIMARY_BG)
        shortcuts_win.resizable(False, False)

        shortcuts_text = """
        Keyboard Shortcuts:

        Ctrl+N          Add New Job
        Ctrl+E          Edit Selected Job
        Ctrl+F          Search
        Ctrl+S          Save Data
        Ctrl+X          Export Data
        F5              Refresh View
        Delete          Remove Selected Job
        Enter           Add Job (in URL field)
        Enter           Search (in search field)
        Double-click    Show Job Details
        Escape          Stop Parsing / Close Dialog
        """

        tk.Label(shortcuts_win, text=shortcuts_text,
                font=('Courier', 10), bg=PRIMARY_BG, fg=TEXT_COLOR,
                justify=tk.LEFT).pack(pady=20, padx=20)

    def show_about(self):
        """Show about dialog"""
        about_text = ("Job Application Tracker v2.0\n\n"
                     "A simple desktop application to track job applications\n"
                     "with automatic job parsing and Excel integration.")
        messagebox.showinfo("About", about_text)

    def create_url_entry_frame(self):
        frame_top = tk.Frame(self.root, bg=SECONDARY_BG)
        frame_top.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(frame_top, text="Job Posting URL:", bg=SECONDARY_BG,
                fg=TEXT_COLOR, font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        self.url_entry = tk.Entry(frame_top, width=60, font=('Arial', 10))
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.url_entry.bind("<Return>", lambda event: self.add_job_from_ui() if not self.is_parsing else None)

        # Add progress bar for job parsing
        self.progress_frame = tk.Frame(frame_top, bg=SECONDARY_BG)
        self.progress_frame.pack(side=tk.RIGHT, padx=5)

        self.add_job_btn = tk.Button(self.progress_frame, text="Add Job",
                                    bg=BUTTON_BG, fg=BUTTON_FG,
                                    font=('Arial', 10, 'bold'),
                                    command=self.add_job_from_ui)
        self.add_job_btn.pack(side=tk.LEFT, padx=2)

        # Stop parsing button (initially hidden)
        self.stop_parse_btn = tk.Button(self.progress_frame, text="Stop",
                                       bg="#e74c3c", fg="white",
                                       font=('Arial', 10, 'bold'),
                                       command=self.stop_parsing)

        self.progress_bar = ttk.Progressbar(self.progress_frame,
                                           mode='indeterminate', length=100)
        self.progress_label = tk.Label(self.progress_frame, text="",
                                      bg=SECONDARY_BG, fg=TEXT_COLOR,
                                      font=('Arial', 8))

    def create_search_frame(self):
        frame_search = tk.Frame(self.root, bg=SECONDARY_BG)
        frame_search.pack(pady=5, fill=tk.X, padx=10)

        self.search_var = tk.StringVar()
        tk.Label(frame_search, text="Search:", bg=SECONDARY_BG, fg=TEXT_COLOR,
                font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        search_entry = tk.Entry(frame_search, textvariable=self.search_var,
                               width=40, font=('Arial', 10))
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

        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                   command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                                   command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Configure column headings and widths
        for col in HEADERS:
            self.tree.heading(col, text=col,
                             command=lambda c=col: self.treeview_sort_column(
                                 self.tree, c, False))
            if col == "Status":
                self.tree.column(col, anchor=tk.CENTER, width=120)
            elif col == "Date Applied":
                self.tree.column(col, anchor=tk.CENTER, width=100)
            elif col == "Company":
                self.tree.column(col, anchor=tk.W, width=150)
            elif col == "Job Title":
                self.tree.column(col, anchor=tk.W, width=200)
            elif col == "Location":
                self.tree.column(col, anchor=tk.W, width=150)
            elif col == "Link":
                self.tree.column(col, anchor=tk.W, width=100)
            else:
                self.tree.column(col, anchor=tk.W, width=150)

        # Setup status color tags
        for status in JOB_STATUS_OPTIONS:
            if status in STATUS_COLORS:
                tag_name = f"status_{status}"
                self.tree.tag_configure(tag_name,
                                       background=STATUS_COLORS[status])

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Delete>", lambda event: self.remove_selected())

    def create_control_buttons_frame(self):
        main_btn_frame = tk.Frame(self.root, bg=PRIMARY_BG)
        main_btn_frame.pack(pady=(5, 10), padx=10, fill=tk.X)

        # Primary action buttons
        primary_frame = tk.Frame(main_btn_frame, bg=PRIMARY_BG)
        primary_frame.pack(fill=tk.X, pady=2)

        tk.Button(primary_frame, text="Remove Selected Job",
                 bg="#e74c3c", fg="white",
                 font=('Arial', 10, 'bold'), width=18,
                 command=self.remove_selected).pack(side=tk.LEFT, padx=5)

        tk.Button(primary_frame, text="Edit Selected Job",
                 bg=BUTTON_BG, fg=BUTTON_FG,
                 font=('Arial', 10, 'bold'), width=18,
                 command=self.edit_selected).pack(side=tk.LEFT, padx=5)

        # Quick status update section
        status_frame = tk.Frame(primary_frame, bg=PRIMARY_BG)
        status_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(status_frame, text="Quick Status Update:",
                bg=PRIMARY_BG, fg=TEXT_COLOR,
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        self.quick_status_var = tk.StringVar()
        self.quick_status_combo = ttk.Combobox(
            status_frame,
            textvariable=self.quick_status_var,
            values=JOB_STATUS_OPTIONS,
            state="readonly",
            width=12,
            font=('Arial', 9)
        )
        self.quick_status_combo.pack(side=tk.LEFT, padx=5)
        self.quick_status_combo.set("Applied")

        tk.Button(status_frame, text="Update Status", bg="#2ecc71", fg="white",
                 font=('Arial', 9, 'bold'), width=12,
                 command=self.update_selected_status).pack(side=tk.LEFT, padx=5)

        # Delete action buttons
        delete_frame = tk.Frame(main_btn_frame, bg=PRIMARY_BG)
        delete_frame.pack(fill=tk.X, pady=1)

        tk.Label(delete_frame, text="Delete Actions:", bg=PRIMARY_BG,
                fg=TEXT_COLOR, font=('Arial', 9, 'italic')).pack(side=tk.LEFT, padx=5)

        self.undo_btn = tk.Button(delete_frame, text="Undo Delete",
                                 bg="#acae27", fg="white",
                                 font=('Arial', 9, 'bold'), width=15,
                                 state='disabled',
                                 command=self.undo_delete)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        self.confirm_btn = tk.Button(delete_frame, text="Confirm Delete",
                                    bg="#e74c3c", fg="white",
                                    font=('Arial', 9, 'bold'), width=15,
                                    state='disabled',
                                    command=self.confirm_deletion)
        self.confirm_btn.pack(side=tk.LEFT, padx=5)

    def create_info_frame(self):
        info_frame = tk.Frame(self.root, bg=PRIMARY_BG)
        info_frame.pack(pady=(0, 5), padx=10, fill=tk.X)

        shortcuts_text = ("• Double-click row for details • Delete key to remove "
                         "• Enter to add/search")
        tk.Label(info_frame, text=shortcuts_text, bg=PRIMARY_BG, fg="#95a5a6",
                font=('Arial', 8), justify=tk.CENTER).pack()

    def create_terminal_frame(self):
        terminal_frame = tk.Frame(self.root, bg=PRIMARY_BG)
        terminal_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        # Terminal text widget
        self.terminal_text = tk.Text(
            terminal_frame,
            height=12,  # increased height from 8 to 12
            bg="#111111",
            fg="#39FF14",
            insertbackground="white",
            font=("Courier", 10),
            state='disabled',
            wrap='word'
        )
        self.terminal_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(terminal_frame, command=self.terminal_text.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.terminal_text['yscrollcommand'] = scrollbar.set

        # Buttons frame next to terminal
        btn_frame = tk.Frame(terminal_frame, bg=PRIMARY_BG)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))

        clear_btn = tk.Button(
            btn_frame,
            text="Clear Terminal",
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            font=('Arial', 10, 'bold'),
            width=15,
            command=self.clear_terminal
        )
        clear_btn.pack(pady=(0, 5))

        copy_btn = tk.Button(
            btn_frame,
            text="Copy Terminal",
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            font=('Arial', 10, 'bold'),
            width=15,
            command=self.copy_terminal
        )
        copy_btn.pack(pady=(0, 5))

    def clear_terminal(self):
        self.terminal_text.config(state='normal')
        self.terminal_text.delete('1.0', tk.END)
        self.terminal_text.config(state='disabled')

    def copy_terminal(self):
        # Copy all terminal text to clipboard
        self.root.clipboard_clear()
        terminal_content = self.terminal_text.get('1.0', tk.END)
        self.root.clipboard_append(terminal_content)
        print("Terminal content copied to clipboard")

    def print_to_terminal(self, message):
        if not hasattr(self, 'terminal_text'):
            return
        try:
            self.terminal_text.config(state='normal')
            self.terminal_text.insert(tk.END, f"{message}\n")
            self.terminal_text.see(tk.END)
            self.terminal_text.config(state='disabled')
        except tk.TclError:
            pass

    # Core functionality methods
    def on_double_click(self, event):
        """Handle double-click - show details only if clicking on a row, not header"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":  # Clicked on a data cell, not header
            self.show_row_details()
        # If region == "heading", do nothing (let column sorting handle it)

    def treeview_sort_column(self, tree, col, reverse):
        data = [(tree.set(item, col), item) for item in tree.get_children('')]

        try:
            data.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)

        for index, (_, item) in enumerate(data):
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

        if self.is_parsing:
            messagebox.showinfo("Please Wait",
                               "Already parsing a job. Please wait for it to complete.")
            return

        # Start parsing in background thread
        self.start_job_parsing(url)

    def start_job_parsing(self, url):
        """Start job parsing in a background thread with progress indication"""
        self.is_parsing = True
        self.parse_cancelled = False
        self.parse_start_time = time.time()
        self.add_job_btn.config(state='disabled')
        self.stop_parse_btn.pack(side=tk.LEFT, padx=2)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        self.progress_bar.start(10)
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.progress_label.config(text="Parsing... 0.0s")

        # Start background thread
        self.current_parse_thread = threading.Thread(target=self._parse_job_background, args=(url,))
        self.current_parse_thread.daemon = True
        self.current_parse_thread.start()

        # Start timer update
        self.update_parse_timer()

    def update_parse_timer(self):
        """Update the parsing timer display"""
        if self.is_parsing and not self.parse_cancelled:
            elapsed = time.time() - self.parse_start_time
            self.progress_label.config(text=f"Parsing... {elapsed:.1f}s")
            # Schedule next update in 100ms
            self.root.after(100, self.update_parse_timer)
        elif self.parse_cancelled:
            self.progress_label.config(text="Cancelled")

    def _parse_job_background(self, url):
        """Background job parsing with thread-safe UI updates"""
        try:
            # Pass the cancelled flag to the parser
            info = parse_job_info(url, cancelled_callback=lambda: self.parse_cancelled)
            if not self.parse_cancelled:
                # Schedule UI update on main thread
                self.root.after(0, self._on_job_parsed, url, info, None)
        except Exception as e:
            if not self.parse_cancelled:
                # Schedule error handling on main thread
                self.root.after(0, self._on_job_parsed, url, None, str(e))

    def _on_job_parsed(self, url, info, error):
        """Handle job parsing completion on main thread"""
        # Calculate final parse time
        final_time = time.time() - self.parse_start_time

        self.is_parsing = False
        self.current_parse_thread = None
        self.add_job_btn.config(state='normal')
        self.stop_parse_btn.pack_forget()
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()

        if self.parse_cancelled:
            self.print_to_terminal(f"Parsing cancelled after {final_time:.1f} seconds")
            self.parse_cancelled = False
            return

        # Show final parse time in terminal
        self.print_to_terminal(f"Parsing completed in {final_time:.1f} seconds")

        if error:
            messagebox.showerror("Parsing Error",
                                f"Failed to parse job info: {error}")
            return

        if not info:
            messagebox.showwarning("Parsing Failed",
                                  "Could not extract job information from the URL.")
            return

        today = datetime.today().strftime('%Y-%m-%d')
        row_data = [
            "Applied",                          # Status
            today,                              # Date Applied
            info["Company"],                    # Company
            info["Job Title"],                  # Job Title
            info["Location"],                   # Location
            url,                               # Link
        ]

        save_to_excel(row_data)
        self.tree.insert('', tk.END, values=row_data)
        self.url_entry.delete(0, tk.END)
        self.refresh_treeview()
        self.print_to_terminal("Successfully added new job row")

    def stop_parsing(self):
        """Stop the current parsing operation"""
        if self.is_parsing:
            self.parse_cancelled = True
            self.print_to_terminal("Stopping parsing... please wait for cleanup")

            # Force cleanup after a reasonable timeout
            def force_cleanup():
                if self.is_parsing:
                    self.is_parsing = False
                    self.current_parse_thread = None
                    self.add_job_btn.config(state='normal')
                    self.stop_parse_btn.pack_forget()
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
                    self.progress_label.pack_forget()
                    self.print_to_terminal("Parsing forcefully stopped")

            # Give it 3 seconds to cleanup gracefully, then force stop
            self.root.after(3000, force_cleanup)

    def refresh_treeview(self, filter_text=None):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Use cached data to avoid repeated Excel loads
        try:
            rows = get_all_applications()
            for row in rows:
                row_vals = list(row)

                # Pad to current header length if needed
                while len(row_vals) < len(HEADERS):
                    row_vals.append("Unknown")

                # Ensure we only have the right number of columns
                row_vals = row_vals[:len(HEADERS)]

                if filter_text:
                    if not any(filter_text.lower() in str(cell).lower()
                              for cell in row_vals):
                        continue

                # Insert with color coding for status
                item_id = self.tree.insert('', tk.END, values=row_vals)
                self.apply_status_color(item_id, row_vals[0])  # Status is now first column
        except Exception as e:
            self.print_to_terminal(f"Error refreshing treeview: {e}")

        self.root.update_idletasks()

    def apply_status_color(self, item_id, status):
        """Apply color coding to status column based on status value"""
        if status in STATUS_COLORS:
            # Create a unique tag for this status
            tag_name = f"status_{status}"
            self.tree.set(item_id, "Status", status)  # Ensure status is properly set
            self.tree.item(item_id, tags=(tag_name,))

            # Configure the tag with the appropriate color
            self.tree.tag_configure(tag_name, background=STATUS_COLORS[status])

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
            self.print_to_terminal("Full row not found in Excel for deletion.")

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
        print("Deletion undone")

    def confirm_deletion(self):
        self.last_deleted_row = None
        self.undo_btn.config(state='disabled')
        self.confirm_btn.config(state='disabled')
        print("Confirmed deletion")

    def show_row_details(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = list(self.tree.item(item_id, 'values'))
        self.open_edit_window(item_id, values)

    def open_edit_window(self, item_id, values):
        # Pad values to match current headers (for backward compatibility)
        while len(values) < len(HEADERS):
            values.append("Unknown")

        edit_win = tk.Toplevel()
        edit_win.title("Edit Job Entry")
        edit_win.geometry("600x400")
        edit_win.configure(bg=PRIMARY_BG)
        edit_win.resizable(False, False)

        entries = {}
        entry_widgets = []

        def save_changes():
            new_values = []
            for idx, col in enumerate(HEADERS):
                if col == "Status":
                    # Handle StringVar for Status dropdown
                    new_val = entries[col].get().strip()
                else:
                    # Handle Entry widget for other fields
                    new_val = entries[col].get().strip()
                new_values.append(new_val if new_val else "Unknown")

            self.tree.item(item_id, values=new_values)
            self.apply_status_color(item_id, new_values[0])  # Apply color to updated status
            update_excel_row(values, new_values)
            edit_win.destroy()

        for idx, col in enumerate(HEADERS):
            tk.Label(
                edit_win,
                text=col,
                font=('Arial', 10, 'bold'),
                bg=PRIMARY_BG,
                fg=TEXT_COLOR
            ).grid(row=idx, column=0, padx=10, pady=5, sticky=tk.W)

            # Special handling for Status field - use dropdown
            if col == "Status":
                status_var = tk.StringVar()
                status_combo = ttk.Combobox(
                    edit_win,
                    textvariable=status_var,
                    values=JOB_STATUS_OPTIONS,
                    state="readonly",
                    width=48,
                    font=('Arial', 10)
                )
                status_combo.grid(row=idx, column=1, padx=10, pady=5)
                status_combo.set(values[idx] if values[idx] in JOB_STATUS_OPTIONS else "Applied")
                entries[col] = status_var  # Store the StringVar for getting value
            else:
                # Regular text entry for other fields
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
                entry_widgets.append(entry)

        tk.Button(
            edit_win,
            text="Save",
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            font=('Arial', 10, 'bold'),
            command=save_changes
        ).grid(row=len(HEADERS), column=0, columnspan=2, pady=15)

        # Focus on the first focusable widget
        entry_widgets[0].focus_set() if entry_widgets else None

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a row to edit.")
            return
        item_id = selected[0]
        values = list(self.tree.item(item_id, 'values'))
        self.open_edit_window(item_id, values)

    def update_selected_status(self):
        """Update status of selected job using quick status dropdown"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection",
                                  "Please select a job to update status.")
            return

        item_id = selected[0]
        old_values = list(self.tree.item(item_id, 'values'))

        # Pad values to match current headers (for backward compatibility)
        while len(old_values) < len(HEADERS):
            old_values.append("Unknown")

        new_status = self.quick_status_var.get()
        if not new_status:
            messagebox.showwarning("No Status",
                                  "Please select a status to update.")
            return

        # Update the status column (now index 0 in new headers)
        new_values = old_values.copy()
        new_values[0] = new_status  # Status is first column

        # Update treeview and Excel
        self.tree.item(item_id, values=new_values)
        self.apply_status_color(item_id, new_status)  # Apply color to updated status
        update_excel_row(old_values, new_values)

        print(f"Status updated to: {new_status}")
        messagebox.showinfo("Status Updated", f"Status updated to: {new_status}")

    def do_search(self, event=None):
        query = self.search_var.get().strip()
        if query == "":
            print("No search query data")
            self.refresh_treeview()
        else:
            print("Search performed successfully")
            self.refresh_treeview(query)

    def clear_search(self):
        self.search_var.set("")
        self.refresh_treeview()
