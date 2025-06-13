"""
Main entry point for the Job Application Tracker.

This module initializes the application, sets up signal handlers,
and starts the GUI main loop with proper cleanup on exit.
"""

import signal
import sys
import tkinter as tk
import atexit
import threading
import time
import traceback
from tkinter import messagebox

from src.job_tracker.gui.main_window import JobTrackerGUI
from src.job_tracker.core.excel_handler import init_excel, flush_changes, backup_data
from src.job_tracker.core.parser import cleanup_browser_pool
from src.job_tracker.core.constants import APP_CONFIG, GREEN, RED, YELLOW, CYAN, RESET

# Global reference to root window
ROOT_WINDOW = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print(f"\n{YELLOW}Interrupt signal received, shutting down gracefully...{RESET}")
    force_exit()


def cleanup_and_exit():
    """Cleanup resources before exit - used for atexit."""
    try:
        print(f"{CYAN}Performing cleanup...{RESET}")

        # Save any pending changes
        print("Saving pending changes...")
        flush_changes()

        # Cleanup browser pool
        print("Cleaning up browser instances...")
        cleanup_browser_pool()

        # Close GUI if it exists
        if ROOT_WINDOW:
            try:
                ROOT_WINDOW.quit()
            except tk.TclError:
                pass  # Window already destroyed

        print(f"{GREEN}Cleanup completed successfully{RESET}")

    except Exception as e:
        print(f"{RED}Warning during cleanup: {e}{RESET}")


def force_exit():
    """Force exit with cleanup - used for signal handlers."""
    cleanup_and_exit()
    sys.exit(0)


def check_dependencies():
    """Check if all required dependencies are available."""
    try:
        import selenium
        import openpyxl
        print(f"{GREEN}All dependencies are available{RESET}")
        return True
    except ImportError as e:
        print(f"{RED}Missing dependency: {e}{RESET}")
        print(f"{YELLOW}Please install missing packages with: "
              f"pip install -r requirements.txt{RESET}")
        return False


def create_initial_backup():
    """Create initial backup on startup."""
    try:
        backup_path = backup_data()
        if backup_path:
            print(f"{GREEN}Initial backup created: {backup_path}{RESET}")
    except Exception as e:
        print(f"{YELLOW}Warning: Could not create initial backup: {e}{RESET}")


def setup_periodic_save():
    """Setup periodic auto-save in background thread."""
    def auto_save():
        while True:
            time.sleep(APP_CONFIG['auto_save_interval'])
            try:
                flush_changes()
                print("Auto-save completed")
            except Exception as e:
                print("Auto-save failed: ", e)

    thread = threading.Thread(target=auto_save, daemon=True)
    thread.start()


def main():
    """Main application entry point with comprehensive error handling."""
    global ROOT_WINDOW

    try:
        print(f"{CYAN}Starting Job Application Tracker...{RESET}")

        # Check dependencies
        if not check_dependencies():
            sys.exit(1)

        # Initialize Excel file
        print("Initializing data storage...")
        init_excel()

        # Create initial backup
        create_initial_backup()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

        # Register cleanup function
        atexit.register(cleanup_and_exit)

        # Create and configure main window
        ROOT_WINDOW = tk.Tk()
        ROOT_WINDOW.title(APP_CONFIG['window_title'])
        ROOT_WINDOW.minsize(*APP_CONFIG['min_window_size'])
        window_width, window_height = APP_CONFIG['default_window_size']
        ROOT_WINDOW.geometry(f"{window_width}x{window_height}")

        # Create application instance
        app = JobTrackerGUI(ROOT_WINDOW)

        # Setup periodic save
        setup_periodic_save()

        # Setup polling for signal handling on Windows
        def poll_signals():
            ROOT_WINDOW.after(100, poll_signals)
        poll_signals()

        print("Application started successfully!")
        print("Use Ctrl+C or close window to exit")

        # Start main event loop
        ROOT_WINDOW.mainloop()

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")

    except Exception as e:
        print("Fatal error occurred: ", e)
        traceback.print_exc()

        # Try to show error dialog if GUI is available
        if ROOT_WINDOW:
            try:
                messagebox.showerror(
                    "Fatal Error",
                    f"A fatal error occurred:\n{str(e)}\n\n"
                    f"The application will now close."
                )
            except tk.TclError:
                pass

    finally:
        print("Application shutdown complete")


if __name__ == "__main__":
    main()
