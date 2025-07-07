import time
from datetime import datetime
from datetime import date
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
# Initialize the driver with the correct ChromeDriver version
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://www.todaytix.com/nyc/shows/25598-and-juliet-on-broadway")
time.sleep(10)
driver.maximize_window()
sold_ticket_data = []
index = 0
try:
    cookie = driver.find_element(By.XPATH, "//*[@id='onetrust-accept-btn-handler']")
    cookie.click()
except:
    pass
time.sleep(3)
while True:  # Main repeat loop
    show = venue = month = None
    try:
        show_tag = driver.find_element(By.XPATH, "//*[@id='about-section']/div[2]/h2")
        show = show_tag.text
    except:
        pass
    try:
        venue_tag = driver.find_element(By.XPATH, "//*[@id='__next']/div[1]/div/div[1]/div/div[1]/div[2]/div/div/p/a")
        venue = venue_tag.text
    except:
        pass
    try:
        month_tag = driver.find_element(By.XPATH, "//*[@id='show-calendar']/div[contains(@class, 'jss2')]/div[contains(@class, 'jss2')]/div[contains(@class, 'jss2')]")
        month_text = month_tag.text
        if re.search(r"January|February|March|April|May|June|July|August|September|October|November|December", month_text):
            month = month_text
    except:
        pass
    # Find available calendar days
    calendar_tag = []
    try:
        calendar_tag = driver.find_elements(By.XPATH, "//*[@id='show-calendar']/div/div/div/div/div/div[2]/button[not(@disabled)]/div[1]")
    except:
        pass
    for k in range(len(calendar_tag)):
        day = None
        try:
            day = calendar_tag[k].text
            calendar_tag[k].click()
        except:
            continue
        present_url = driver.current_url
        time.sleep(3)
        # Get available times
        time_tag = []
        try:
            time_tag = driver.find_elements(By.XPATH, "//*[@id='showtimes-list']/div/div/div[2]/div/div[1]/span[1]")
        except:
            pass
        for j in range(len(time_tag)):
            show_time = None
            try:
                show_time = time_tag[j].text
                time_tag[j].click()
            except:
                continue
            time.sleep(2)
            # Click checkout button
            select_tag = None
            try:
                select_tag = driver.find_element(By.XPATH, "//*[@id='pdp-checkout-button']")
                # Try multiple times as it might be needed
                for _ in range(4):
                    try:
                        select_tag.click()
                    except:
                        pass
            except:
                pass
            time.sleep(5)
            # Handle ticket selection
            no_ticket = None
            try:
                no_ticket = driver.find_element(By.XPATH, "//*[@id='show-summary-container']/div/div[2]/div/div[2]/div[2]/div/button")
                no_ticket.click()
                time.sleep(2)
                subtract = driver.find_element(By.XPATH, "//*[@id='wl-root']/div/div[3]/div[3]/div/div[2]/div/div[2]/div/div[2]/button[1]")
                subtract.click()
                submit = driver.find_element(By.XPATH, "//*[@id='wl-root']/div/div[3]/div[3]/div/div[2]/div/button")
                submit.click()
                time.sleep(3)
            except:
                pass
            first_pass = True
            # Loop through ticket options
            while True:
                ticket_tag = []
                try:
                    ticket_tag = driver.find_elements(By.XPATH, "//*[@id='leftContainer']/div[2]/div/div[6]/span/div/strong")
                except:
                    pass
                for i in range(len(ticket_tag)):
                    ticket_price = amount_unsold = unavailable = sold_seats = available = no_of_tickets = None
                    try:
                        ticket_price = ticket_tag[i].text
                    except:
                        pass
                    try:
                        color = ticket_tag[i].value_of_css_property("color")
                    except:
                        pass
                    try:
                        no_ticket = driver.find_element(By.XPATH, "//*[@id='show-summary-container']/div/div[2]/div/div[2]/div[2]/div/button")
                        no_of_tickets = no_ticket.text
                    except:
                        pass
                    # Get available seats
                    rects = []
                    try:
                        rects = driver.find_elements(By.XPATH, "//*[name()='g' and contains(@aria-label, 'availableSeat')]/*[name()='rect']")
                        available = len(rects)
                    except:
                        pass
                    # Process color
                    try:
                        parts = re.search(r"rgba\s*\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color)
                        if parts:
                            color = f"rgb({parts.group(1)}, {parts.group(2)}, {parts.group(3)})"
                    except:
                        pass
                    # Find matching rectangles
                    matching_rects = []
                    for rect in rects:
                        try:
                            fill_color = rect.value_of_css_property("fill")
                            if fill_color == color:
                                matching_rects.append(rect)
                        except:
                            continue
                    try:
                        amount_unsold = len(matching_rects)
                    except:
                        pass
                    # Save old values and reset
                    a_seats1 = a_seats if 'a_seats' in locals() else []
                    a_seats = []  # reset
                    # Get unavailable seats
                    rects1 = []
                    try:
                        rects1 = driver.find_elements(By.XPATH, "//*[name()='g' and contains(@aria-label, 'tooltip') and not(contains(@aria-label, 'availableSeat'))]/*[name()='rect']")
                        unavailable = len(rects1)
                    except:
                        unavailable = 0
                    # Build new a_seats from current rects
                    try:
                        a_seats = [seat.get_attribute("aria-label") for seat in rects1]
                    except:
                        a_seats = []
                    # Only compute sold_seats if NOT the first pass
                    sold_seats = None
                    if not first_pass:
                        a_seats = list(set(a_seats1) & set(a_seats))  # intersection
                        sold_seats = len(a_seats)
                    try:
                        no_ticket.click()
                    except:
                        pass
                    # Now that the first round is done, mark flag as FALSE
                    first_pass = False
                                        # Store the data
                    sold_ticket_data.append({
                        'show': show,
                        'venue': venue,
                        'month': month,
                        'day': day,
                        'time': show_time,
                        'ticket_price': ticket_price,
                        'No_of_tickets': no_of_tickets,
                        'Amount_unsold': amount_unsold,
                        'unavailable': unavailable,
                        'sold_seats': sold_seats,
                        'available': available,
                        'scrape_time': date.today().strftime('%Y-%m-%d'),
                        'website': "Broadway_world",
                        'country': "USA"
                    })
                    index += 1
                    time.sleep(2)
                time.sleep(2)
                # Check for next button
                next_btn = None
                try:
                    add = driver.find_element(By.XPATH, "//*[@id='wl-root']/div/div[3]/div[3]/div/div[2]/div/div[2]/div/div[2]/button[2]")
                    class_attr = add.get_attribute("class")
                    if "disabled" not in class_attr:
                        next_btn = add
                except:
                    pass
                if next_btn is None:
                    break
                try:
                    next_btn.click()
                    submit = driver.find_element(By.XPATH, "//*[@id='wl-root']/div/div[3]/div[3]/div/div[2]/div/button")
                    submit.click()
                    time.sleep(3)
                except:
                    pass
            # Navigate back to the original URL
            driver.get(present_url)
            time.sleep(5)
            # Refresh time tags
            try:
                time_tag = driver.find_elements(By.XPATH, "//*[@id='showtimes-list']/div/div/div[2]/div/div[1]/span[1]")
            except:
                pass
        time.sleep(3)
        # Refresh calendar tags
        try:
            calendar_tag = driver.find_elements(By.XPATH, "//*[@id='show-calendar']/div/div/div/div/div/div[2]/button[not(@disabled)]/div[1]")
        except:
            pass
    # Check for next calendar page button
    next_btn = None
    try:
        add = driver.find_element(By.XPATH, "//*[@id='show-calendar']/div/div/div[2]/button[2]")
        class_attr = add.get_attribute("class")
        if "disabled" not in class_attr:
            next_btn = add
    except:
        pass
    if next_btn is None:
        break
    try:
        next_btn.click()
    except:
        pass
sold_ticket_data_df = pd.DataFrame(sold_ticket_data)
print(sold_ticket_data_df)