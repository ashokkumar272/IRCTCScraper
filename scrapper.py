import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_irctc_trains(from_station, to_station, date):
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-extensions')
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()
    
    # Create wait objects
    short_wait = WebDriverWait(driver, 10)
    wait = WebDriverWait(driver, 20)
    train_list = []
    
    try:
        # Navigate to IRCTC website
        driver.get("https://www.irctc.co.in/nget/train-search")
        short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p-autocomplete[formcontrolname='origin'] input.ui-autocomplete-input")))

        # Handle popup
        try:
            alert_close = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'OK')]")))
            alert_close.click()
        except:
            pass

        # Input stations
        from_input = short_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p-autocomplete[formcontrolname='origin'] input.ui-autocomplete-input")))
        from_input.clear()
        from_input.send_keys(from_station)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-panel .ui-autocomplete-items")))
        from_input.send_keys(Keys.DOWN, Keys.ENTER)

        to_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p-autocomplete[formcontrolname='destination'] input.ui-autocomplete-input")))
        to_input.clear()
        to_input.send_keys(to_station)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-panel .ui-autocomplete-items")))
        to_input.send_keys(Keys.DOWN, Keys.ENTER)

        # Input date
        date_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.ui-calendar > input.ui-inputtext")))
        date_input.clear()
        driver.execute_script("arguments[0].value = arguments[1]", date_input, date)
        driver.find_element(By.TAG_NAME, 'body').click()

        # Click search
        search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search_btn.train_Search")))
        search_button.click()

        # Wait for results
        train_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
            "div.form-group.no-pad.col-xs-12.bull-back.border-all")))

        # Extracting train information
        train_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 
            "div.form-group.no-pad.col-xs-12.bull-back.border-all > app-train-avl-enq > div.ng-star-inserted")))
        
        for train_element in train_elements:
            train_dict = {}

            # Train name and number
            train_info = train_element.find_element(By.CSS_SELECTOR, ".train-heading strong").text.strip()
            if '(' in train_info and ')' in train_info:
                train_dict['name'], train_dict['number'] = train_info.split('(')
                train_dict['number'] = train_dict['number'].strip(')')
                train_dict['name'] = train_dict['name'].strip()
            else:
                train_dict['name'] = train_info

            # Departure & arrival
            schedule_div = train_element.find_element(By.CSS_SELECTOR, ".white-back.no-pad")
            times = schedule_div.find_elements(By.CSS_SELECTOR, ".time")
            train_dict['departure_time'] = times[0].text.strip() if len(times) > 0 else "N/A"
            train_dict['arrival_time'] = times[1].text.strip() if len(times) > 1 else "N/A"

            # Stations
            stations = schedule_div.find_elements(By.CSS_SELECTOR, ".col-xs-12.hidden-lg.hidden-md.hidden-sm")
            if len(stations) >= 2:
                train_dict['from_station'] = stations[0].text.strip()
                train_dict['to_station'] = stations[1].text.strip()

            # Days
            try:
                days_div = schedule_div.find_element(By.CSS_SELECTOR, ".remove-padding.col-xs-4.text-center")
                train_dict['operating_days'] = ''.join([day.text for day in days_div.find_elements(By.CSS_SELECTOR, ".Y")])
            except:
                train_dict['operating_days'] = ""

            # Classes
            class_elements = train_element.find_elements(By.CSS_SELECTOR, ".pre-avl")
            train_dict['available_classes'] = []
            for class_elem in class_elements:
                class_name = class_elem.find_element(By.TAG_NAME, 'strong').text.strip()
                train_dict['available_classes'].append(class_name)

            train_list.append(train_dict)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

    return train_list

# Input from user
from_station = input("Enter source station: ")
to_station = input("Enter destination station: ")
date = input("Enter date (format: dd/mm/yyyy): ")

# Scrape train data
train_data = scrape_irctc_trains(from_station, to_station, date)

# Save to JSON
import os
output_path = os.path.join(os.getcwd(), "train_data.json")
with open(output_path, "w") as f:
    json.dump(train_data, f, indent=2)

print(f"\n✅ Train data saved to: {output_path}")
