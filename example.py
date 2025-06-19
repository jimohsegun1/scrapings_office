# ========== Import Required Libraries ==========
import csv  # For writing scraped data to CSV files
import os  # For creating directories and handling file paths
import time  # To add delays (e.g., waiting for page elements to load)
from datetime import datetime  # For working with and formatting dates and times
import logging  # For logging scraper progress, warnings, and errors
import undetected_chromedriver as uc  # Chrome driver that helps bypass bot detection
from selenium.webdriver.common.by import (
    By,
)  # For locating elements by CSS selectors, tags, etc.
from selenium.webdriver.support.ui import (
    WebDriverWait,
)  # To wait for elements to appear/be clickable
from selenium.webdriver.support import (
    expected_conditions as EC,
)  # Defines expected conditions for WebDriverWait

# ========== Setup Logging ==========
# Ensure the 'log' folder exists, create if it does not
os.makedirs("log", exist_ok=True)

# Create the main logger object
logger = logging.getLogger()
logger.setLevel(
    logging.INFO
)  # Set minimum log level to INFO to catch info, warnings, errors

# Create a file handler to write log messages to a file (appending mode, UTF-8 encoding)
file_handler = logging.FileHandler(
    "log/ovationtix_scraper.log", mode="a", encoding="utf-8"
)
# Define the format for file logs (timestamp, level, message)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)

# Create a console handler to output log messages to the terminal
console_handler = logging.StreamHandler()
# Define a simpler format for console logs (level and message)
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# Add both the file and console handlers to the main logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ========== Set Up Chrome Driver ==========
def setup_driver():
    """
    Initialize the undetected Chrome driver with custom options to avoid detection.
    Runs headless (no GUI) by default but can be toggled to show window.
    """
    options = uc.ChromeOptions()
    options.headless = (
        True  # Headless mode: no visible browser window. Set False for debugging.
    )
    options.add_argument(
        "--no-sandbox"
    )  # Bypass OS security model (needed for some environments)
    options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
    options.add_argument(
        "--disable-dev-shm-usage"
    )  # Overcome limited resource problems in Docker
    options.add_argument(
        "--window-size=1920,1080"
    )  # Set the browser window size to Full HD

    # Set a realistic user-agent string to help avoid detection as a bot
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )

    # Create and return the Chrome driver with these options
    driver = uc.Chrome(options=options)

    # If running in visible mode, maximize the window
    if not options.headless:
        driver.maximize_window()

    return driver


# ========== Load Page and Wait for It ==========
def load_page(driver, url):
    """
    Load the given URL in the browser and wait until the page is fully loaded by checking the presence of the <body> tag.
    Returns True if successful, False if there was an error.
    """
    try:
        driver.get(url)  # Navigate to the page URL
        logging.info(f"Navigated to {url}")

        # Wait for up to 20 seconds until the <body> element is present, meaning the page loaded
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
    """
    Locate and click the 'Calendar' button on the page to reveal event listings.
    Wait until the calendar content container is visible after clicking.
    Returns True if successful, False if any error occurs.
    """
    try:
        # Wait for the calendar button to be clickable, then click it
        calendar_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[data-test="calendar_button"]')
            )
        )
        calendar_btn.click()
        logging.info("Clicked the 'Calendar' button successfully.")

        # Wait for the calendar event list container to become visible
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Calendar content (.ot_prodListContainer) is visible.")
        return True
    except Exception as e:
        logging.error(f"Failed to click the 'Calendar' button: {e}")
        return False


# ========== Extract Details From a Single Event Page ==========
def extract_event_details(driver):
    """
    Scrape the event detail page for title, dates/times, and image URL.
    Returns a dictionary of extracted information.
    """
    details = {}

    # Get current page URL as event URL
    try:
        details["event_url"] = driver.current_url
    except Exception:
        details["event_url"] = "N/A"

    # Extract event title (expected to always be present)
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

    # Extract all available date and time slots for the event
    formatted_date_times = []

    try:
        # Find all list items representing different dates for the event
        event_list_items = driver.find_elements(By.CSS_SELECTOR, "li.events")

        for item in event_list_items:
            try:
                # Extract the date text for this list item
                date_div = item.find_element(
                    By.CSS_SELECTOR, "h5.ot_eventDateTitle .date"
                )
                date_text = date_div.text.strip()

                # Extract all time buttons for this date
                time_buttons = item.find_elements(
                    By.CSS_SELECTOR, "button.ot_timeSlotBtn p"
                )
                time_texts = [
                    btn.text.strip() for btn in time_buttons if btn.text.strip()
                ]

                # Combine date with each time and append to list
                for time in time_texts:
                    formatted_date_times.append(f"{date_text} - {time}")

            except Exception as inner_e:
                logging.warning(
                    f"Failed to extract date/time from an event item: {inner_e}"
                )

        details["date_times"] = formatted_date_times
    except Exception as outer_e:
        logging.error(f"Error while extracting all dates and times: {outer_e}")
        details["date_times"] = "N/A"

    # Extract image URL for the event
    try:
        image_element = driver.find_element(By.CSS_SELECTOR, "img.ot_prodImg")
        details["image_url"] = image_element.get_attribute("src")
        logging.info(f"Extracted image URL: {details['image_url']}")
    except Exception as e:
        logging.warning(f"Image not found or selector issue: {e}")
        details["image_url"] = "N/A"

    return details


# ========== Extract All Events From Calendar ==========
def extract_events(driver):
    """
    From the calendar page, extract all listed events by clicking each and scraping their detail pages.
    Returns a list of dictionaries with event data.
    """
    try:
        # Wait until event list container is visible
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Event list container is visible.")

        # Find all event list items currently on page
        original_events = driver.find_elements(
            By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"
        )
        logging.info(f"Found {len(original_events)} event items.")

        event_data_list = []

        # Iterate through each event by index to avoid stale element issues
        for idx in range(len(original_events)):
            try:
                # Refetch events each loop (DOM may have changed)
                events = driver.find_elements(
                    By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"
                )

                # Check if the current index still exists
                if idx >= len(events):
                    logging.warning(
                        f"Event #{idx + 1} no longer exists on reloaded page."
                    )
                    continue

                # Scroll to and click the 'See this event' button to open event detail page
                button = events[idx].find_element(
                    By.CSS_SELECTOR, "button.ot_prodInfoButton"
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
                    button,
                )
                button.click()
                logging.info(f"Clicked 'See this event' on event #{idx + 1}")

                # Wait until the URL changes to indicate event page loaded
                WebDriverWait(driver, 10).until(EC.url_contains("production"))

                # Scrape the event details on this page
                details = extract_event_details(driver)
                event_data_list.append(details)
                logging.info(f"Extracted event #{idx + 1} details: {details}")

                # Go back to the calendar page
                driver.back()

                # Wait for the calendar container to be visible again before next iteration
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CLASS_NAME, "ot_prodListContainer")
                    )
                )

            except Exception as e:
                logging.error(f"Error processing event #{idx + 1}: {e}")

        return event_data_list

    except Exception as e:
        logging.error(f"Failed to extract events: {e}")
        return []


# ========== Main Execution ==========
def main():
    """
    Main script function to run the full scraping process.
    Loads the page, clicks calendar, extracts event URLs, scrapes each event details,
    compiles data with status, and saves all data to CSV.
    """
    url = "https://ci.ovationtix.com/35583/production/1152995"  # The base URL to scrape

    driver = setup_driver()  # Launch Chrome driver (headless)

    all_events = []  # List to hold all scraped event dictionaries

    try:
        # Load the main page
        if load_page(driver, url):
            logging.info("Ready to begin scraping content...")

            # Click calendar button to reveal events
            if click_calendar_button(driver):

                # Extract event URLs and initial data from calendar listing
                event_links = extract_events(driver)

                if event_links:
                    logging.info(
                        f"Successfully extracted {len(event_links)} event URLs."
                    )
                    for link in event_links:
                        logging.info(f"→ {link['event_url']}")

                    # Visit each event URL individually to gather detailed data
                    for idx, link in enumerate(event_links, start=1):
                        try:
                            driver.get(link["event_url"])
                            time.sleep(
                                2
                            )  # Wait for page load (could replace with explicit wait)

                            # Extract more detailed info from event page
                            event_data = extract_event_details(driver)

                            # Merge previously extracted link info and newly scraped data,
                            # preferring new data if available
                            merged_data = link.copy()
                            for key in set(list(link.keys()) + list(event_data.keys())):
                                val1 = event_data.get(key, "N/A")
                                val2 = link.get(key, "N/A")
                                merged_data[key] = (
                                    val1 if val1 not in [None, "", "N/A"] else val2
                                )

                            # For each date/time combo, generate a record with event info and status
                            for date_time in merged_data.get("date_times", []):
                                # Warn if title is missing (should always be present)
                                if (
                                    not merged_data.get("title")
                                    or merged_data.get("title") == "N/A"
                                ):
                                    logging.warning(
                                        f"Missing title for event: {merged_data.get('event_url')}"
                                    )

                                # Attempt to parse the event datetime string for status classification
                                try:
                                    event_datetime = datetime.strptime(
                                        date_time, "%d %B %Y - %I:%M %p"
                                    )
                                    now = datetime.now()

                                    # Determine if event is active (within 5 minutes), upcoming, or closed
                                    if (
                                        abs((event_datetime - now).total_seconds())
                                        <= 300
                                    ):
                                        status = "active"
                                    elif event_datetime > now:
                                        status = "upcoming"
                                    else:
                                        status = "closed"
                                except Exception as e:
                                    logging.warning(
                                        f"Could not parse date_time '{date_time}' for status: {e}"
                                    )
                                    status = "N/A"

                                # Append this event occurrence's data to the list
                                all_events.append(
                                    {
                                        "title": merged_data.get("title", "N/A"),
                                        "event_url": merged_data.get(
                                            "event_url", "N/A"
                                        ),
                                        "image_url": merged_data.get(
                                            "image_url", "N/A"
                                        ),
                                        "status": status,
                                        "production_type": merged_data.get(
                                            "production_type", "N/A"
                                        ),
                                        "date_time": date_time,
                                        "origin": "N/A",
                                        "market_presence": "N/A",
                                        "age_of_production": "N/A",
                                    }
                                )

                        except Exception as e:
                            logging.error(
                                f"Failed to process event URL '{link.get('event_url', '')}': {e}"
                            )

            else:
                logging.error("Could not click the calendar button to reveal events.")

        else:
            logging.error("Could not load the main page to start scraping.")

    finally:
        driver.quit()
        logging.info("Driver closed.")

    # Save all scraped events to CSV file
    if all_events:
        csv_path = os.path.join("data", "ovationtix_events.csv")
        os.makedirs("data", exist_ok=True)
        keys = all_events[0].keys()

        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(all_events)
            logging.info(f"Saved {len(all_events)} events to {csv_path}")
        except Exception as e:
            logging.error(f"Failed to write CSV file: {e}")
    else:
        logging.info("No events found to save.")


if __name__ == "__main__":
    main()
