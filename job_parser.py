from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

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
                        break
                except:
                    continue
        except:
            job_title = "Unknown"

        try:
            company = driver.find_element(By.XPATH, "//meta[@property='og:site_name']").get_attribute("content").strip()
        except:
            company = "Unknown"

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
                break

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
                job_num = new_text[2]
                if len(full_text) > len(elem.text):
                    job_req = job_num
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
