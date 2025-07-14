# ========== Import Required Libraries ==========
import csv  # For writing data to CSV files
import os  # For creating folders and handling paths
import time  # For adding delays (e.g., waiting for pages to load)
from datetime import datetime  # For working with dates and times
import logging  # For logging events (info, warnings, errors)
import undetected_chromedriver as uc  # For bypassing bot detection in Chrome
from selenium.webdriver.common.by import By  # For locating elements
from selenium.webdriver.support.ui import WebDriverWait  # To wait until elements are available
from selenium.webdriver.support import expected_conditions as EC  # Expected conditions for waits

# ========== Setup Logging ==========
# Create 'log' folder if it doesn't exist
os.makedirs("log", exist_ok=True)

# Create the main logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set logging level to INFO

# Create file handler to write logs to file
file_handler = logging.FileHandler("log/ovationtix_scraper.log", mode="a", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)

# Create console handler to print logs to terminal
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# Attach both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ========== Set Up Chrome Driver ==========
def setup_driver():
    options = uc.ChromeOptions()
    options.headless = False  # Run browser in headless mode (no window) change to False to show window
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")  # Set browser window size
    options.add_argument("--disable-blink-features=AutomationControlled")    
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    # options.add_argument("--disable-javascript")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US,en;q=0.9")

    # Set custom user-agent to help avoid detection
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(options=options)  # Launch browser with options
    if not options.headless:
        driver.maximize_window()  # Maximize if not headless
    return driver


# ========== Load Page and Wait for It ==========
def load_page(driver, url):
    try:
        driver.get(url)  # Navigate to URL
        logging.info(f"Navigated to {url}")

        # Wait until body tag appears (ensures page is loaded)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logging.info("Page fully loaded")
        return True
    except Exception as e:
        logging.error(f"Error loading page: {e}")
        return False
    

# ========== Click Calendar Button ==========
def click_calendar_button(driver):
    try:
        logging.info("Waiting for calendar button...")

        # Optional: Screenshot for debugging
        driver.save_screenshot("debug_calendar.png")
        logging.info("Saved screenshot to debug_calendar.png")

        # Optional: Try dismissing cookie or modal popups
        try:
            dismiss_btn = driver.find_element(By.CSS_SELECTOR, ".close-button, .cookie-dismiss, .modal-close")
            driver.execute_script("arguments[0].click();", dismiss_btn)
            logging.info("Dismissed popup/modal if present.")
            time.sleep(1)
        except:
            logging.info("No popup/modal to dismiss.")

        # Wait until calendar button is present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-test="calendar_button"]'))
        )

        # Get all matching buttons
        buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-test="calendar_button"]')
        logging.info(f"Found {len(buttons)} calendar button(s).")

        if not buttons:
            raise Exception("Calendar button not found.")

        calendar_btn = buttons[0]

        # Scroll and click via JS to avoid interception
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", calendar_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", calendar_btn)
        logging.info("👍 Clicked the 'Calendar' button successfully.")

        # Wait for toggle buttons to appear
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "calendarToggleButtons"))
        )

        # Get and click second toggle button
        toggle_buttons = driver.find_elements(By.CSS_SELECTOR, ".calendarToggleButtons button")
        if len(toggle_buttons) < 2:
            raise Exception("Second calendar toggle button not found.")
        driver.execute_script("arguments[0].click();", toggle_buttons[1])
        logging.info("Clicked the second calendar toggle button (Grid View).")

        # Wait for event list container
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Calendar content is visible.")
        return True

    except Exception as e:
        logging.error(f"Failed to click the 'Calendar' button: {e}")
        return False

    

# ========== Extract Details From a Single Event Page ==========
def extract_event_details(driver):
    details = {}

    # Get the event URL
    try:
        details["event_url"] = driver.current_url
    except Exception:
        details["event_url"] = "N/A"

    # Extract the title of the event
    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "h1.calendarTitle.prodTitle")
            )
        )
        details["title"] = title_element.text.strip()
        logging.info(f"Extracted title: {details['title']}")
    except Exception as e:
        logging.warning(f"Failed to extract title: {e}")
        details["title"] = "N/A"

    # Extract all date and time slots for the event
    formatted_date_times = []

    try:
        event_list_items = driver.find_elements(By.CSS_SELECTOR, "li.events")

        for item in event_list_items:
            try:
                date_div = item.find_element(By.CSS_SELECTOR, "h5.ot_eventDateTitle .date")
                date_text = date_div.text.strip()

                # Find all time slots for this date
                time_buttons = item.find_elements(By.CSS_SELECTOR, "button.ot_timeSlotBtn p")
                time_texts = [btn.text.strip() for btn in time_buttons if btn.text.strip()]

                for time in time_texts:
                    formatted_date_times.append(f"{date_text} - {time}")

            except Exception as inner_e:
                logging.warning(f"Failed to extract date/time from an event item: {inner_e}")

        details["date_times"] = formatted_date_times
    except Exception as outer_e:
        logging.error(f"Error while extracting all dates and times: {outer_e}")
        details["date_and_times"] = "N/A"

    # Extract image URL
    try:
        image_element = driver.find_element(By.CSS_SELECTOR, "img.ot_prodImg")
        details["image_url"] = image_element.get_attribute("src")
        logging.info(f"Extracted image URL: {details['image_url']}")
    except Exception as e:
        logging.warning(f"Image not found or selector issue: {e}")
        details["image_url"] = "N/A"

    return details


# ========== Helper: Click the second toggle button again after going back ==========
def click_second_toggle_button(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "calendarToggleButtons"))
        )
        toggle_buttons = driver.find_elements(By.CSS_SELECTOR, ".calendarToggleButtons button")

        if len(toggle_buttons) >= 2:
            # Scroll into view first
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggle_buttons[1])
            time.sleep(0.5)

            # Click with JavaScript to avoid interception
            driver.execute_script("arguments[0].click();", toggle_buttons[1])
            logging.info("Re-clicked the second calendar toggle button (via JS).")
        else:
            raise Exception("Less than 2 toggle buttons found.")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        time.sleep(1)  # Let the calendar settle
        logging.info("Calendar content (.ot_prodListContainer) is visible again after returning.")
        return True

    except Exception as e:
        logging.error(f"Error re-clicking the second toggle button: {e}")
        return False




def extract_events(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Event list container is visible.")

        event_data_list = []
        processed_urls = set()
        index = 0

        while True:
            # Refresh events list every loop to get fresh DOM references
            events = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"))
            )

            if index >= len(events):
                break

            try:
                event = events[index]
                button = event.find_element(By.CSS_SELECTOR, "button.ot_prodInfoButton")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", button)
                time.sleep(0.5)
                button.click()
                logging.info(f"Clicked 'See this event' on event #{index + 1}")

                WebDriverWait(driver, 10).until(EC.url_contains("production"))

                current_url = driver.current_url
                if current_url in processed_urls:
                    logging.info(f"Already processed {current_url}, skipping.")
                    driver.back()
                    click_second_toggle_button(driver)
                    index += 1
                    continue

                processed_urls.add(current_url)

                details = extract_event_details(driver)
                event_data_list.append(details)
                logging.info(f"Extracted event #{index + 1} details: {details}")

                driver.back()
                click_second_toggle_button(driver)
                index += 1

            except Exception as e:
                logging.error(f"Error processing event #{index + 1}: {e}")
                driver.back()
                click_second_toggle_button(driver)
                index += 1

        return event_data_list

    except Exception as e:
        logging.error(f"Failed to extract events: {e}")
        return []


# ========== Main Execution ==========
def main():
    url = "https://ci.ovationtix.com/35583/production/1152995"
    driver = setup_driver()  # Launch Chrome in headless mode

    all_events = []  # This will hold all event data to be written to CSV

    try:
        # Step 1: Load the main page
        if load_page(driver, url):
            logging.info("Ready to begin scraping content...")

            # Step 2: Click the calendar button to open the event listing
            if click_calendar_button(driver):
                logging.info("Calendar panel should now be visible.")

                # Step 3: Extract event links by clicking each "See this event" button
                event_links = extract_events(driver) # Extract events to get events 

                # Step 4: Check and log the extracted event URLs
                if event_links:
                    logging.info(f"Successfully extracted {len(event_links)} event URLs.")
                    for link in event_links:
                        logging.info(f"→ {link['event_url']}")  # Log each event URL

                    # Step 5: Visit each event URL and extract detailed data                      
                    for idx, link in enumerate(event_links, start=1):
                        try:
                            driver.get(link["event_url"])
                            time.sleep(2)

                            event_data = extract_event_details(driver)

                            # Merge link + newly extracted data
                            merged_data = link.copy()
                            for key in set(list(link.keys()) + list(event_data.keys())):
                                val1 = event_data.get(key, "N/A")
                                val2 = link.get(key, "N/A")
                                merged_data[key] = val1 if val1 not in [None, "", "N/A"] else val2

                            # Go through each date/time combo
                            for date_time in merged_data.get("date_times", []):
                                # Check if title is missing
                                if not merged_data.get("title") or merged_data.get("title") == "N/A":
                                    logging.warning(f"Missing title for event: {merged_data.get('event_url')}")

                                # Determine event status (upcoming, active, closed)
                                try:
                                    event_datetime = datetime.strptime(date_time, "%d %B %Y - %I:%M %p")
                                    now = datetime.now()
                                    if abs((event_datetime - now).total_seconds()) <= 300:
                                        status = "active"
                                    elif event_datetime > now:
                                        status = "upcoming"
                                    else:
                                        status = "closed"
                                except Exception as e:
                                    logging.warning(f"Could not parse date_time '{date_time}' for status: {e}")
                                    status = "N/A"

                                # Append event data
                                all_events.append({
                                    "title": merged_data.get("title", "N/A"),
                                    "event_url": merged_data.get("event_url", "N/A"),
                                    "image_url": merged_data.get("image_url", "N/A"),
                                    "status": status,
                                    "production_type": merged_data.get("production_type", "N/A"),
                                    "date_time": date_time,
                                    "origin": "N/A",
                                    "market_presence": "N/A",
                                    "age_of_production": "N/A",  
                                })

                        except Exception as e:
                            logging.error(f"Error scraping event page {link['event_url']}: {e}")

                else:
                    logging.warning("No event URLs were extracted.")
            else:
                logging.error("Failed to open calendar panel.")
        else:
            logging.error("Page did not load properly.")

        # Step 8: Save results to CSV if data was collected
        if all_events:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/tnny_events_{timestamp}.csv"
            os.makedirs("data", exist_ok=True)
            with open(filename, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "title",
                        "event_url",
                        "image_url",
                        "status",
                        "production_type",
                        "date_time",
                        "origin",	
                        "market_presence",
                        "age_of_production",
                    ],
                )
                writer.writeheader()
                writer.writerows(all_events)
            logging.info(f"Successfully saved {len(all_events)} records to {filename}")
        else:
            logging.warning("No event data collected. CSV not created.")

    finally:
        # Step 9: Always quit the driver to release resources
        driver.quit()
        del driver  # Helps suppress warning messages in Windows

# Run the script
if __name__ == "__main__":
    main()
