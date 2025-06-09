import signal
import sys
import tkinter as tk
from gui import JobTrackerGUI
from excel_handler import init_excel

def signal_handler(sig, frame):
    print("\nCtrl+C pressed, exiting...")
    if 'root' in globals():
        root.quit()
    else:
        sys.exit(0)

def main():
    init_excel()

    root = tk.Tk()
    app = JobTrackerGUI(root)

    signal.signal(signal.SIGINT, signal_handler)

    def poll():
        root.after(100, poll)
    poll()

    def on_close():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
    print("Application closed.")

if __name__ == "__main__":
    main()
