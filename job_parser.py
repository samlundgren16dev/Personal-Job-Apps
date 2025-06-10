from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from constants import GREEN, YELLOW, RED, CYAN, RESET

def parse_job_info(url):
    print("Starting headless browser to parse job info...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)

    try:
        print("Navigating to URL: ", url)
        driver.get(url)
        time.sleep(5)

        # Job Title
        job_title = "Unknown"
        title_selectors = [
            "//h1",
            "//h2",
            "//*[contains(@class, 'jobTitle')]",
            "//*[contains(@class, 'job-title')]",
            "//*[contains(@class, 'title')]",
            "//*[contains(@id, 'jobTitle')]",
            "//*[contains(@id, 'job-title')]",
            "//div[contains(text(), 'Job Title')]/following-sibling::*[1]",
        ]

        for selector in title_selectors:
            try:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.text.strip()
                if text:
                    job_title = text
                    print("Job title found: ", job_title)
                    break
            except:
                continue
        if job_title == "Unknown":
            print("Job title not found with known selectors.")

        # Company
        try:
            company = driver.find_element(By.XPATH, "//meta[@property='og:site_name']").get_attribute("content").strip()
            print("Company found: ", company)
        except:
            company = "Unknown"
            print("Company not found from meta tag.")

        # Location
        location = "Unknown"
        elements = driver.find_elements(By.XPATH,
            "//*[contains(@class, 'location') or contains(@id, 'location') or contains(text(), 'United States') or contains(text(), 'Remote')]"
        )

        if not elements:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), ',')]")

        for el in elements:
            text = el.text.strip()
            if not text:
                continue
            if (
                2 <= len(text.split()) <= 6 and
                ',' in text and
                not any(x in text.lower() for x in ['apply', 'requirements', 'responsibilities'])
            ):
                location = text
                print("Location found: ", location)
                break
        if location == "Unknown":
            print("Location not confidently detected.")

        # Job Requisition ID
        job_req = "Unknown"
        try:
            elems = driver.find_elements(
                By.XPATH,
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job id') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job number') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'requisition id')]"
            )
            for elem in elems:
                parent = elem.find_element(By.XPATH, "..")
                full_text = parent.text.strip()
                new_text = full_text.split()
                if len(new_text) >= 3:
                    job_num = new_text[2]
                    if len(full_text) > len(elem.text):
                        job_req = job_num
                        print("Job/Requisition # found: ", job_req)
                        break
        except:
            print("Job/Requisition ID not found or parse failed.")

        return {
            "Job Title": job_title,
            "Company": company,
            "Location": location,
            "Job/Req #": job_req
        }
    except Exception as e:
        print("Error parsing job info: ", e)
        return None
    finally:
        driver.quit()
        print("Browser session closed.")
