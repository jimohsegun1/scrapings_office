import os
import time
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime
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
    options.add_argument("--disable-javascript")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US,en;q=0.9")
    # options.add_argument("--disable-javascript")  used when you're scraping a static site

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )
    
    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://www.broadway.com/shows/tickets/?view_all=true")
        log_and_print("🌐 Navigated to the website page.")
        time.sleep(random.uniform(2, 4))

        # Wait for the show cards to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.showlistpage__bg-color"))
        )

        shows = driver.find_elements(By.CSS_SELECTOR, 'li.showlistpage__show-card-list--card-container')
        log_and_print(f"🔍 Found {len(shows)} shows.")

        data = []

        for i, card in enumerate(shows):
            try:
                title = card.find_element(By.CSS_SELECTOR, '[data-qa="show-name"]').text.strip()

                #  Description, Some shows might not have a description, so we handle that gracefully
                description = "N/A"
                desc_elements = card.find_elements(By.CSS_SELECTOR, '.showlistpage__show-card-list--show-description p')
                if desc_elements:
                    description = desc_elements[0].text.strip()

                # Image URL, Some shows might not have an image, so we handle that gracefully
                img_url = "N/A"
                poster_imgs = card.find_elements(By.CSS_SELECTOR, '[data-qa="show-poster"] img')
                if poster_imgs:
                    img_url = poster_imgs[0].get_attribute('src') or poster_imgs[0].get_attribute('data-src')

                # Reviews, Some shows might not have reviews, so we handle that gracefully
                review_elements = card.find_elements(By.CSS_SELECTOR, '.showlistpage__show-card-list--total-customer-reviews')
                reviews = review_elements[0].text.strip("()") if review_elements else "N/A"

                # Price, Some shows might not have a price listed, so we handle that gracefully
                price = "N/A"
                price_containers = card.find_elements(By.CSS_SELECTOR, '.showlistpage__show-card-list--pricing-container')

                for container in price_containers:
                    if "hide" not in container.get_attribute("class"):
                        try:
                            price = container.find_element(By.CSS_SELECTOR, '.showlistpage__show-card-list--show-price').text.strip()
                            break
                        except:
                            continue

                log_and_print(f" [{i+1}] ✅ Extracted: {title} | {description} | {img_url} | {reviews} | {price}")

                data.append({
                    "title": title,
                    "description": description,
                    "image_url": img_url,
                    "reviews": reviews,
                    "price": price
                })

            except Exception as e:
                log_and_print(f"⚠️ Error processing a show card: {e}")

        
        log_and_print("🛑 Browser closed.")

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

        # Save data to a CSV file
        if data:
            os.makedirs("data", exist_ok=True)  # Ensure 'data' folder exists
            filename = f"data/broadway_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            # Truncate description field
            for entry in data:
                full_desc = entry.get("description", "")
                if len(full_desc) > 30:
                    entry["description"] = full_desc[:27] + "..."

            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding="utf-8-sig")

            log_and_print(f"📁 Data saved to {filename}")
        else:
            log_and_print("⚠️ No data to save.")

       

# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_shows()
