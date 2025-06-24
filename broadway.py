import re
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
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )

    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://www.broadway.com/shows/tickets/?view_all=true")
        log_and_print("🌐 Navigated to the website page.")
        time.sleep(random.uniform(2, 4))

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.showlistpage__bg-color"))
        )

        shows = driver.find_elements(By.CSS_SELECTOR, 'li.showlistpage__show-card-list--card-container')
        log_and_print(f"🔍 Found {len(shows)} shows.")

        links = []

        for i, card in enumerate(shows):
            try:
                title_element = card.find_element(By.CSS_SELECTOR, '[data-qa="show-name"]')
                title = title_element.text.strip()
                link = title_element.get_attribute("href")

                description = "N/A"
                desc_elements = card.find_elements(By.CSS_SELECTOR, '.showlistpage__show-card-list--show-description p')
                if desc_elements:
                    description = desc_elements[0].text.strip()

                img_url = "N/A"
                poster_imgs = card.find_elements(By.CSS_SELECTOR, '[data-qa="show-poster"] img')
                if poster_imgs:
                    img_url = poster_imgs[0].get_attribute('src') or poster_imgs[0].get_attribute('data-src')

                review_elements = card.find_elements(By.CSS_SELECTOR, '.showlistpage__show-card-list--total-customer-reviews')
                reviews = review_elements[0].text.strip("()") if review_elements else "N/A"

                price = "N/A"
                price_containers = card.find_elements(By.CSS_SELECTOR, '.showlistpage__show-card-list--pricing-container')

                for container in price_containers:
                    if "hide" not in container.get_attribute("class"):
                        try:
                            price = container.find_element(By.CSS_SELECTOR, '.showlistpage__show-card-list--show-price').text.strip()
                            break
                        except:
                            continue

                if link:
                    links.append({
                        "Title": title,
                        "Link": link,
                        "Description": description,
                        "Image URL": img_url,
                        "Reviews": reviews,
                        "Price": price
                    })
                    # log_and_print(f" [{i+1}] ✅ Extracted: {title} | {link} ")

            except Exception as e:
                log_and_print(f"⚠️ Error processing a show card: {e}")

        wait = WebDriverWait(driver, 10)
        actions = ActionChains(driver)

        all_scraped_data = []

        for i, item in enumerate(links):
            title = item["Title"]
            link = item["Link"]

            try:
                driver.get(link)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.showpage__contents")))
                log_and_print(f"[{i+1}] ➡️  Opened detail page for {title}")

                # try:
                #     calendar_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.showpage__calendar--button[data-qa="rsp-btn-view-calendar"]')))
                #     driver.execute_script("arguments[0].click();", calendar_button)
                #     log_and_print(f"🗓️ Clicked 'View Calendar' for {title}")
                #     time.sleep(random.uniform(2, 4))
                # except Exception as e:
                #     log_and_print(f"⚠️ 'View Calendar' not found or clickable for {title}: {e}")

                try:
                    calendar_buttons = driver.find_elements(By.CSS_SELECTOR, 'a.showpage__calendar--button[data-qa="rsp-btn-view-calendar"]')
                    if calendar_buttons and calendar_buttons[0].is_displayed() and calendar_buttons[0].is_enabled():
                        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.showpage__calendar--button[data-qa="rsp-btn-view-calendar"]')))
                        driver.execute_script("arguments[0].click();", calendar_buttons[0])
                        log_and_print(f"🗓️ Clicked 'View Calendar' for {title}")
                        time.sleep(random.uniform(2, 4))
                    else:
                        log_and_print(f"⚠️ 'View Calendar' button not visible or enabled for {title}")
                except Exception as e:
                    log_and_print(f"⚠️ Error trying to click 'View Calendar' for {title}: {e}")


                
                # --- Scrape calendar performances (dates + times) ---
                calendar_data = []

                while True:
                    try:
                        # Wait for calendar to render
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.CalendarBody__root__Anjr2')))

                        # Collect all active performance buttons
                        performance_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-qa="performance-button"]')


                        # for btn in performance_buttons:
                        #     try:
                        #         aria_label = btn.get_attribute("aria-label")
                        #         time_text = btn.text.strip()

                        #         if aria_label and time_text:
                        #             entry = {"date": aria_label, "time": time_text}
                        #             calendar_data.append(entry)
                        #             log_and_print(f"🟢 Found performance: {aria_label} at {time_text}")
                        #     except Exception as e:
                        #         log_and_print(f"⚠️ Error reading performance button: {e}")


                        # Get the current visible month + year (e.g., "June 2025")
                        # This is necessary to correctly parse the dates without a year


# ================

                        # Get the current visible month + year (e.g., "June 2025")
                        try:
                            current_month_year = driver.find_element(By.CSS_SELECTOR, '[data-qa="current-month-year"]').text.strip()
                            current_year = datetime.strptime(current_month_year, "%B %Y").year
                        except Exception as e:
                            log_and_print(f"⚠️ Failed to get current calendar year, using current system year: {e}")
                            current_year = datetime.now().year


                        for btn in performance_buttons:
                            try:
                                aria_label = btn.get_attribute("aria-label")
                                time_text = btn.text.strip()

                                if aria_label and time_text:
                                    # Extract full date part from aria-label using regex
                                    date_match = re.search(r'(\w+day, \w+ \d+)', aria_label)
                                    if date_match:
                                        date_part = date_match.group(1)

                                        # Remove ordinal suffixes (e.g., 28th -> 28)
                                        date_part = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_part)

                                        # Parse to datetime object
                                        date_obj = datetime.strptime(date_part, "%A, %b %d")

                                        # Attach correct year
                                        date_obj = date_obj.replace(year=current_year)
                                        formatted_date = date_obj.strftime("%Y-%m-%d")

                                        # Store performance info
                                        calendar_data.append({
                                            "date": formatted_date,
                                            "time": time_text
                                        })

                                        log_and_print(f"📅 {title} — {formatted_date} at {time_text}")
                                    else:
                                        log_and_print(f"⚠️ Could not extract date from '{aria_label}'")

                            except Exception as e:
                                log_and_print(f"⚠️ Error reading performance button: {e}")



# ================


                        # Move to next month if available
                        next_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-qa="right-arrow"]')
                        if next_btn.get_attribute("disabled"):
                            log_and_print("📅 No more future months. Exiting calendar.")
                            break

                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(random.uniform(1.5, 3))  # Let next month load
                    except Exception as e:
                        log_and_print(f"❌ Calendar scraping stopped: {e}")
                        break




            #     # ============================

            except Exception as e:
                log_and_print(f"❌ Error visiting detail page for {title}: {e}")




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

# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_shows()
