from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import signal
import time
import threading
from queue import Queue, Empty
from contextlib import contextmanager
from .constants import GREEN, YELLOW, RED, CYAN, RESET
from urllib.parse import urlparse, parse_qs
import re

# Browser pool for reusing browser instances
_browser_pool = Queue(maxsize=2)  # Max 2 browsers to avoid too much memory usage
_pool_lock = threading.Lock()

class JobParserConfig:
    """Configuration for job parsing"""
    BROWSER_TIMEOUT = 15  # More generous for complex sites
    PAGE_LOAD_TIMEOUT = 20  # More generous for page loads
    MAX_RETRIES = 1  # Allow one retry
    ELEMENT_TIMEOUT = 3  # More time for element detection
    MAX_SELECTORS_PER_FUNCTION = 5  # Try more selectors for better results
    TOTAL_PARSE_TIMEOUT = 45  # Increased to allow for retries

def _create_browser():
    """Create a new browser instance with balanced settings"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    # Re-enable JS and CSS for better compatibility with modern sites
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    options.add_argument(f"--user-agent={user_agent}")
    # Add stability options
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(JobParserConfig.PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(JobParserConfig.ELEMENT_TIMEOUT)
        return driver
    except Exception as e:
        print("Failed to create browser: ", e)
        return None

@contextmanager
def get_browser():
    """Context manager to get a browser from the pool"""
    driver = None
    try:
        # Try to get browser from pool
        with _pool_lock:
            try:
                driver = _browser_pool.get_nowait()
                print("Reusing browser from pool")
            except Empty:
                print("Creating new browser instance")
                driver = _create_browser()
                if not driver:
                    raise RuntimeError("Failed to create browser")

        yield driver

    except Exception as e:
        print("Browser error: ", e)
        if driver:
            try:
                driver.quit()
            except:
                pass
        driver = None
        raise
    finally:
        # Return browser to pool if it's still working
        if driver:
            try:
                # Test if browser is still responsive
                driver.current_url
                with _pool_lock:
                    try:
                        _browser_pool.put_nowait(driver)
                        print("Browser returned to pool")
                    except:
                        # Pool is full, close this browser
                        driver.quit()
                        print("Browser pool full, closing browser")
            except:
                # Browser is broken, close it
                try:
                    driver.quit()
                except:
                    pass

def cleanup_browser_pool():
    """Clean up all browsers in the pool"""
    with _pool_lock:
        while not _browser_pool.empty():
            try:
                driver = _browser_pool.get_nowait()
                driver.quit()
            except:
                pass

def parse_job_info(url, max_retries=None, cancelled_callback=None):
    """Parse job information from URL with retry logic"""
    if max_retries is None:
        max_retries = JobParserConfig.MAX_RETRIES

    for attempt in range(max_retries + 1):
        try:
            # Check if cancelled before starting attempt
            if cancelled_callback and cancelled_callback():
                print("Parsing cancelled by user")
                return None

            return _parse_job_info_single(url, cancelled_callback)
        except Exception as e:
            print("Attempt ", attempt + 1, " failed: ", e)
            if attempt < max_retries:
                # Check if cancelled during retry delay
                if cancelled_callback and cancelled_callback():
                    print("Parsing cancelled during retry")
                    return None
                print("Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("All parsing attempts failed")
                return None

def _parse_job_info_single(url, cancelled_callback=None):
    """Single attempt to parse job info with timeout"""
    import time
    import signal
    from urllib.parse import urlparse, parse_qs

    def timeout_handler(signum, frame):
        raise TimeoutException("Parsing timeout exceeded")

    start_time = time.time()
    print("Starting job info parsing...")

    # Set up timeout signal (only works on Unix-like systems)
    try:
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(JobParserConfig.TOTAL_PARSE_TIMEOUT)
    except:
        pass  # Windows doesn't support SIGALRM

    try:
        # Check if cancelled before getting browser
        if cancelled_callback and cancelled_callback():
            print("Parsing cancelled before browser initialization")
            return None

        with get_browser() as driver:
            print("Navigating to URL: ", url)
            driver.get(url)

            # Check if cancelled after navigation
            if cancelled_callback and cancelled_callback():
                print("Parsing cancelled after page navigation")
                return None

            # Check if this is a LinkedIn job search page
            if "linkedin.com/jobs/search" in url:
                print("Detected LinkedIn job search page, extracting job posting URL...")
                try:
                    # Wait for job cards to load
                    WebDriverWait(driver, JobParserConfig.BROWSER_TIMEOUT).until(
                        lambda d: d.find_elements(By.XPATH, "//*[contains(@class, 'jobs-search__job-details')]")
                    )

                    # Get the current job ID from URL
                    parsed_url = urlparse(url)
                    query_params = parse_qs(parsed_url.query)
                    current_job_id = query_params.get('currentJobId', [None])[0]

                    if current_job_id:
                        # Try multiple selectors to find the job card
                        selectors = [
                            f"//*[contains(@data-job-id, '{current_job_id}')]",
                            f"//*[contains(@data-job-id, '{current_job_id}')]//a",
                            f"//*[contains(@class, 'jobs-search__job-details')]//a[contains(@href, '{current_job_id}')]",
                            f"//*[contains(@class, 'jobs-search__job-details')]//a[contains(@href, '/jobs/view/')]"
                        ]

                        job_url = None
                        for selector in selectors:
                            try:
                                elements = driver.find_elements(By.XPATH, selector)
                                if elements:
                                    # Try to get href from the element or its parent
                                    job_url = elements[0].get_attribute("href")
                                    if not job_url and elements[0].find_elements(By.XPATH, ".//a"):
                                        job_url = elements[0].find_elements(By.XPATH, ".//a")[0].get_attribute("href")
                                    if job_url:
                                        break
                            except:
                                continue

                        if job_url:
                            print(f"Found job posting URL: {job_url}")
                            # Navigate to the actual job posting
                            driver.get(job_url)
                            # Wait for job details to load
                            WebDriverWait(driver, JobParserConfig.BROWSER_TIMEOUT).until(
                                lambda d: d.find_elements(By.XPATH, "//*[contains(@class, 'jobs-unified-top-card')]")
                            )
                        else:
                            print("Could not find job posting URL")
                except Exception as e:
                    print(f"Error extracting job posting URL: {e}")

            # Page load check with reasonable timeout
            try:
                WebDriverWait(driver, JobParserConfig.BROWSER_TIMEOUT).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                print("Page load timeout - continuing anyway")

            # Parse fields with individual timeout checks
            job_title = _parse_job_title_fast(driver)

            # Check if cancelled after job title parsing
            if cancelled_callback and cancelled_callback():
                print("Parsing cancelled after job title extraction")
                return None

            # Check timeout after each field
            elapsed = time.time() - start_time
            if elapsed > JobParserConfig.TOTAL_PARSE_TIMEOUT:
                print(f"Parsing timeout after {elapsed:.1f}s - returning partial results")
                return {
                    "Job Title": job_title,
                    "Company": "Unknown",
                    "Location": "Unknown"
                }

            company = _parse_company_fast(driver)

            # Check if cancelled after company parsing
            if cancelled_callback and cancelled_callback():
                print("Parsing cancelled after company extraction")
                return None

            elapsed = time.time() - start_time
            if elapsed > JobParserConfig.TOTAL_PARSE_TIMEOUT:
                print(f"Parsing timeout after {elapsed:.1f}s - returning partial results")
                return {
                    "Job Title": job_title,
                    "Company": company,
                    "Location": "Unknown"
                }

            location = _parse_location_fast(driver)

            # Check if cancelled after location parsing
            if cancelled_callback and cancelled_callback():
                print("Parsing cancelled after location extraction")
                return None

            result = {
                "Job Title": job_title,
                "Company": company,
                "Location": location
            }

            elapsed = time.time() - start_time
            print(f"Successfully parsed job info in {elapsed:.1f}s: ", result)
            return result

    finally:
        # Cancel the alarm
        try:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
        except:
            pass

def _parse_job_title_fast(driver):
    """Fast job title parsing with improved selectors"""
    selectors = [
        # Common job title selectors
        "//h1",
        "//h2",
        "//h3",
        # LinkedIn specific
        "//*[contains(@class, 'jobs-unified-top-card__job-title')]",
        "//*[contains(@class, 'jobs-unified-top-card__job-title')]//span",
        # Indeed specific
        "//*[contains(@class, 'jobsearch-JobInfoHeader-title')]",
        "//*[contains(@class, 'jobsearch-JobInfoHeader-title')]//span",
        # Microsoft Careers specific
        "//*[contains(@class, 'job-details-title')]",
        "//*[contains(@class, 'job-details-title')]//span",
        # Greenhouse specific
        "//*[contains(@class, 'opening-title')]",
        "//*[contains(@class, 'opening-title')]//span",
        # Generic selectors
        "//*[contains(@class, 'job-title')]",
        "//*[contains(@class, 'jobTitle')]",
        "//*[contains(@class, 'title')]",
        "//*[contains(@id, 'jobTitle')]",
        "//*[contains(@id, 'job-title')]",
        # Meta tags
        "//meta[@property='og:title']",
        "//meta[@name='title']",
        # Title tag
        "//title"
    ]

    for selector in selectors:
        try:
            if selector.startswith("//meta"):
                elem = driver.find_element(By.XPATH, selector)
                title = elem.get_attribute("content").strip()
            elif selector == "//title":
                elem = driver.find_element(By.XPATH, selector)
                title = elem.text.strip()
                # Clean up title tag content
                title = title.replace(" - Careers", "").replace(" - Jobs", "")
                title = title.split("|")[0].strip()
            else:
                elem = driver.find_element(By.XPATH, selector)
                title = elem.text.strip()

            if title and len(title) > 3 and len(title) < 200:
                # Clean the title
                title = _clean_job_title(title)
                if _is_valid_job_title(title):
                    print(f"Job title found: {title}")
                    return title
        except Exception:
            continue

    print("Job title not found")
    return "Unknown"

def _parse_company_fast(driver):
    """Fast company parsing with improved selectors"""
    selectors = [
        # LinkedIn specific
        "//*[contains(@class, 'jobs-unified-top-card__company-name')]",
        "//*[contains(@class, 'jobs-unified-top-card__company-name')]//span",
        "//*[@data-testid='company-name']",
        # Indeed specific
        "//*[contains(@class, 'jobsearch-CompanyInfoContainer')]",
        "//*[contains(@class, 'jobsearch-CompanyInfoContainer')]//span",
        # Microsoft Careers specific
        "//*[contains(@class, 'company-name')]",
        "//*[contains(@class, 'company-name')]//span",
        # Greenhouse specific
        "//*[contains(@class, 'company-name')]",
        "//*[contains(@class, 'company-name')]//span",
        # Generic selectors
        "//*[contains(@class, 'company-name')]",
        "//*[contains(@class, 'companyName')]",
        "//*[contains(@class, 'employer-name')]",
        "//*[contains(@class, 'employerName')]",
        # Meta tags
        "//meta[@property='og:site_name']",
        "//meta[@name='company']",
        # Logo alt text
        "//img[contains(@class, 'company-logo')]/@alt",
        "//img[contains(@class, 'logo')]/@alt"
    ]

    for selector in selectors:
        try:
            if selector.startswith("//meta"):
                elem = driver.find_element(By.XPATH, selector)
                company = elem.get_attribute("content").strip()
            elif selector.endswith("/@alt"):
                elem = driver.find_element(By.XPATH, selector[:-5])
                company = elem.get_attribute("alt").strip()
            else:
                elem = driver.find_element(By.XPATH, selector)
                company = elem.text.strip()

            if company and len(company) > 1 and len(company) < 100:
                # Clean the company name
                company = _clean_company_name(company)
                if _is_valid_company_name(company):
                    print(f"Company found: {company}")
                    return company
        except Exception:
            continue

    print("Company not found")
    return "Unknown"

def _parse_location_fast(driver):
    """Fast location parsing with improved selectors"""
    selectors = [
        # LinkedIn specific
        "//*[contains(@class, 'jobs-unified-top-card__bullet')]",
        "//*[contains(@class, 'jobs-unified-top-card__bullet')]//span",
        "//*[@data-testid='job-location']",
        # Indeed specific
        "//*[contains(@class, 'jobsearch-JobInfoHeader-subtitle')]",
        "//*[contains(@class, 'jobsearch-JobInfoHeader-subtitle')]//span",
        # Microsoft Careers specific
        "//*[contains(@class, 'job-details-location')]",
        "//*[contains(@class, 'job-details-location')]//span",
        # Greenhouse specific
        "//*[contains(@class, 'location')]",
        "//*[contains(@class, 'location')]//span",
        # Generic selectors
        "//*[contains(@class, 'location')]",
        "//*[contains(@class, 'job-location')]",
        "//*[contains(@class, 'workplace-type')]",
        # Meta tags
        "//meta[@property='og:locality']",
        "//meta[@name='location']"
    ]

    for selector in selectors:
        try:
            if selector.startswith("//meta"):
                elem = driver.find_element(By.XPATH, selector)
                location = elem.get_attribute("content").strip()
            else:
                elem = driver.find_element(By.XPATH, selector)
                location = elem.text.strip()

            if location and len(location) > 2 and len(location) < 100:
                # Clean the location
                location = _clean_location(location)
                if _is_valid_location(location):
                    print(f"Location found: {location}")
                    return location
        except Exception:
            continue

    # Fallback: Look for location-like text in the page
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text
        location_patterns = [
            r'\b(Remote|Hybrid|On-site|Onsite)\b',
            r'\b[A-Z][a-z]+,\s*[A-Z]{2}\b',  # City, State
            r'\b[A-Z][a-z]+,\s*[A-Z][a-z]+\b',  # City, Country
            r'\b[A-Z][a-z]+\s*,\s*[A-Z]{2}\s*\d{5}\b'  # City, State ZIP
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                location = matches[0]
                if _is_valid_location(location):
                    print(f"Location found via pattern: {location}")
                    return location
    except Exception:
        pass

    print("Location not found")
    return "Unknown"

def _clean_location(location):
    """Clean and normalize location text"""
    if not location:
        return ""

    # Remove common prefixes/suffixes
    location = location.replace("Location:", "").replace("Work Location:", "")
    location = location.replace("Job Location:", "").replace("Office Location:", "")

    # Normalize common variations
    location_lower = location.lower().strip()

    if 'remote' in location_lower or 'wfh' in location_lower or 'work from home' in location_lower:
        return "Remote"
    elif 'hybrid' in location_lower:
        return "Hybrid"
    elif 'on-site' in location_lower or 'onsite' in location_lower or 'in-office' in location_lower:
        return "On-site"

    # Remove extra whitespace
    location = " ".join(location.split())

    return location.strip()

def _is_valid_location(location):
    """Check if the extracted text looks like a valid location"""
    if not location or len(location) < 2:
        return False

    location_lower = location.lower().strip()

    # Valid location indicators
    location_indicators = [
        'remote', 'hybrid', 'on-site', 'onsite', 'in-office',
        'united states', 'usa', 'us', 'canada', 'uk', 'europe'
    ]

    # Check for location indicators
    has_location_indicator = any(indicator in location_lower for indicator in location_indicators)

    # Check for city, state format
    has_city_state = bool(re.search(r'[A-Z][a-z]+,\s*[A-Z]{2}', location))

    # Exclude common non-location text
    excludes = [
        'apply', 'requirements', 'responsibilities', 'description',
        'qualifications', 'benefits', 'salary', 'company', 'job',
        'experience', 'skills', 'education', 'degree'
    ]

    has_excludes = any(exclude in location_lower for exclude in excludes)

    # Should be reasonable length
    word_count = len(location.split())
    reasonable_length = 1 <= word_count <= 6

    return (has_location_indicator or has_city_state) and not has_excludes and reasonable_length

def _parse_job_requisition_fast(driver):
    """Ultra-fast job requisition parsing"""
    try:
        selectors = ["//*[contains(@class, 'job-id')]", "//*[@data-job-id]"]

        for selector in selectors:
            try:
                if "@data-job-id" in selector:
                    elem = driver.find_element(By.XPATH, selector)
                    req = elem.get_attribute("data-job-id").strip()
                else:
                    elem = driver.find_element(By.XPATH, selector)
                    req = elem.text.strip()

                if req and len(req) > 2 and len(req) < 50:
                    print("Job requisition found: ", req)
                    return req
            except:
                continue
    except:
        pass

    return "Unknown"

def _parse_job_requisition(driver):
    """Parse job requisition with simplified fast strategies"""
    job_req = "Unknown"

    # Simplified job requisition detection
    req_selectors = [
        "//*[contains(@class, 'job-id')]",
        "//*[contains(@class, 'jobId')]",
        "//*[contains(@class, 'requisition')]",
        "//*[@data-job-id]",
        "//*[@data-testid='job-id']",
        "//*[contains(@id, 'job-id')]",
        "//*[contains(@id, 'requisition')]",
        "//*[contains(@class, 'reference')]",
        "//*[contains(@class, 'posting-id')]",
        "//*[@data-requisition]",
    ]

    for idx, selector in enumerate(req_selectors[:JobParserConfig.MAX_SELECTORS_PER_FUNCTION]):
        try:
            if "@data-job-id" in selector or "@data-requisition" in selector or "@data-reference" in selector:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.get_attribute("data-job-id") or elem.get_attribute("data-requisition") or elem.get_attribute("data-reference")
                text = text.strip() if text else ""
            else:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.text.strip()

            if text and len(text) > 2 and len(text) < 50:
                job_req = text
                print("Job requisition found: ", job_req)
                break
        except:
            continue

    if job_req == "Unknown":
        print("Job requisition not found from selectors")

    return job_req

def _parse_job_type_fast(driver):
    """Ultra-fast job type parsing"""
    try:
        # LinkedIn specific selectors
        linkedin_selectors = [
            "//*[contains(@class, 'jobs-unified-top-card__job-insight')]//span",
            "//*[contains(@class, 'jobs-unified-top-card__workplace-type')]",
            "//*[@data-testid='job-type']",
            "//*[contains(@class, 'jobs-search__job-details--type')]",
            "//*[contains(@class, 'jobs-search__job-details--type')]//span"
        ]

        for selector in linkedin_selectors:
            try:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.text.strip().lower()

                # Enhanced job type detection
                if 'full' in text and 'time' in text:
                    return "Full-time"
                elif 'part' in text and 'time' in text:
                    return "Part-time"
                elif 'contract' in text:
                    return "Contract"
                elif 'remote' in text or 'wfh' in text or 'work from home' in text:
                    return "Remote"
                elif 'hybrid' in text:
                    return "Hybrid"
                elif 'on-site' in text or 'onsite' in text or 'in-office' in text:
                    return "On-site"
                elif 'intern' in text or 'internship' in text:
                    return "Internship"
                elif 'temporary' in text or 'temp' in text:
                    return "Temporary"
                elif 'permanent' in text or 'perm' in text:
                    return "Permanent"
            except:
                continue

        # Quick text search only
        import re
        page_text = driver.find_element(By.TAG_NAME, "body").text[:1000]  # Only first 1000 chars
        if re.search(r'\bfull[\s-]?time\b', page_text, re.IGNORECASE):
            return "Full-time"
        elif re.search(r'\bpart[\s-]?time\b', page_text, re.IGNORECASE):
            return "Part-time"
        elif re.search(r'\bcontract\b', page_text, re.IGNORECASE):
            return "Contract"
        elif re.search(r'\bremote\b|\bwfh\b|\bwork\s+from\s+home\b', page_text, re.IGNORECASE):
            return "Remote"
        elif re.search(r'\bhybrid\b', page_text, re.IGNORECASE):
            return "Hybrid"
        elif re.search(r'\bon[\s-]?site\b|\bin[\s-]?office\b', page_text, re.IGNORECASE):
            return "On-site"
    except:
        pass

    return "Unknown"

def _parse_job_title(driver):
    """Parse job title with comprehensive strategies based on modern job posting patterns"""
    job_title = "Unknown"

    # Top 5 most reliable selectors only (for speed)
    title_selectors = [
        "//h1",  # Most common and reliable
        "//*[contains(@class, 'jobsearch-JobInfoHeader-title')]",  # Indeed
        "//*[contains(@class, 'jobs-unified-top-card__job-title')]",  # LinkedIn
        "//*[contains(@class, 'job-title')]",  # Generic
        "//title",  # Fallback
    ]

    for idx, selector in enumerate(title_selectors[:JobParserConfig.MAX_SELECTORS_PER_FUNCTION]):
        try:
            if selector.startswith("//meta") or selector == "//title":
                elem = driver.find_element(By.XPATH, selector)
                text = elem.get_attribute("content") if selector.startswith("//meta") else elem.text
                text = text.strip() if text else ""
            else:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.text.strip()

            if text and len(text) > 3 and len(text) < 200:  # Reasonable length limits
                # Clean the title
                cleaned_text = _clean_job_title(text)
                if _is_valid_job_title(cleaned_text):
                    job_title = cleaned_text
                    print("Job title found: ", job_title)
                    break
        except:
            continue

    if job_title == "Unknown":
        print("Job title not found with known selectors")

    return job_title

def _clean_job_title(title):
    """Clean and normalize job title text"""
    if not title:
        return ""

    # Remove common prefixes/suffixes
    title = title.replace("Job Title:", "").replace("Position:", "").replace("Role:", "")
    title = title.replace("n- job post", "").replace("- job post", "")
    title = title.replace("Apply for", "").replace("Apply to", "")

    # Remove extra whitespace and newlines
    title = " ".join(title.split())

    return title.strip()

def _is_valid_job_title(title):
    """Check if the extracted text looks like a valid job title"""
    if not title or len(title) < 3:
        return False

    # Common non-title patterns to exclude
    exclude_patterns = [
        'apply now', 'click here', 'view job', 'see more', 'job search',
        'company profile', 'about us', 'contact', 'privacy policy',
        'terms of service', 'cookie policy', 'home', 'careers'
    ]

    title_lower = title.lower()
    return not any(pattern in title_lower for pattern in exclude_patterns)

def _parse_company(driver):
    """Parse company with simplified fast strategies"""
    company_selectors = [
        "//meta[@property='og:site_name']",  # Most reliable
        "//*[contains(@class, 'jobsearch-CompanyInfoContainer')]",  # Indeed
        "//*[contains(@class, 'jobs-unified-top-card__company-name')]",  # LinkedIn
        "//*[contains(@class, 'company-name')]",  # Generic
        "//*[contains(@class, 'companyName')]",  # Generic alt
    ]

    for idx, selector in enumerate(company_selectors[:JobParserConfig.MAX_SELECTORS_PER_FUNCTION]):
        try:
            if selector.startswith("//meta"):
                elem = driver.find_element(By.XPATH, selector)
                company = elem.get_attribute("content").strip()
            elif selector.endswith("/@alt"):
                elem = driver.find_element(By.XPATH, selector)
                company = elem.get_attribute("alt").strip()
            elif "@data-company-name" in selector:
                elem = driver.find_element(By.XPATH, selector)
                company = elem.get_attribute("data-company-name").strip()
            else:
                elem = driver.find_element(By.XPATH, selector)
                company = elem.text.strip()

            if company and len(company) > 1 and len(company) < 100:
                cleaned_company = _clean_company_name(company)
                if _is_valid_company_name(cleaned_company):
                    print("Company found: ", cleaned_company)
                    return cleaned_company
        except:
            continue

    print("Company not found from selectors")
    return "Unknown"

def _clean_company_name(company):
    """Clean and normalize company name"""
    if not company:
        return ""

    # Remove common suffixes/prefixes
    company = company.replace("Company:", "").replace("Employer:", "")
    company = company.replace("Jobs at", "").replace("Careers at", "")
    company = company.replace("- Jobs", "").replace("- Careers", "")

    # Remove extra whitespace
    company = " ".join(company.split())

    return company.strip()

def _is_valid_company_name(company):
    """Check if the extracted text looks like a valid company name"""
    if not company or len(company) < 2:
        return False

    # Exclude common non-company patterns
    exclude_patterns = [
        'apply', 'job', 'career', 'hiring', 'search', 'find', 'browse',
        'view all', 'see more', 'click here', 'home', 'about', 'contact',
        'privacy', 'terms', 'cookie', 'login', 'sign in', 'register'
    ]

    company_lower = company.lower()
    return not any(pattern in company_lower for pattern in exclude_patterns)

def _parse_location(driver):
    """Parse location with simplified fast logic"""
    location = "Unknown"

    # Top 5 location selectors only
    location_selectors = [
        "//*[contains(@class, 'jobsearch-JobInfoHeader-subtitle')]",  # Indeed
        "//*[contains(@class, 'jobs-unified-top-card__bullet')]",  # LinkedIn
        "//*[contains(@class, 'location')]",  # Generic
        "//*[contains(@class, 'job-location')]",  # Generic alt
        "//*[@data-testid='job-location']",  # Modern sites
    ]

    # Try specific location selectors (limited for performance)
    for idx, selector in enumerate(location_selectors[:JobParserConfig.MAX_SELECTORS_PER_FUNCTION]):
        try:
            elem = driver.find_element(By.XPATH, selector)
            text = elem.text.strip()
            if text and _is_valid_location(text):
                location = _clean_location(text)
                print("Location found: ", location)
                return location
        except:
            continue

    # Skip slow text pattern matching for speed

    if location == "Unknown":
        print("Location not confidently detected")

    return location

def _clean_location(location):
    """Clean and normalize location text"""
    if not location:
        return ""

    # Remove common prefixes/suffixes
    location = location.replace("Location:", "").replace("Address:", "")
    location = location.replace("City:", "").replace("Based in", "")

    # Normalize remote indicators
    remote_indicators = ['remote', 'work from home', 'wfh', 'telecommute', 'virtual']
    location_lower = location.lower()
    for indicator in remote_indicators:
        if indicator in location_lower:
            return "Remote"

    # Remove extra whitespace
    location = " ".join(location.split())

    return location.strip()

def _is_valid_location(text):
    """Enhanced location validation"""
    if not text or len(text) < 2:
        return False

    text_lower = text.lower().strip()

    # Valid location indicators
    location_indicators = [
        ',',  # City, State format
        'remote', 'work from home', 'wfh', 'telecommute', 'virtual',
        'united states', 'usa', 'us', 'canada', 'uk', 'united kingdom',
        # State abbreviations
        ' ca', ' ny', ' tx', ' fl', ' wa', ' il', ' pa', ' oh', ' ga', ' nc', ' mi',
        ' nj', ' va', ' ma', ' tn', ' in', ' az', ' mo', ' md', ' wi', ' co', ' mn',
        # State full names (partial list)
        'california', 'new york', 'texas', 'florida', 'washington', 'illinois'
    ]

    # Check for location indicators
    has_location_indicator = any(indicator in text_lower for indicator in location_indicators)

    # Exclude common non-location phrases (but not if they're part of remote work phrases)
    excludes = [
        'apply', 'requirements', 'responsibilities', 'description', 'qualifications',
        'benefits', 'salary', 'company', 'job', 'career', 'position', 'role',
        'experience', 'skills', 'education', 'degree', 'years', 'team',
        'manage', 'develop', 'create', 'build', 'design', 'implement', 'support',
        'maintain', 'improve', 'ensure', 'provide', 'deliver', 'lead', 'drive'
    ]

    # Check for excludes, but ignore if it's a remote work phrase
    remote_work_phrases = ['work from home', 'work remotely', 'remote work']
    is_remote_work_phrase = any(phrase in text_lower for phrase in remote_work_phrases)

    has_excludes = any(exclude in text_lower for exclude in excludes) and not is_remote_work_phrase

    # Should be reasonable length (not too long or too short)
    word_count = len(text.split())
    reasonable_length = 1 <= word_count <= 10

    # Additional checks for common location patterns
    import re

    # US City, State pattern
    us_pattern = r'\b\w+,\s*[A-Z]{2}\b'
    is_us_location = bool(re.search(us_pattern, text))

    # Remote pattern
    remote_pattern = r'\b(remote|wfh|work from home|telecommute|virtual)\b'
    is_remote = bool(re.search(remote_pattern, text, re.IGNORECASE))

    return ((has_location_indicator or is_us_location or is_remote) and
            not has_excludes and reasonable_length)

def _parse_job_type(driver):
    """Parse job type (Full-time, Part-time, Contract, etc.) with simplified fast strategies"""
    job_type = "Unknown"

    # Simplified job type detection for performance
    type_selectors = [
        "//*[contains(@class, 'job-type')]",
        "//*[contains(@class, 'jobType')]",
        "//*[contains(@class, 'employment-type')]",
        "//*[contains(@class, 'jobsearch-JobInfoHeader-subtitle')]",  # Indeed
        "//*[contains(@class, 'jobs-unified-top-card__job-insight')]",  # LinkedIn
        "//*[@data-testid='job-type']",
        "//*[contains(@class, 'schedule')]",
        "//*[contains(@id, 'job-type')]",
        "//*[@data-job-type]",
        "//div[contains(@itemtype, 'JobPosting')]//span[@itemprop='employmentType']",
    ]

    # Try specific job type selectors (limited for performance)
    for idx, selector in enumerate(type_selectors[:JobParserConfig.MAX_SELECTORS_PER_FUNCTION]):
        try:
            if "@data-job-type" in selector:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.get_attribute("data-job-type").strip()
            else:
                elem = driver.find_element(By.XPATH, selector)
                text = elem.text.strip()

            if text and _is_valid_job_type(text):
                job_type = _clean_job_type(text)
                print("Job type found: ", job_type)
                return job_type
        except:
            continue

    # Quick text search for common job types only
    try:
        import re
        page_text = driver.find_element(By.TAG_NAME, "body").text
        # Only look for most obvious patterns
        if re.search(r'\bfull[\s-]?time\b', page_text, re.IGNORECASE):
            job_type = "Full-time"
            print("Job type found via quick pattern: ", job_type)
            return job_type
        elif re.search(r'\bpart[\s-]?time\b', page_text, re.IGNORECASE):
            job_type = "Part-time"
            print("Job type found via quick pattern: ", job_type)
            return job_type
        elif re.search(r'\bcontract\b', page_text, re.IGNORECASE):
            job_type = "Contract"
            print("Job type found via quick pattern: ", job_type)
            return job_type
    except:
        pass

    if job_type == "Unknown":
        print("Job type not confidently detected")

    return job_type

def _clean_job_type(job_type):
    """Clean and normalize job type text"""
    if not job_type:
        return ""

    # Remove common prefixes/suffixes
    job_type = job_type.replace("Job Type:", "").replace("Employment Type:", "")
    job_type = job_type.replace("Work Type:", "").replace("Schedule:", "")

    # Normalize common variations
    job_type_lower = job_type.lower().strip()

    if 'full' in job_type_lower and 'time' in job_type_lower:
        return "Full-time"
    elif 'part' in job_type_lower and 'time' in job_type_lower:
        return "Part-time"
    elif 'contract' in job_type_lower:
        return "Contract"
    elif 'temp' in job_type_lower:
        return "Temporary"
    elif 'permanent' in job_type_lower or 'perm' in job_type_lower:
        return "Permanent"
    elif 'freelance' in job_type_lower:
        return "Freelance"
    elif 'intern' in job_type_lower:
        return "Internship"
    elif 'volunteer' in job_type_lower:
        return "Volunteer"
    elif 'seasonal' in job_type_lower:
        return "Seasonal"
    elif 'remote' in job_type_lower or 'wfh' in job_type_lower or 'work from home' in job_type_lower:
        return "Remote"
    elif 'hybrid' in job_type_lower:
        return "Hybrid"
    elif 'on-site' in job_type_lower or 'onsite' in job_type_lower or 'in-office' in job_type_lower:
        return "On-site"

    # Remove extra whitespace
    job_type = " ".join(job_type.split())

    return job_type.strip()

def _is_valid_job_type(text):
    """Check if the extracted text looks like a valid job type"""
    if not text or len(text) < 3:
        return False

    text_lower = text.lower().strip()

    # Valid job type indicators
    job_type_indicators = [
        'full', 'part', 'time', 'contract', 'temp', 'permanent', 'perm',
        'freelance', 'intern', 'volunteer', 'seasonal', 'remote', 'hybrid',
        'on-site', 'onsite', 'wfh', 'work from home', 'in-office'
    ]

    # Check for job type indicators
    has_job_type_indicator = any(indicator in text_lower for indicator in job_type_indicators)

    # Exclude common non-job-type phrases
    excludes = [
        'apply', 'requirements', 'responsibilities', 'description', 'qualifications',
        'benefits', 'salary', 'company', 'location', 'experience', 'skills',
        'education', 'degree', 'years', 'team', 'manage', 'develop', 'create'
    ]

    has_excludes = any(exclude in text_lower for exclude in excludes)

    # Should be reasonable length
    word_count = len(text.split())
    reasonable_length = 1 <= word_count <= 5

    return has_job_type_indicator and not has_excludes and reasonable_length
