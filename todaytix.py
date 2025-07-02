import re
import os
import time
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import random

# --- Configuration ---
RUN_HEADLESS = True  # <--- Change this to True or False
BASE_URL = "https://www.todaytix.com/"

# --- Setup logging ---
if not os.path.exists("log"):
    os.makedirs("log")
log_file = os.path.join("log", "scrape.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_and_print(message):
    print(message)
    logging.info(message)

# --- Hash function for (potential) deduplication ---
def hash_event(event):
    return hashlib.md5(json.dumps(event, sort_keys=True).encode()).hexdigest()

# --- Scraper Logic ---
def scrape_shows():
    start_time = datetime.now()
    log_and_print(f"🚀 Scraping started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    options = webdriver.ChromeOptions()
    if RUN_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")    
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    # options.add_argument("--disable-javascript")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )

    driver = None
    try:
        driver = uc.Chrome(options=options)
        
        try:
            driver.get(BASE_URL)
            log_and_print("🌐 Navigated to the website page.")
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            log_and_print(f"❌ Error navigating to the website page: {e}")
            
        # Wait for the page to load All Shows div
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[@id='reference-9=linkList']//div[2]"))
        )
        log_and_print("✅ All Shows section loaded successfully.")
        
        all_shows_link = driver.find_element(By.ID, "quick-link-0")
        all_shows_link.click()
        log_and_print("🔗 Clicked on 'All Shows' link.")
            








        log_and_print("🛌 Browser closed.")
    except Exception as e:
        log_and_print(f"❌ Fatal error in scraping function: {e}")

    finally:
        if driver:
            driver.quit()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        log_and_print(
            f"✅ Scraping finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Duration: {duration:.2f} seconds)"
        )

        # if all_scraped_data:

        #     os.makedirs("data", exist_ok=True)  # Ensure 'data' folder exists
        #     filename = f"data/broadway_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        #     df = pd.DataFrame(all_scraped_data)
        #     df.to_csv(filename, index=False)
        #     log_and_print(f"📁 Data saved to {filename}")
        # else:
        #     log_and_print("⚠️ No data to save.")

# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_shows()
