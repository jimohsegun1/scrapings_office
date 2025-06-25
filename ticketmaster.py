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
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import random

# --- Configuration ---
# Set to True to run the browser without a visible GUI.
# Set to False to see the browser window during scraping.
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
def scrape_shows():  # No longer takes 'headless_mode' as an argument
    start_time = datetime.now()
    log_and_print(f"🚀 Scraping started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    options = webdriver.ChromeOptions()
    if RUN_HEADLESS:  # Uses the global RUN_HEADLESS variable
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
        driver.get("https://www.ticketmaster.com/broadway")
        log_and_print("🌐 Navigated to Broadway Ticketmaster page.")
        time.sleep(random.uniform(2, 4))

        soup = BeautifulSoup(driver.page_source, "lxml")
        cards = soup.find_all("div", class_="card item ny-category-musicals ny")
        log_and_print(f"📦 Found {len(cards)} show cards on the main page.")

        links = []
        for i, item in enumerate(cards):
            name = item.find("h3").text.strip() if item.find("h3") else "N/A"
            link = item.find("a")["href"] if item.find("a") else ""
            img = item.find("img")["src"] if item.find("img") else ""
            if link:
                links.append({"Name": name, "Link": link, "Image url": img})
                log_and_print(f"🔗 [{i+1}] Found show: {name} - {link}")

        wait = WebDriverWait(driver, 10)
        actions = ActionChains(driver)
        
        all_scraped_data = []

        for idx, entry in enumerate(links):
            log_and_print(
                f"\n➡️ Visiting show #{idx + 1}: {entry['Name']} ({entry['Link']})"
            )
            try:
                driver.get(entry["Link"])
                time.sleep(random.uniform(2, 4))

                try:
                    wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//*[@id="pageInfo"]/div[1]/ul/li[1]/button')
                        )
                    ).click()
                    log_and_print("🧭 Expanded the event listing.")
                    time.sleep(random.uniform(2, 3))
                except Exception:
                    pass

                event_count_current_show = 0
                while True:
                    soup = BeautifulSoup(driver.page_source, "lxml")
                    events = soup.find_all("li", class_="sc-a4c9d98c-1 gmqiju")
                    log_and_print(f"🔍 Found {len(events)} event listings.")

                    for i, event in enumerate(events):
                        try:
                            date = event.find("div", class_="sc-d4c18b64-0 kViXXz")
                            time_ = event.find("span", class_="sc-5ae165d4-1 xHFfV")
                            span_tags = event.find_all(
                                "span", class_="sc-cce7ae2b-8 eHUDaT"
                            )
                            thea = span_tags[-1] if len(span_tags) > 0 else None
                            loc = span_tags[-2] if len(span_tags) > 1 else None

                            show_info = {
                                "Show": entry["Name"],
                                "Link": entry["Link"],
                                "Image url": entry["Image url"],
                                "Theatre": thea.text.strip() if thea else "",
                                "Date": date.text.strip() if date else "",
                                "Time": time_.text.strip() if time_ else "",
                                "Location": loc.text.strip() if loc else "",
                            }

                            all_scraped_data.append(show_info)
                            event_count_current_show += 1
                            log_and_print(
                                f"✅ Scraped event: {show_info['Date']} - {show_info['Time']} @ {show_info['Theatre']}"
                            )

                        except Exception:
                            pass

                    try:
                        more_events_button = wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//span[text()='More Events']/ancestor::button",
                                )
                            )
                        )
                        actions.move_to_element(more_events_button).perform()
                        more_events_button.click()
                        log_and_print("📥 Loaded more events.")
                        time.sleep(2)
                    except:
                        log_and_print("🔚 No more events to load.")
                        break

                log_and_print(
                    f"📌 Finished scraping {entry['Name']} with {event_count_current_show} events processed.\n"
                )

            except Exception:
                pass

        log_and_print("🛑 Browser closed.")

        if all_scraped_data:
            log_and_print(f"🎉 Total events scraped: {len(all_scraped_data)}")
        else:
            log_and_print("📭 No events scraped.")

        if not os.path.exists("data"):
            os.makedirs("data")

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = f"data/ticketmaster_{now}.json"
        csv_path = f"data/ticketmaster_{now}.csv"

        pd.DataFrame(all_scraped_data).to_json(json_path, orient="records", indent=2)
        pd.DataFrame(all_scraped_data).to_csv(csv_path, index=False)

        log_and_print(f"💾 Scraped data exported to:\n - {json_path}\n - {csv_path}")

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
