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
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--disable-javascript")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )
    
    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://playbill.com/shows/broadway")
        log_and_print("🌐 Navigated to https://playbill.com/shows/broadway page.")
        time.sleep(random.uniform(2, 4))

        # Wait for the show cards to be present
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.show-container")))
        cards = driver.find_elements(By.CSS_SELECTOR, "div.show-container")
        log_and_print(f"📦 Found {len(cards)} show cards on the main page.")
        
        links = []
        
        # Loop through each card to extract the required information
        for i, card in enumerate(cards):
            try:
                # Extract the name
                title_element = card.find_element(By.CSS_SELECTOR, "div.prod-title a")
                name = title_element.text
                link = title_element.get_attribute("href")
                
                # Extract the image
                img_element = card.find_element(By.CSS_SELECTOR, "div.cover-container img")
                img_src = img_element.get_attribute("src")

                # Extract the venue
                venue_element = card.find_element(By.CSS_SELECTOR, "div.prod-venue a")
                venue_name = venue_element.text
                venue_link = venue_element.get_attribute("href")
                
                if link:
                    # Append the details to the list
                    links.append({
                        "Name": name,
                        "Link": link,
                        "image url": img_src,
                        "venue_name": venue_name,
                        "venue_link": venue_link
                    })
                    log_and_print(f"🔗 [{i+1}] Found show: {name} - {link}")

            except NoSuchElementException as e:
                log_and_print(f"Error finding elements in card: {e}")

        wait = WebDriverWait(driver, 10)
        actions = ActionChains(driver)
        
        all_scraped_data = []

        # Iterate through each show link
        for idx, entry in enumerate(links):
            log_and_print(
                f"\n➡️ Visiting show #{idx + 1}: {entry['Name']} ({entry['Link']} {entry['venue_name']})"
            )
            try:
                driver.get(entry["Link"])
                time.sleep(random.uniform(2, 4))

                # --- Extract production details ---
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.bsp-bio-subtitle")))
                    subtitle_elements = driver.find_elements(By.CSS_SELECTOR, "div.bsp-bio-subtitle h5")

                    market = (
                        subtitle_elements[0].get_attribute("textContent").strip()
                        if len(subtitle_elements) > 0 else "N/A"
                    )
                    production_type = (
                        subtitle_elements[1].get_attribute("textContent").strip()
                        if len(subtitle_elements) > 1 else "N/A"
                    )
                    origin = (
                        subtitle_elements[2].get_attribute("textContent").strip()
                        if len(subtitle_elements) > 2 else "N/A"
                    )

                    # Get the state/city from address (Market Presence)
                    try:
                        address_el = driver.find_element(By.CSS_SELECTOR, "ul.bsp-bio-links li:nth-child(2) a")
                        market_location = address_el.text.strip()
                        if market_location.endswith("NY") or market_location.endswith("CA") or "New York" in market_location:
                            market_location += " (US)"
                    except:
                        market_location = "N/A"

                    log_and_print(f"🌍 Market: {market} | 🎭 Production Type: {production_type} | 📜 Origin: {origin}")
                    log_and_print(f"📍 Market Presence: {market_location}")
                except Exception as e:
                    log_and_print(f"⚠️ Could not extract production details: {e}")
                    market = production_type = origin = market_location = "N/A"

                # --- Extract schedule ---
                structured_schedule = []

                try:
                    schedule_block = driver.find_element(By.CSS_SELECTOR, "div.bsp-bio-text").text
                    date_blocks = [block.strip() for block in schedule_block.split("\n\n") if "@" in block]

                    for block in date_blocks:
                        lines = block.split("\n")
                        if not lines:
                            continue

                        date_range = lines[0].strip(": ").strip()
                        for line in lines[1:]:
                            if "@" in line:
                                parts = line.split("@")
                                day = parts[0].strip()
                                time_slot = parts[1].strip()

                                log_and_print(f"🗓️ Date Range: {date_range} | 📅 Day: {day} | ⏰ Time: {time_slot}")

                                structured_schedule.append({
                                    "Name": entry["Name"],
                                    "Link": entry["Link"],
                                    "Image URL": entry["image url"],
                                    "Venue Name": entry["venue_name"],
                                    "Venue Link": entry["venue_link"],
                                    "Market": market,
                                    "Market Presence": market_location,
                                    "Production Type": production_type,
                                    "Origin": origin,
                                    "Date Range": date_range,
                                    "Day": day,
                                    "Time": time_slot
                                })
                except Exception as e:
                    log_and_print(f"⚠️ Could not extract schedule: {e}")

                all_scraped_data.extend(structured_schedule)

                log_and_print(
                    f"📌 Finished scraping {entry['Name']} with {len(structured_schedule)} schedule entries.\n"
                )

            except Exception as e:
                log_and_print(f"🚫 Error scraping show {entry['Name']}: {e}")


        
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
# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_shows()  # Calls the scraper directly