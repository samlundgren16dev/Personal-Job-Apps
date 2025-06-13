#!/usr/bin/env python3
"""
Setup script for Job Application Tracker
Checks dependencies, downloads ChromeDriver if needed, and sets up the application.
"""

import os
import sys
import subprocess
import platform
import requests
import zipfile
import stat
from pathlib import Path

# Required packages
REQUIRED_PACKAGES = [
    'selenium>=4.15.0',
    'openpyxl>=3.1.0',
    'requests>=2.31.0'
]

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("Python 3.7 or higher is required")
        return False
    print(f"Python {sys.version.split()[0]} is compatible")
    return True

def install_requirements():
    """Install required Python packages"""
    print("\nInstalling Python packages...")
    for package in REQUIRED_PACKAGES:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
            print(f"Installed {package}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {package}")
            return False
    return True

def get_chrome_version():
    """Get installed Chrome version"""
    try:
        if platform.system() == "Windows":
            import winreg
            reg_path = r"SOFTWARE\Google\Chrome\BLBeacon"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                version, _ = winreg.QueryValueEx(key, "version")
                return version
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run([
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"
            ], capture_output=True, text=True)
            return result.stdout.split()[-1]
        else:  # Linux
            result = subprocess.run([
                "google-chrome", "--version"
            ], capture_output=True, text=True)
            return result.stdout.split()[-1]
    except:
        return None

def download_chromedriver():
    """Download and install ChromeDriver"""
    print("\nSetting up ChromeDriver...")

    chrome_version = get_chrome_version()
    if not chrome_version:
        print("Google Chrome not found. Please install Chrome first.")
        return False

    major_version = chrome_version.split('.')[0]
    print(f"Found Chrome version {chrome_version}")

    # Determine platform
    system = platform.system().lower()
    if system == "windows":
        platform_name = "win64"
        executable_name = "chromedriver.exe"
    elif system == "darwin":
        platform_name = "mac-x64"
        executable_name = "chromedriver"
    else:
        platform_name = "linux64"
        executable_name = "chromedriver"

    # Use Chrome for Testing download URL
    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/{platform_name}/chromedriver-{platform_name}.zip"

    try:
        print(f"Downloading ChromeDriver for Chrome {chrome_version}...")
        response = requests.get(download_url)
        response.raise_for_status()

        # Save and extract
        driver_dir = Path("drivers")
        driver_dir.mkdir(exist_ok=True)

        zip_path = driver_dir / "chromedriver.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(driver_dir)

        # Make executable on Unix systems
        driver_path = driver_dir / executable_name
        if system != "windows":
            driver_path.chmod(driver_path.stat().st_mode | stat.S_IEXEC)

        # Add to PATH
        current_dir = os.path.abspath(driver_dir)
        if current_dir not in os.environ.get('PATH', ''):
            print(f"Add {current_dir} to your PATH environment variable")

        # Cleanup
        zip_path.unlink()

        print(f"ChromeDriver installed to {driver_path}")
        return True

    except Exception as e:
        print(f"Failed to download ChromeDriver: {e}")
        return False

def create_shortcut():
    """Create desktop shortcut (Windows only)"""
    if platform.system() != "Windows":
        return

    try:
        import win32com.client

        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "Job Tracker.lnk"

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = str(Path.cwd() / "main.py")
        shortcut.WorkingDirectory = str(Path.cwd())
        shortcut.IconLocation = sys.executable
        shortcut.save()

        print(f"Desktop shortcut created: {shortcut_path}")
    except ImportError:
        print("Install pywin32 to create desktop shortcuts")
    except Exception as e:
        print(f"Could not create shortcut: {e}")

def main():
    """Main setup function"""
    print("\nJob Application Tracker Setup")
    print("=" * 40)

    if not check_python_version():
        return False

    if not install_requirements():
        return False

    if not download_chromedriver():
        print("\nChromeDriver setup failed")
        return False

    # Create shortcut
    create_shortcut()

    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("   1. Run: python main.py")
    print("   2. Start tracking your job applications!")
    print("\nTips:")
    print("   - Use Ctrl+N to add jobs quickly")
    print("   - The app will auto-save every 5 minutes")
    print("   - Check the View menu for statistics")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
