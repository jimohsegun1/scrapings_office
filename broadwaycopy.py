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
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--window-size=1920,1080")  # Set browser window size
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

        # GET SOME DETAILS ON THE CARD LIST PAGE
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

        # ========  ITERATE THROUGH EACH SHOW CARD AND  ============
        for i, item in enumerate(links):
            title = item["Title"]
            link = item["Link"]

            try:
                # driver.get(link)
                # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.showpage__contents")))
                # log_and_print(f"[{i+1}] ➡️  Opened detail page for {title}")

                try:
                    driver.get(link)
                except Exception as e:
                    log_and_print(f"⚠️ Timeout loading page for {title}. Retrying after 5 seconds...")
                    time.sleep(5)
                    try:
                        driver.get(link)
                    except Exception as e:
                        log_and_print(f"❌ Retry failed for {title}: {e}")
                        continue

                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.showpage__contents")))
                    log_and_print(f"[{i+1}] ➡️  Opened detail page for {title}")
                except Exception as e:
                    log_and_print(f"❌ Could not load detail content for {title}: {e}")
                    continue

                # locate and click the "View Calendar" button
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

                
                # ========  Scrape calendar performances (dates + times) ============
                calendar_data = []

                while True:

                    # Calendar scraping logic
                    try:
                        # Wait for calendar to render
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.CalendarBody__root__Anjr2')))

                        # Collect all active performance buttons
                        performance_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-qa="performance-button"]')


                        # Get the current visible month + year (e.g., "June 2025")
                        try:
                            current_month_year = driver.find_element(By.CSS_SELECTOR, '[data-qa="current-month-year"]').text.strip()
                            current_year = datetime.strptime(current_month_year, "%B %Y").year
                        except Exception as e:
                            log_and_print(f"⚠️ Failed to get current calendar year, using current system year: {e}")
                            current_year = datetime.now().year

                        #################################
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

                                        # Determine status
                                        today = date.today()
                                        performance_day = date_obj.date()
                                        
                                        if performance_day == today:
                                            status = "active"
                                        elif performance_day > today:
                                            status = "upcoming"
                                        elif performance_day < today:
                                            status = "closed"
                                        else:
                                            status = "N/A"

                                        calendar_data.append({
                                            "date": formatted_date,
                                            "time": time_text,
                                            "status": status
                                        })

                                        log_and_print(f"📅 {title} — {formatted_date} at {time_text} ({status})")
                                    else:
                                        log_and_print(f"⚠️ Could not extract date from '{aria_label}'")

                            except Exception as e:
                                log_and_print(f"⚠️ Error reading performance button: {e}")

                        #################################


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
                # calendar scraping logic ends here

                # Go back to card details page
                driver.back()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.showpage__contents")))
                log_and_print(f"[{i+1}] ➡️  Back to detail page for {title}")
                time.sleep(2)

                # Production type
                production_type = "N/A"
                try:
                    category_section = driver.find_element(By.CSS_SELECTOR, "div.showpage__story--categories")
                    log_and_print(f"✅ 'Categories' section found for {title}")
                    
                    category_links = category_section.find_elements(By.CSS_SELECTOR, "a.showpage__story--button")
                    categories_text = [link.text.strip().lower() for link in category_links]

                    if any("musicals" in cat for cat in categories_text):
                        production_type = "Musicals"    
                    elif any("plays" in cat for cat in categories_text):
                        production_type = "Plays"                        
                    else:
                        production_type = "N/A"

                except Exception:
                    log_and_print(f"⚠️ No 'Categories' section found for {title}; defaulting to production_type = N/A")

                log_and_print(f"🎭 Production Type for '{title}': {production_type}")

                # Origin
                origin = "N/A"
                log_and_print(f"🔍'Origin' for {title} is {origin} ")

                # Category
                category = "show-production"

                # Production age
                production_age = "N/A"

                try:
                    # Find the "Show Dates" section
                    show_dates_heading = driver.find_element(By.XPATH, '//h3[text()="Show Dates"]')
                    show_dates_content = show_dates_heading.find_element(By.XPATH, './following-sibling::div')

                    raw_text = show_dates_content.text.strip()
                    log_and_print(f"📅 Raw show dates text for {title}: {raw_text}")

                    # Extract Opening Date using regex
                    match = re.search(r"Opening:\s*([A-Za-z]{3,9}\s\d{1,2},\s\d{4})", raw_text)
                    if match:
                        date_str = match.group(1)
                        try:
                            opening_date = datetime.strptime(date_str, "%b %d, %Y")
                            today = datetime.now()

                            if opening_date > today:
                                production_age = "Upcoming"
                                log_and_print(f"🕓 '{title}' has not opened yet. Age: {production_age}")
                            else:
                                delta = today - opening_date
                                years = delta.days // 365
                                production_age = f"{years}"
                                log_and_print(f"🎭 Production age for '{title}': {production_age} year(s)")
                        except Exception as e:
                            log_and_print(f"⚠️ Failed to parse opening date '{date_str}': {e}")
                    else:
                        log_and_print(f"⚠️ No opening date found for {title}")

                except Exception as e:
                    log_and_print(f"⚠️ Could not find 'Show Dates' section for {title}: {e}")






                # venue & market presence
                try:
                    # Get venue name
                    venue_name_el = driver.find_element(By.CSS_SELECTOR, 'a.showpage__venue--name[data-qa="show-theater-link"]')
                    full_venue_name = venue_name_el.text.strip()

                    # Remove "Theatre" or "Theater" suffix from the name
                    venue_name = re.sub(r"\b(Theatre|Theater)\b", "", full_venue_name, flags=re.IGNORECASE).strip()

                    # Get address
                    venue_address_el = venue_name_el.find_element(By.XPATH, './following-sibling::div')
                    venue_address = venue_address_el.get_attribute('innerHTML').replace('<br>', ' ').strip()

                    # Determine market presence
                    if "New York" in venue_address or "NY" in venue_address or "Broadway" in venue_address:
                        market_presence = "US"
                    elif "London" in venue_address or "UK" in venue_address or "England" in venue_address:
                        market_presence = "UK"
                    else:
                        market_presence = "Unknown"

                    log_and_print(f"🏛️ Venue: {venue_name}")
                    log_and_print(f"🌍 Market Presence: {market_presence}")

                except Exception as e:
                    venue_name = "N/A"
                    market_presence = "Unknown"
                    log_and_print(f"⚠️ Venue info not found for {title}: {e}")


                # # Save final data row(s)
                # if calendar_data:
                #     for perf in calendar_data:
                #         all_scraped_data.append({
                #             "Title": title,
                #             "Link": link,
                #             "Description": item.get("Description", "N/A"),
                #             "Image URL": item.get("Image URL", "N/A"),
                #             # "Reviews": item.get("Reviews", "N/A"),
                #             # "Price": item.get("Price", "N/A"),
                #             "Production Type": production_type,
                #             "Market Presence": market_presence,
                #             "Theatre": venue_name,
                #             "Age of Production (yrs)": production_age,
                #             "Category": category,
                #             "Origin": origin,
                #             "Date": perf["date"],
                #             "Time": perf["time"],
                #             "Status": perf["status"],
                #         })
                # else:
                #     # If no calendar data, save at least one row
                #     all_scraped_data.append({
                #         "Title": title,
                #         "Link": link,
                #         "Description": item.get("Description", "N/A"),
                #         "Image URL": item.get("Image URL", "N/A"),
                #         # "Reviews": item.get("Reviews", "N/A"),
                #         # "Price": item.get("Price", "N/A"),
                #         "Production Type": production_type,
                #         "Market Presence": market_presence,
                #         "Theatre": venue_name,
                #         "Age of Production (yrs)": production_age,
                #         "Category": category,
                #         "Origin": origin,
                #         "Date": "N/A",
                #         "Time": "N/A",
                #         "Status": "N/A",
                #     })
                
                
                
                # Ensure at least one row is saved even if calendar_data is empty
                calendar_data = calendar_data or [{"date": "N/A", "time": "N/A", "status": "N/A"}]

                for perf in calendar_data:
                    all_scraped_data.append({
                        "Title": title,
                        "Link": link,
                        "Description": item.get("Description", "N/A"),
                        "Image URL": item.get("Image URL", "N/A"),
                        # "Reviews": item.get("Reviews", "N/A"),
                        # "Price": item.get("Price", "N/A"),
                        "Production Type": production_type,
                        "Market Presence": market_presence,
                        "Theatre": venue_name,
                        "Age of Production (yrs)": production_age,
                        "Category": category,
                        "Origin": origin,
                        "Date": perf["date"],
                        "Time": perf["time"],
                        "Status": perf["status"],
                    })





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

        if all_scraped_data:

            os.makedirs("data", exist_ok=True)  # Ensure 'data' folder exists
            filename = f"data/broadwaycopy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df = pd.DataFrame(all_scraped_data)
            df.to_csv(filename, index=False)
            log_and_print(f"📁 Data saved to {filename}")
        else:
            log_and_print("⚠️ No data to save.")

# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_shows()
