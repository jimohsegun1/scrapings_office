import os
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

# --- Config ---
RUN_HEADLESS = True
WAIT_TIMEOUT = 20
START_URL = "https://conspicuous.com/jobs/"

# --- Logging setup ---
if not os.path.exists("log"):
    os.makedirs("log")

log_file = os.path.join("log", "scrape_jobs.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_and_print(message):
    print(message)
    logging.info(message)

# --- Setup Chrome Driver ---
def setup_driver(headless=True):
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=options)
    if not headless:
        driver.maximize_window()
    return driver

# --- Scrape Function ---
def scrape_jobs():
    start_time = datetime.now()
    log_and_print(f"🚀 Scraping started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    driver = None

    try:
        driver = setup_driver(headless=RUN_HEADLESS)

        driver.get(START_URL)
        log_and_print(f"🌐 Navigated to {START_URL}")

        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "jobs-filter-results"))
        )
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-item"))
        )
        log_and_print("✅ Job listings loaded successfully.")

        page_number = 1

        while True:
            log_and_print(f"📄 On page {page_number} (scraping logic can be added here)")

            # --- Add scraping logic here if needed, e.g. parsing job cards ---

            # Try to go to the next page
            try:
                nav = driver.find_element(By.CLASS_NAME, "job-manager-pagination")
                next_button = nav.find_element(By.XPATH, './/a[text()="→"]')
                next_button.click()
                log_and_print("➡️ Clicked forward arrow to go to next page.")
                time.sleep(3)

                WebDriverWait(driver, WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "jobs-filter-results"))
                )
                WebDriverWait(driver, WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "job-item"))
                )

                page_number += 1

            except NoSuchElementException:
                log_and_print("🛑 No forward arrow found; last page reached.")
                break
            except Exception as e:
                log_and_print(f"⚠️ Error while paginating: {e}")
                break

        log_and_print("✅ Pagination complete.")

    except Exception as e:
        log_and_print(f"❌ Fatal error during scraping: {e}")

    finally:
        if driver:
            driver.quit()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        log_and_print(
            f"🏁 Scraping finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Duration: {duration:.2f} seconds)"
        )

# --- Main Execution ---
if __name__ == "__main__":
    scrape_jobs()
