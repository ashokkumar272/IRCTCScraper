import json
import datetime
import time # time module is used for deliberate short pauses
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

def normalize_date(date_input: str) -> datetime.date:
    """Accept dd/mm/YYYY or dd-mm-YYYY, return a date object."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(date_input, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date {date_input!r} not in dd/mm/YYYY or dd-mm-YYYY format")

def scrape_irctc_trains(from_code, to_code, journey_date_str):
    journey_date = normalize_date(journey_date_str)

    opts = Options()
    # opts.add_argument("--headless")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.page_load_strategy = 'eager'
    opts.add_argument('--blink-settings=imagesEnabled=false')
    opts.add_argument('--disable-extensions')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    wait = WebDriverWait(driver, 20)
    short_wait = WebDriverWait(driver, 10)

    trains = []
    try:
        driver.get("https://www.irctc.co.in/nget/train-search")

        # Handle popup if it appears
        try:
            ok_button = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']")))
            ok_button.click()
            print("Closed initial popup")
        except TimeoutException:
            print("Info: 'OK' dialog not found or not clickable.")
            pass
        
        # 1) FROM station
        fld_from_selector = (By.CSS_SELECTOR, "p-autocomplete[formcontrolname='origin'] input.ui-autocomplete-input")
        fld_from = short_wait.until(EC.element_to_be_clickable(fld_from_selector))
        fld_from.clear()
        fld_from.send_keys(from_code)
        
        # Wait for suggestions to appear
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-items")))
            fld_from.send_keys(Keys.DOWN, Keys.ENTER)
        except TimeoutException:
            print("No suggestions appeared for FROM station. Trying to proceed...")
            # Try clicking elsewhere to focus away and then try again
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
            fld_from = driver.find_element(*fld_from_selector)
            fld_from.clear()
            fld_from.send_keys(from_code)
            time.sleep(1)
            fld_from.send_keys(Keys.DOWN, Keys.ENTER)
        
        # Get station details
        full_from = fld_from.get_attribute("value").strip()
        if "(" in full_from:
            name_from, code_from_extracted = full_from.split("(", 1)
            name_from = name_from.strip()
            code_from = code_from_extracted.rstrip(")").strip()
        else:
            name_from, code_from = full_from, from_code
        
        print(f"From station: {name_from} ({code_from})")

        # 2) TO station
        fld_to_selector = (By.CSS_SELECTOR, "p-autocomplete[formcontrolname='destination'] input.ui-autocomplete-input")
        fld_to = wait.until(EC.element_to_be_clickable(fld_to_selector))
        fld_to.clear()
        fld_to.send_keys(to_code)
        
        # Wait for suggestions to appear
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-items")))
            fld_to.send_keys(Keys.DOWN, Keys.ENTER)
        except TimeoutException:
            print("No suggestions appeared for TO station. Trying to proceed...")
            # Try clicking elsewhere to focus away and then try again
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
            fld_to = driver.find_element(*fld_to_selector)
            fld_to.clear()
            fld_to.send_keys(to_code)
            time.sleep(1)
            fld_to.send_keys(Keys.DOWN, Keys.ENTER)
        
        # Get station details
        full_to = fld_to.get_attribute("value").strip()
        if "(" in full_to:
            name_to, code_to_extracted = full_to.split("(", 1)
            name_to = name_to.strip()
            code_to = code_to_extracted.rstrip(")").strip()
        else:
            name_to, code_to = full_to, to_code
        
        print(f"To station: {name_to} ({code_to})")

        # 3) DATE - Fixed approach
        date_field_selector = (By.CSS_SELECTOR, "span.ui-calendar > input.ui-inputtext")
        fld_date = wait.until(EC.element_to_be_clickable(date_field_selector))
        journey_date_formatted_str = journey_date.strftime("%d/%m/%Y")
        print(f"Setting date to: {journey_date_formatted_str}")
        
        # Method 1: Character-by-character input
        # First, ensure the field is clear and focused
        fld_date.click()
        time.sleep(0.3)
        fld_date.clear()
        time.sleep(0.5)
        
        # Type the date character by character
        for char in journey_date_formatted_str:
            fld_date.send_keys(char)
            time.sleep(0.1)
        
        # Press Tab to move focus away from date field and confirm
        fld_date.send_keys(Keys.TAB)
        time.sleep(0.5)
        
        # Method 2: JavaScript direct injection (backup)
        # This will run after the key-by-key input as a fallback
        try:
            # Re-get the field to avoid staleness
            fld_date = driver.find_element(*date_field_selector)
            
            # Set value directly with JavaScript
            driver.execute_script(f"arguments[0].value = '{journey_date_formatted_str}';", fld_date)
            time.sleep(0.2)
            
            # Dispatch events to trigger Angular's change detection
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", fld_date)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", fld_date)
        except Exception as e:
            print(f"JavaScript date setting failed: {e}")
        
        # Verify the date value
        try:
            actual_date = fld_date.get_attribute("value")
            print(f"Date field value: '{actual_date}'")
            if actual_date != journey_date_formatted_str:
                print(f"WARNING: Date field has value '{actual_date}' instead of '{journey_date_formatted_str}'")
        except Exception as e:
            print(f"Could not verify date field value: {e}")
            
        # Click elsewhere to close any popup calendar and confirm
        try:
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
        except Exception as e:
            print(f"Body click failed: {e}")
        
        # Final pause before search
        time.sleep(1)

        # 4) SEARCH
        search_button_selector = (By.CSS_SELECTOR, "button.search_btn.train_Search")
        search_button = wait.until(EC.element_to_be_clickable(search_button_selector))
        print("Clicking search button...")
        search_button.click()
        time.sleep(1)  # Brief pause after search button click

        # 5) RESULTS
        print("Waiting for results...")
        try:
            # Wait for either results or "no trains" message
            wait.until(lambda d: 
                len(d.find_elements(By.CSS_SELECTOR, "div.form-group.no-pad.col-xs-12.bull-back.border-all")) > 0 or
                len(d.find_elements(By.XPATH, "//div[contains(text(), 'No trains available')]")) > 0
            )
            
            # Check if "no trains" message is present
            no_trains_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'No trains available')]")
            if no_trains_elements:
                print("No trains are available for this route and date.")
                return []
            
            # Find all train elements
            results_container = driver.find_element(By.CSS_SELECTOR, "div.form-group.no-pad.col-xs-12.bull-back.border-all")
            elems = results_container.find_elements(By.CSS_SELECTOR, "app-train-avl-enq > div.ng-star-inserted")
            print(f"Found {len(elems)} trains.")
            
            # Process each train
            for idx, el in enumerate(elems):
                try:
                    d = {}
                    # Train name and number
                    info_element = el.find_element(By.CSS_SELECTOR, ".train-heading strong")
                    info = info_element.text.strip()
                    if "(" in info:
                        tn, num = info.split("(", 1)
                        d["train_name"], d["train_number"] = tn.strip(), num.rstrip(")").strip()
                    else:
                        d["train_name"], d["train_number"] = info, ""
                    
                    # Schedule details
                    sched = el.find_element(By.CSS_SELECTOR, ".white-back.no-pad")
                    
                    # Get departure and arrival times
                    times = sched.find_elements(By.CSS_SELECTOR, ".time")
                    if len(times) >= 2:
                        dep = times[0].text.replace("|", "").strip()
                        arr = times[1].text.replace("|", "").strip()
                    else:
                        dep = times[0].text.replace("|", "").strip() if times else "N/A"
                        arr = "N/A"
                    
                    d["departure_time"], d["arrival_time"] = dep, arr
                    
                    # Calculate arrival date (next day if arrival time is earlier than departure)
                    dt_dep = journey_date
                    dt_arr = journey_date
                    
                    if dep != "N/A" and arr != "N/A":
                        try:
                            h_dep, m_dep = map(int, dep.split(":"))
                            h_arr, m_arr = map(int, arr.split(":"))
                            if h_arr < h_dep or (h_arr == h_dep and m_arr < m_dep):
                                dt_arr = dt_dep + datetime.timedelta(days=1)
                        except Exception as e:
                            print(f"Warning: Time parsing issue for {d.get('train_name', 'unknown')}: {e}")
                    
                    d["departure_date"] = dt_dep.strftime("%d/%m/%Y")
                    d["arrival_date"] = dt_arr.strftime("%d/%m/%Y")
                    
                    # Station info
                    d["from_station_name"], d["from_station_code"] = name_from, code_from
                    d["to_station_name"], d["to_station_code"] = name_to, code_to
                    
                    # Operating days
                    try:
                        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                        day_elements = sched.find_elements(By.CSS_SELECTOR, ".remove-padding.col-xs-4 .Y")
                        active_days = [day for day, elem in zip(days, day_elements) if elem.text.strip() == "Y"]
                        d["operating_days"] = active_days if active_days else []
                    except Exception as e:
                        print(f"Error parsing operating days: {e}")
                        d["operating_days"] = []
                    
                    # Available classes
                    try:
                        class_elements = el.find_elements(By.CSS_SELECTOR, ".pre-avl strong")
                        d["available_classes"] = [elem.text.strip() for elem in class_elements]
                    except Exception as e:
                        print(f"Error parsing available classes: {e}")
                        d["available_classes"] = []
                    
                    # Add the train to our list
                    trains.append(d)
                    print(f"Processed train {idx+1}: {d.get('train_name', 'Unknown')}")
                    
                except Exception as e:
                    print(f"Error processing train {idx+1}: {e}")
            
        except TimeoutException:
            print("Timed out waiting for results")
        except Exception as e:
            print(f"Error processing results: {e}")

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    finally:
        print("Closing browser")
        driver.quit()

    return trains

if __name__ == "__main__":
    src = input("Enter source station code (e.g. GKP): ").strip().upper()
    dst = input("Enter destination station code (e.g. DEE): ").strip().upper()
    date_in = input("Enter journey date (dd/mm/yyyy or dd-mm-yyyy): ").strip()

    try:
        print(f"Starting train scrape for {src} to {dst} on {date_in}")
        data = scrape_irctc_trains(src, dst, date_in)
        if data:
            with open("train_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n✅ Saved {len(data)} trains to train_data.json")
        else:
            print("\n❌ No train data found. This could be due to no trains on the route/date, or an error during scraping.")
    except ValueError as ve:
        print(f"❌ Input Error: {ve}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")