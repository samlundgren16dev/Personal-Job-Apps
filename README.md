# Personal Job Application Tracker (Tkinter + Excel + Selenium)

A simple desktop GUI app that helps you keep track of jobs you've applied to. It uses **Tkinter** for the UI, **Excel** for persistent storage, and **Selenium** to auto-fill job info from URLs.

## Features

- View and manage your job application list in a table.
- Add job applications by URL (job title, company, and location are auto-parsed).
- Edit any job entry manually with the `Edit Selected Job` button.
- Sort on any keyword or string, and rows that do not contain that search data will be filtered out, and will be filtered back in once you clear the search.
- Double click on any row, and a detailed window view containing the data for that row will open, along with a hyperlink to the job posting, allowing easy access to past job listings you've applied to.
- By pressing on any of the column headers, the rows will sort alphabetically by that column header's data.
- Delete selected entries(either with the `del` key, or the built in button).
- Excel file (`job_applications.xlsx`) saves all data for future use.

![App Showcase:](showcase/ExampleAppPic.png)

The parsing is not perfect, you may need to edit a few of the fields to be correct. It is quite hard to get it right every time, due to how some job postings have their data setup.

## Requirements

- Python 3.7+
- `selenium`
- `requests`
- `beautifulsoup4`
- `openpyxl`

Install dependencies:

```bash
pip install selenium requests beautifulsoup4 openpyxl
```

You also need [**ChromeDriver**](https://sites.google.com/chromium.org/driver/) in your system `PATH`.

## Usage

Run the app:

```bash
python main.py
```

### Notes:
- Parsed info (job title, company, location) may sometimes be incomplete depending on the job page structure.
- You can edit the row manually if parsing fails.

## Files

- `main.py` – Main application code.
- `constants.py` - Holds all the constants used throughout this project.
- `excel_handler.py` - Handles all of the excel logic.
- `gui.py` - Handles all of the gui logic.
- `job_parser.py` - Handles all the data parsing.
- `job_applications.xlsx` – Automatically created Excel file storing job data.
