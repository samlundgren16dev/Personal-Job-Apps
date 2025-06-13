# Colors and styling
PRIMARY_BG = "#2c3e50"
SECONDARY_BG = "#34495e"
TEXT_COLOR = "#ecf0f1"
BUTTON_BG = "#3498db"
BUTTON_FG = "#ffffff"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
RESET = "\033[0m"

# Excel configuration
EXCEL_FILE = "job_applications.xlsx"
HEADERS = ["Status", "Date Applied", "Company", "Job Title", "Location", "Link"]

# Application settings
APP_CONFIG = {
    "auto_save_interval": 300,  # seconds
    "max_browser_instances": 2,
    "parse_timeout": 15,  # seconds
    "enable_notifications": True,
    "backup_enabled": True,
    "backup_interval_days": 7,
    'window_title': 'Job Application Tracker v2.0',
    'min_window_size': (1000, 600),
    'default_window_size': (1200, 700),
    'terminal_height': 12,
    'max_recent_files': 10,
    'backup_retention_days': 30
}

# Browser Configuration
BROWSER_CONFIG = {
    'headless': True,
    'page_load_timeout': 15,
    'element_timeout': 10,
    'max_retries': 2,
    'pool_size': 2
}

# Status options for jobs with color coding
JOB_STATUS_OPTIONS = [
    "Applied",
    "Phone Interview",
    "Technical Interview",
    "Rejected",
    "No response"
]

# Status color mapping
STATUS_COLORS = {
    "Applied": "#ADD8E6",           # Light Blue
    "Phone Interview": "#FFFACD",   # Light Yellow
    "Technical Interview": "#FFDAB9", # Light Orange
    "Rejected": "#F08080",          # Light Red/Pink
    "No response": "#D3D3D3"        # Light Gray
}

# Enhanced headers with new fields
ENHANCED_HEADERS = [
    "Status",
    "Date Applied",
    "Company",
    "Job Title",
    "Location",
    "Link"
]

# Keyboard shortcuts
KEYBOARD_SHORTCUTS = {
    'new_job': '<Control-n>',
    'edit_job': '<Control-e>',
    'delete_job': '<Delete>',
    'search': '<Control-f>',
    'save': '<Control-s>',
    'export': '<Control-x>',
    'refresh': '<F5>',
    'quit': '<Control-q>',
    'copy': '<Control-c>',
    'select_all': '<Control-a>'
}

# Parsing Configuration
PARSING_CONFIG = {
    'timeout_seconds': 10,
    'max_concurrent_parsers': 3,
    'retry_delay': 2,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Excel Configuration
EXCEL_CONFIG = {
    'sheet_name': 'Applications',
    'backup_on_start': True,
    'auto_backup_interval': 3600,  # 1 hour
    'max_backups': 10
}

# UI Messages
MESSAGES = {
    'no_selection': "Please select a row first.",
    'url_required': "Please enter a job URL.",
    'parsing_success': "Job information parsed successfully!",
    'parsing_failed': "Failed to parse job information.",
    'save_success': "Data saved successfully.",
    'export_success': "Data exported successfully.",
    'import_success': "Data imported successfully.",
    'backup_success': "Backup created successfully."
}
