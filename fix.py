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
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import random

# --- Configuration ---
RUN_HEADLESS = True

# --- Setup logging ---
os.makedirs("log", exist_ok=True)
log_file = os.path.join("log", "scrape.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_and_print(message):
    print(message)
    logging.info(message)

def hash_event(event):
    # Ensure all values are strings before hashing, or handle non-string types
    # For simplicity, convert all values to string if not already
    event_str_values = {k: str(v) for k, v in event.items()}
    return hashlib.md5(json.dumps(event_str_values, sort_keys=True).encode()).hexdigest()

def scrape_shows():
    start_time = datetime.now()
    log_and_print(f"🚀 Scraping started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    options = webdriver.ChromeOptions()
    if RUN_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    # Removing --disable-javascript as it might interfere with dynamic content loading on some sites
    # options.add_argument("--disable-javascript") 
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36")
    options.add_argument("--no-sandbox") # Required for some environments (e.g., Docker)
    options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems

    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://playbill.com/shows/broadway")
        log_and_print("🌐 Navigated to main page.")
        time.sleep(random.uniform(2, 4))

        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.show-container")))
        cards = driver.find_elements(By.CSS_SELECTOR, "div.show-container")
        log_and_print(f"📦 Found {len(cards)} show cards.")

        links = []
        for i, card in enumerate(cards):
            try:
                title_element = card.find_element(By.CSS_SELECTOR, "div.prod-title a")
                name = title_element.text.strip()
                link = title_element.get_attribute("href").strip()
                img_src = card.find_element(By.CSS_SELECTOR, "div.cover-container img").get_attribute("src").strip()
                venue_element = card.find_element(By.CSS_SELECTOR, "div.prod-venue a")
                venue_name = venue_element.text.strip()
                venue_link = venue_element.get_attribute("href").strip()
                links.append({
                    "Name": name,
                    "Link": link,
                    "Image URL": img_src, # Changed 'image url' to 'Image URL' for consistency
                    "Venue Name": venue_name, # Changed 'venue_name' to 'Venue Name' for consistency
                    "Venue Link": venue_link # Changed 'venue_link' to 'Venue Link' for consistency
                })
                log_and_print(f"🔗 [{i+1}] Found show: {name}")
            except NoSuchElementException as e:
                log_and_print(f"⚠️ Card element error for card {i+1}: {e}")
            except Exception as e:
                log_and_print(f"⚠️ Unexpected error processing card {i+1}: {e}")

        wait = WebDriverWait(driver, 10)
        all_scraped_data = []

        for idx, entry in enumerate(links):
            log_and_print(
                f"\n➡️ Visiting show #{idx + 1}: {entry['Name']} ({entry['Link']} {entry['Venue Name']})"
            )
            
            # --- Initialize all detail fields for the current show to N/A ---
            # This is crucial to prevent data from previous successful scrapes from carrying over
            market = "N/A"
            production_type = "N/A"
            origin = "N/A"
            market_location = "N/A"
            status = "Unknown" 
            age_of_production = "N/A"
            opening_date_str = "N/A"
            
            # These will be populated correctly if schedules are found, or remain N/A if not
            current_schedule_date_range = "N/A"
            current_schedule_date = "N/A"
            current_schedule_time = "N/A"

            try:
                driver.get(entry["Link"])
                time.sleep(random.uniform(2, 4)) # Adjusted sleep for page load

                # --- Extract production details (Market, Production Type, Origin, Market Presence) ---
                try:
                    # Increased wait time for subtitle elements, as they are crucial
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

                    try:
                        address_el = driver.find_element(By.CSS_SELECTOR, "ul.bsp-bio-links li:nth-child(2) a")
                        market_location = address_el.text.strip()
                        if market_location.endswith("NY") or "NEW YORK" in market_location.upper():
                            market_location = market_location + " (US)"
                    except NoSuchElementException: 
                        log_and_print(f"DEBUG: Address element not found for {entry['Name']}. Setting market_location to N/A.")
                        market_location = "N/A"
                    except Exception as e:
                        log_and_print(f"⚠️ Error extracting market location for {entry['Name']}: {e}")
                        market_location = "N/A"

                    log_and_print(f"🌍 Market: {market} | 🎭 Production Type: {production_type} | 📜 Origin: {origin}")
                    log_and_print(f"📍 Market Presence: {market_location}")
                except Exception as e:
                    log_and_print(f"⚠️ Could not extract primary production details for {entry['Name']}: {e}")
                    # Variables will remain N/A as initialized


                # --- Extract production status and age ---
                try:
                    date_blocks = driver.find_elements(By.CSS_SELECTOR, "div.bsp-carousel-slide.with-circular-links")
                    for block in date_blocks:
                        try:
                            title_el = block.find_element(By.CSS_SELECTOR, ".bsp-list-promo-title")
                            title = title_el.text.strip().upper()
                        except NoSuchElementException:
                            log_and_print(f"DEBUG: Title element not found in date block for {entry['Name']}. Skipping this block.")
                            continue 

                        span_texts = block.find_elements(By.CSS_SELECTOR, ".info-circular span")
                        full_text = " ".join([s.text.strip().upper() for s in span_texts if s.text.strip()])

                        log_and_print(f"🔍 {title} => Date Text: '{full_text}'")

                        if title == "OPENING DATE":
                            opening_date_str = full_text
                            try:
                                opening_dt = datetime.strptime(full_text.title(), "%b %d %Y")
                                today = datetime.now()
                                years = today.year - opening_dt.year - (
                                    (today.month, today.day) < (opening_dt.month, opening_dt.day)
                                )
                                age_of_production = f"{years} years"
                            except ValueError as ve: 
                                log_and_print(f"⚠️ Failed parsing opening date '{full_text}' for {entry['Name']}: {ve}")

                        elif title == "CLOSING DATE":
                            if "CURRENTLY RUNNING" in full_text:
                                status = "Active"
                            else:
                                try:
                                    closing_dt = datetime.strptime(full_text.title(), "%b %d %Y")
                                    if closing_dt < datetime.now():
                                        status = "Closed"
                                    else:
                                        status = "Upcoming"
                                except ValueError as ve:
                                    log_and_print(f"⚠️ Failed parsing closing date '{full_text}' for {entry['Name']}: {ve}")
                                    status = "Upcoming" 

                    # Final fallback for status if not determined by closing date or if no date blocks found
                    if status == "Unknown" and opening_date_str != "N/A":
                        status = "Active" # Assume active if an opening date exists and no closing status is set.

                    log_and_print(f"📆 Opening Date: {opening_date_str}")
                    log_and_print(f"📅 Status: {status} | 🕰️ Age: {age_of_production}")

                except Exception as e:
                    log_and_print(f"⚠️ Could not extract status/age for {entry['Name']}: {e}")
                    # Variables will remain N/A or Unknown as initialized


                # --- Extract schedule ---
                current_show_schedules_list = []  # This list collects all schedule rows for the current show

                try:
                    schedule_block_element = driver.find_element(By.CSS_SELECTOR, "div.bsp-bio-text")
                    schedule_block_text = schedule_block_element.text
                    
                    # Split the text into lines and process each line
                    schedule_lines = [line.strip() for line in schedule_block_text.split('\n') if line.strip()]
                    
                    current_date_range_for_schedule = "N/A" # Variable to hold the current date range being processed

                    for line in schedule_lines:
                        # Check if the line is a date range (ends with ':' and doesn't contain '@')
                        if line.endswith(":") and "@" not in line:
                            current_date_range_for_schedule = line.strip(": ").strip()
                            log_and_print(f"  Recognized new Date Range for Schedule: '{current_date_range_for_schedule}'")
                        elif "@" in line:
                            # This line contains a day and a time (e.g., "Monday @ 7pm")
                            parts = line.split("@")
                            if len(parts) >= 2:
                                extracted_day = parts[0].replace("SCHEDULE", "").strip() # Remove "SCHEDULE"
                                extracted_time = parts[1].strip()

                                log_and_print(f"  Parsed Schedule Entry - Date Range: '{current_date_range_for_schedule}' | Day: '{extracted_day}' | Time: '{extracted_time}'")

                                # Append this specific schedule entry to the list
                                current_show_schedules_list.append({
                                    "Name": entry.get("Name", "").strip(),
                                    "Link": entry.get("Link", "").strip(),
                                    "Image URL": entry.get("Image URL", "").strip(), # Use consistent key
                                    "Venue Name": entry.get("Venue Name", "").strip(), # Use consistent key
                                    "Venue Link": entry.get("Venue Link", "").strip(), # Use consistent key

                                    "Market": market.strip(),
                                    "Market Presence": market_location.strip(),
                                    "Production Type": production_type.strip(),
                                    "Origin": origin.strip(),
                                    "Status": status.strip(),
                                    "Age of Production": age_of_production.strip(),

                                    "Date Range": current_date_range_for_schedule.strip(),
                                    "Date": extracted_day.strip(),
                                    "Time": extracted_time.strip()
                                })
                            else:
                                log_and_print(f"  DEBUG: Schedule line with '@' did not split into enough parts for {entry['Name']}: '{line}'")
                        else:
                            log_and_print(f"  DEBUG: Skipping unrecognized schedule line format for {entry['Name']}: '{line}'")

                except NoSuchElementException: 
                    log_and_print(f"⚠️ Schedule block (div.bsp-bio-text) not found for {entry['Name']}. No schedule data will be added.")
                except Exception as e:
                    log_and_print(f"⚠️ Error extracting schedule for {entry['Name']}: {e}")

                # --- Append data to all_scraped_data ---
                # If no schedules were found for the current show, append a single row with N/A for schedule details
                if not current_show_schedules_list:
                    log_and_print(f"No specific schedules found for {entry['Name']}. Adding a single entry with N/A schedule fields.")
                    all_scraped_data.append({
                        "Name": entry.get("Name", "").strip(),
                        "Link": entry.get("Link", "").strip(),
                        "Image URL": entry.get("Image URL", "").strip(),
                        "Venue Name": entry.get("Venue Name", "").strip(),
                        "Venue Link": entry.get("Venue Link", "").strip(),

                        "Market": market.strip(),
                        "Market Presence": market_location.strip(),
                        "Production Type": production_type.strip(),
                        "Origin": origin.strip(),
                        "Status": status.strip(),
                        "Age of Production": age_of_production.strip(),

                        "Date Range": "N/A", 
                        "Date": "N/A",
                        "Time": "N/A"
                    })
                else:
                    # If schedules were found, extend the main list with all collected schedules for this show
                    all_scraped_data.extend(current_show_schedules_list)

                log_and_print(
                    f"📌 Finished processing {entry['Name']} with {len(current_show_schedules_list) if current_show_schedules_list else 1} schedule entry/entries.\n"
                )

            except Exception as e:
                log_and_print(f"🚫 Critical error while processing show {entry['Name']}: {e}")
                # In case of a critical error, still try to add a row with basic info and N/A for details not retrieved.
                all_scraped_data.append({
                    "Name": entry.get("Name", "").strip(),
                    "Link": entry.get("Link", "").strip(),
                    "Image URL": entry.get("Image URL", "").strip(),
                    "Venue Name": entry.get("Venue Name", "").strip(),
                    "Venue Link": entry.get("Venue Link", "").strip(),

                    "Market": market.strip(),
                    "Market Presence": market_location.strip(),
                    "Production Type": production_type.strip(),
                    "Origin": origin.strip(),
                    "Status": status.strip(),
                    "Age of Production": age_of_production.strip(),

                    "Date Range": "N/A", 
                    "Date": "N/A",
                    "Time": "N/A"
                })

    finally:
        if driver:
            driver.quit()

        end_time = datetime.now()
        log_and_print(f"✅ Finished in {(end_time - start_time).total_seconds():.2f}s")

        if all_scraped_data:
            os.makedirs("data", exist_ok=True)
            # Ensure the column order is exactly what you want for the CSV
            columns = [
                "Name", "Link", "Image URL", "Venue Name", "Venue Link",
                "Market", "Market Presence", "Production Type", "Origin",
                "Status", "Age of Production", "Date Range", "Date", "Time"
            ]
            df = pd.DataFrame(all_scraped_data)
            
            # Ensure all expected columns are present, fill missing ones with N/A
            for col in columns:
                if col not in df.columns:
                    df[col] = "N/A"
            
            # Reorder columns to ensure correct output sequence
            df = df[columns]

            # Apply .strip().replace('\n', ' ') to all string columns
            # Using .apply(lambda x: x.str.strip().str.replace('\n', ' ') if x.dtype == "object" else x) is more efficient
            for col in df.columns:
                if df[col].dtype == 'object': # Check if the column contains strings
                    df[col] = df[col].apply(lambda x: x.strip().replace('\n', ' ') if isinstance(x, str) else x)

            filename = f"data/broadway_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            log_and_print(f"📁 Data saved to {filename}")
        else:
            log_and_print("⚠️ No data scraped.")

if __name__ == "__main__":
    scrape_shows()





# import os
# import time
# import json
# import hashlib
# import logging
# import pandas as pd
# from datetime import datetime
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import NoSuchElementException
# from webdriver_manager.chrome import ChromeDriverManager
# import undetected_chromedriver as uc
# import random

# # --- Configuration ---
# RUN_HEADLESS = True

# # --- Setup logging ---
# os.makedirs("log", exist_ok=True)
# log_file = os.path.join("log", "scrape.log")

# logging.basicConfig(
#     filename=log_file,
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
# )

# def log_and_print(message):
#     print(message)
#     logging.info(message)

# def hash_event(event):
#     return hashlib.md5(json.dumps(event, sort_keys=True).encode()).hexdigest()

# def scrape_shows():
#     start_time = datetime.now()
#     log_and_print(f"🚀 Scraping started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
#     options = webdriver.ChromeOptions()
#     if RUN_HEADLESS:
#         options.add_argument("--headless=new")
#     options.add_argument("--ignore-certificate-errors")
#     options.add_argument("--ignore-ssl-errors")
#     options.add_argument("--disable-javascript")
#     options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36")

#     driver = None
#     try:
#         driver = uc.Chrome(options=options)
#         driver.get("https://playbill.com/shows/broadway")
#         log_and_print("🌐 Navigated to main page.")
#         time.sleep(random.uniform(2, 4))

#         WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.show-container")))
#         cards = driver.find_elements(By.CSS_SELECTOR, "div.show-container")
#         log_and_print(f"📦 Found {len(cards)} show cards.")

#         links = []
#         for i, card in enumerate(cards):
#             try:
#                 title_element = card.find_element(By.CSS_SELECTOR, "div.prod-title a")
#                 name = title_element.text.strip()
#                 link = title_element.get_attribute("href").strip()
#                 img_src = card.find_element(By.CSS_SELECTOR, "div.cover-container img").get_attribute("src").strip()
#                 venue_element = card.find_element(By.CSS_SELECTOR, "div.prod-venue a")
#                 venue_name = venue_element.text.strip()
#                 venue_link = venue_element.get_attribute("href").strip()
#                 links.append({
#                     "Name": name,
#                     "Link": link,
#                     "image url": img_src,
#                     "venue_name": venue_name,
#                     "venue_link": venue_link
#                 })
#                 log_and_print(f"🔗 [{i+1}] Found show: {name}")
#             except NoSuchElementException as e:
#                 log_and_print(f"⚠️ Card error: {e}")

#         wait = WebDriverWait(driver, 10)
#         all_scraped_data = []

#         for idx, entry in enumerate(links):
#             log_and_print(f"➡️ Visiting show #{idx + 1}: {entry['Name']}")
#             try:
#                 driver.get(entry["Link"])
#                 time.sleep(random.uniform(2, 4))

#                 subtitle_elements = driver.find_elements(By.CSS_SELECTOR, "div.bsp-bio-subtitle h5")
#                 market = subtitle_elements[0].text.strip().replace("\n", " ") if len(subtitle_elements) > 0 else "N/A"
#                 production_type = subtitle_elements[1].text.strip().replace("\n", " ") if len(subtitle_elements) > 1 else "N/A"
#                 origin = subtitle_elements[2].text.strip().replace("\n", " ") if len(subtitle_elements) > 2 else "N/A"

#                 try:
#                     address_el = driver.find_element(By.CSS_SELECTOR, "ul.bsp-bio-links li:nth-child(2) a")
#                     market_location = address_el.text.strip().replace("\n", " ")
#                     if market_location.endswith("NY") or "New York" in market_location:
#                         market_location += " (US)"
#                 except:
#                     market_location = "N/A"

#                 status = "Unknown"
#                 age_of_production = "N/A"
#                 opening_date_str = "N/A"

#                 date_blocks = driver.find_elements(By.CSS_SELECTOR, "div.bsp-carousel-slide.with-circular-links")
#                 for block in date_blocks:
#                     try:
#                         title = block.find_element(By.CSS_SELECTOR, ".bsp-list-promo-title").text.strip().upper()
#                         span_texts = block.find_elements(By.CSS_SELECTOR, ".info-circular span")
#                         full_text = " ".join([s.text.strip().upper() for s in span_texts if s.text.strip()])
#                         if title == "OPENING DATE":
#                             opening_date_str = full_text
#                             try:
#                                 opening_dt = datetime.strptime(full_text.title(), "%b %d %Y")
#                                 today = datetime.now()
#                                 years = today.year - opening_dt.year - ((today.month, today.day) < (opening_dt.month, opening_dt.day))
#                                 age_of_production = f"{years} years"
#                             except:
#                                 pass
#                         elif title == "CLOSING DATE":
#                             if "CURRENTLY RUNNING" in full_text:
#                                 status = "Active"
#                             else:
#                                 try:
#                                     closing_dt = datetime.strptime(full_text.title(), "%b %d %Y")
#                                     status = "Closed" if closing_dt < datetime.now() else "Upcoming"
#                                 except:
#                                     status = "Upcoming"
#                     except:
#                         continue
#                 if status == "Unknown" and opening_date_str != "N/A":
#                     status = "Active"

#                 structured_schedule = []
#                 try:
#                     schedule_block = driver.find_element(By.CSS_SELECTOR, "div.bsp-bio-text").text
#                     date_blocks = [block.strip() for block in schedule_block.split("\n\n") if "@" in block]
#                     for block in date_blocks:
#                         lines = block.split("\n")
#                         date_range = lines[0].strip(": ").strip()
#                         for line in lines[1:]:
#                             if "@" in line:
#                                 parts = line.split("@")
#                                 day = parts[0].strip()
#                                 time_slot = parts[1].strip()
#                                 structured_schedule.append({
#                                     "Name": entry["Name"],
#                                     "Link": entry["Link"],
#                                     "Image URL": entry["image url"],
#                                     "Venue Name": entry["venue_name"],
#                                     "Venue Link": entry["venue_link"],
#                                     "Market": market,
#                                     "Market Presence": market_location,
#                                     "Production Type": production_type,
#                                     "Origin": origin,
#                                     "Status": status,
#                                     "Age of Production": age_of_production,
#                                     "Date Range": date_range,
#                                     "Date": day,
#                                     "Time": time_slot
#                                 })
#                 except Exception as e:
#                     log_and_print(f"⚠️ Schedule error: {e}")

#                 all_scraped_data.extend(structured_schedule)

#             except Exception as e:
#                 log_and_print(f"🚫 Error: {e}")

#     finally:
#         if driver:
#             driver.quit()

#         end_time = datetime.now()
#         log_and_print(f"✅ Finished in {(end_time - start_time).total_seconds():.2f}s")

#         if all_scraped_data:
#             os.makedirs("data", exist_ok=True)
#             columns = [
#                 "Name", "Link", "Image URL", "Venue Name", "Venue Link",
#                 "Market", "Market Presence", "Production Type", "Origin",
#                 "Status", "Age of Production", "Date Range", "Date", "Time"
#             ]
#             df = pd.DataFrame(all_scraped_data)
#             for col in columns:
#                 if col not in df.columns:
#                     df[col] = "N/A"
#             df = df[columns]
#             df = df.applymap(lambda x: x.strip().replace('\n', ' ') if isinstance(x, str) else x)
#             filename = f"data/broadway_shows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
#             df.to_csv(filename, index=False)
#             log_and_print(f"📁 Data saved to {filename}")
#         else:
#             log_and_print("⚠️ No data scraped.")

# if __name__ == "__main__":
#     scrape_shows()
