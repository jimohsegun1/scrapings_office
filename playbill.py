import re
import os
import time
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime, timedelta
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

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.show-container"))
        )
        cards = driver.find_elements(By.CSS_SELECTOR, "div.show-container")
        log_and_print(f"📦 Found {len(cards)} show cards on the main page.")

        links = []
        for i, card in enumerate(cards):
            try:
                title_element = card.find_element(By.CSS_SELECTOR, "div.prod-title a")
                name = title_element.text
                link = title_element.get_attribute("href")
                img_src = card.find_element(
                    By.CSS_SELECTOR, "div.cover-container img"
                ).get_attribute("src")
                venue_element = card.find_element(By.CSS_SELECTOR, "div.prod-venue a")
                # venue_name = venue_element.text
                venue_name = venue_element.text.replace("Theatre", "").strip()
                venue_link = venue_element.get_attribute("href")

                if link:
                    links.append(
                        {
                            "Name": name,
                            "Link": link,
                            "image url": img_src,
                            "venue_name": venue_name,
                            "venue_link": venue_link,
                        }
                    )
                    # log_and_print(f"🔗 [{i+1}] Found show: {name} - {link}")
            except NoSuchElementException as e:
                log_and_print(f"Error finding elements in card: {e}")

        wait = WebDriverWait(driver, 10)
        actions = ActionChains(driver)

        all_scraped_data = []

        for idx, entry in enumerate(links):
            log_and_print(
                f"\n➡️ Visiting show #{idx + 1}: {entry['Name']} ({entry['Link']} {entry['venue_name']})"
            )
            try:
                driver.get(entry["Link"])
                time.sleep(random.uniform(2, 4))

                try:
                    wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.bsp-bio-subtitle")
                        )
                    )
                    subtitle_elements = driver.find_elements(
                        By.CSS_SELECTOR, "div.bsp-bio-subtitle h5"
                    )

                    market = (
                        subtitle_elements[0].get_attribute("textContent").strip()
                        if len(subtitle_elements) > 0
                        else "N/A"
                    )
                    production_type = (
                        subtitle_elements[1].get_attribute("textContent").strip()
                        if len(subtitle_elements) > 1
                        else "N/A"
                    )
                    origin = (
                        subtitle_elements[2].get_attribute("textContent").strip()
                        if len(subtitle_elements) > 2
                        else "N/A"
                    )

                    try:
                        address_el = driver.find_element(
                            By.CSS_SELECTOR, "ul.bsp-bio-links li:nth-child(2) a"
                        )
                        full_address = address_el.text.strip()
                        if "New York" in full_address or full_address.endswith("NY"):
                            market_location = "New York (US)"
                        else:
                            market_location = "N/A"
                    except:
                        market_location = "N/A"

                    log_and_print(
                        f"🌍 Market: {market} | 🎭 Production Type: {production_type} | 📜 Origin: {origin}"
                    )
                    log_and_print(f"📍 Market Presence: {market_location}")
                except Exception as e:
                    log_and_print(f"⚠️ Could not extract production details: {e}")
                    market = production_type = origin = market_location = "N/A"

                # --- Extract production status and age ---
                status = "Unknown"
                age_of_production = "N/A"
                opening_date_str = "N/A"

                try:
                    date_blocks = driver.find_elements(
                        By.CSS_SELECTOR, "div.bsp-carousel-slide.with-circular-links"
                    )
                    for block in date_blocks:
                        try:
                            title_el = block.find_element(
                                By.CSS_SELECTOR, ".bsp-list-promo-title"
                            )
                            title = (
                                title_el.text.strip().upper()
                            )  # Normalize to match "OPENING DATE"
                        except:
                            continue

                        # Extract all span text parts and combine
                        span_texts = block.find_elements(
                            By.CSS_SELECTOR, ".info-circular span"
                        )
                        full_text = " ".join(
                            [
                                s.text.strip().upper()
                                for s in span_texts
                                if s.text.strip()
                            ]
                        )

                        log_and_print(f"🔍 {title} => Date Text: '{full_text}'")

                        if title == "OPENING DATE":
                            opening_date_str = full_text
                            try:
                                opening_dt = datetime.strptime(
                                    full_text.title(), "%b %d %Y"
                                )  # Normalize to title case
                                today = datetime.now()
                                years = (
                                    today.year
                                    - opening_dt.year
                                    - (
                                        (today.month, today.day)
                                        < (opening_dt.month, opening_dt.day)
                                    )
                                )
                                age_of_production = f"{years}"
                            except Exception as e:
                                log_and_print(f"⚠️ Failed parsing opening date: {e}")

                        elif title == "CLOSING DATE":
                            if "CURRENTLY RUNNING" in full_text:
                                status = "Active"
                            else:
                                try:
                                    closing_dt = datetime.strptime(
                                        full_text.title(), "%b %d %Y"
                                    )
                                    if closing_dt < datetime.now():
                                        status = "Closed"
                                    else:
                                        status = "Upcoming"
                                except:
                                    status = "Upcoming"

                    # Final fallback
                    if status == "Unknown" and opening_date_str != "N/A":
                        status = "Active"

                    log_and_print(f"📆 Opening Date: {opening_date_str}")
                    log_and_print(f"📅 Status: {status} | 🕰️ Age: {age_of_production}")

                except Exception as e:
                    log_and_print(f"⚠️ Could not extract status/age: {e}")

                # --- Extract schedule ---
                structured_schedule = []

                try:
                    schedule_block = driver.find_element(
                        By.CSS_SELECTOR, "div.bsp-bio-text"
                    ).text
                    date_blocks = [
                        block.strip()
                        for block in schedule_block.split("\n\n")
                        if "@" in block
                    ]

                    for block in date_blocks:
                        lines = block.split("\n")
                        print("📄 All lines in block:", lines)

                        date_range = ""
                        schedule_data = ""

                        if len(lines) >= 2:
                            schedule_line = lines[1].strip()
                            if ":" in schedule_line:
                                parts = schedule_line.split(":", 1)
                                date_range = parts[0].strip()
                                schedule_data = parts[1].strip()
                            else:
                                schedule_data = schedule_line
                        else:
                            continue

                        # 🧠 Parse actual dates from date_range (e.g. "June 24–29")
                        try:
                            year = datetime.now().year
                            month = date_range.split()[0]
                            day_start, day_end = map(
                                int, date_range.replace(month, "").split("–")
                            )
                            start_date = datetime.strptime(
                                f"{month} {day_start} {year}", "%B %d %Y"
                            )
                            day_map = {}
                            for i in range(day_end - day_start + 1):
                                d = start_date + timedelta(days=i)
                                weekday = d.strftime("%A").lower()
                                padded_date = d.strftime(
                                    "%B %d, %Y"
                                )  # <-- padded date e.g. June 24, 2025
                                day_map[weekday] = padded_date
                        except Exception as e:
                            log_and_print(
                                f"⚠️ Could not parse date range '{date_range}': {e}"
                            )
                            continue

                        # 🔄 Split entries by comma or 'and'
                        schedule_entries = re.split(r",|\band\b", schedule_data)
                        schedule_entries = [
                            s.strip() for s in schedule_entries if "@" in s
                        ]

                        for entry_str in schedule_entries:
                            try:
                                day_part, time_raw = entry_str.split("@")
                                day_name = day_part.strip().lower()
                                time_slot = time_raw.strip()

                                # Remove leftover day names from time
                                time_slot = re.sub(
                                    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
                                    "",
                                    time_slot,
                                    flags=re.IGNORECASE,
                                ).strip()

                                actual_date = day_map.get(day_name, "Unknown")

                                log_and_print(
                                    f"📅 Day: {actual_date} | ⏰ Time: {time_slot}"
                                )

                                structured_schedule.append(
                                    {
                                        "Name": entry["Name"],
                                        "Link": entry["Link"],
                                        "Image URL": entry["image url"],
                                        "Theatre": entry["venue_name"],
                                        # "Venue Link": entry["venue_link"],
                                        "Market": market,
                                        "Market Presence": market_location,
                                        "Production Type": production_type,
                                        "Origin": origin,
                                        "Status": status,
                                        "Age of Production (yrs)": age_of_production,
                                        "Date Range": date_range,
                                        "Date": actual_date,  # e.g. June 24, 2025
                                        "Time": time_slot,
                                        "Category": "show-production",
                                    }
                                )
                            except Exception as e:
                                log_and_print(
                                    f"⚠️ Failed parsing schedule entry '{entry_str}': {e}"
                                )

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

        if all_scraped_data:

            os.makedirs("data", exist_ok=True)  # Ensure 'data' folder exists
            filename = f"data/playbill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df = pd.DataFrame(all_scraped_data)
            df.to_csv(filename, index=False)
            log_and_print(f"📁 Data saved to {filename}")
        else:
            log_and_print("⚠️ No data to save.")


# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_shows()
