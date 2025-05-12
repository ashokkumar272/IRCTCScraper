import json
import datetime
import time  # for deliberate short pauses
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

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

        # Close initial popup if present
        try:
            ok = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']")))
            ok.click()
        except TimeoutException:
            pass

        # FROM station
        fld_from = short_wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "p-autocomplete[formcontrolname='origin'] input.ui-autocomplete-input")))
        fld_from.clear()
        fld_from.send_keys(from_code)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-items")))
        fld_from.send_keys(Keys.DOWN, Keys.ENTER)
        full_from = fld_from.get_attribute("value").strip()
        if "(" in full_from:
            name_from, code_from = full_from.split("(", 1)
            code_from = code_from.rstrip(")")
        else:
            name_from, code_from = full_from, from_code

        # TO station
        fld_to = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "p-autocomplete[formcontrolname='destination'] input.ui-autocomplete-input")))
        fld_to.clear()
        fld_to.send_keys(to_code)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-items")))
        fld_to.send_keys(Keys.DOWN, Keys.ENTER)
        full_to = fld_to.get_attribute("value").strip()
        if "(" in full_to:
            name_to, code_to = full_to.split("(", 1)
            code_to = code_to.rstrip(")")
        else:
            name_to, code_to = full_to, to_code

        # DATE
        fld_date = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.ui-calendar > input.ui-inputtext")))
        date_str = journey_date.strftime("%d/%m/%Y")
        fld_date.click(); time.sleep(0.2)
        fld_date.clear(); time.sleep(0.2)
        for c in date_str:
            fld_date.send_keys(c); time.sleep(0.05)
        fld_date.send_keys(Keys.TAB)
        # JS fallback
        driver.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
            fld_date, date_str)
        time.sleep(0.5)

        # SEARCH
        search_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.search_btn.train_Search")))
        search_btn.click()
        time.sleep(1)

        # RESULTS
        wait.until(lambda d: 
            d.find_elements(By.CSS_SELECTOR, "app-train-avl-enq > div.ng-star-inserted") or
            d.find_elements(By.XPATH, "//div[contains(text(),'No trains available')]"))
        if driver.find_elements(By.XPATH, "//div[contains(text(),'No trains available')]"):
            print("No trains available.")
            return []

        elems = driver.find_elements(By.CSS_SELECTOR, "app-train-avl-enq > div.ng-star-inserted")
        print(f"Found {len(elems)} train(s).")

        for idx, el in enumerate(elems, start=1):
            d = {}
            info = el.find_element(By.CSS_SELECTOR, ".train-heading strong").text.strip()
            if "(" in info:
                tn, num = info.split("(",1)
                d["train_name"], d["train_number"] = tn.strip(), num.rstrip(")").strip()
            else:
                d["train_name"], d["train_number"] = info, ""

            sched = el.find_element(By.CSS_SELECTOR, ".white-back.no-pad")
            times = sched.find_elements(By.CSS_SELECTOR, ".time")
            d["departure_time"] = times[0].text.replace("|","").strip() if times else "N/A"
            d["arrival_time"]   = times[1].text.replace("|","").strip() if len(times)>1 else "N/A"

            # Departure date
            try:
                txt = sched.find_element(By.CSS_SELECTOR, ".hidden-xs").text
                match = re.search(r'\|\s*(\w+,\s*\d+\s*\w+)', txt)
                d["departure_date"] = match.group(1).split(",",1)[1].strip() if match else date_str
            except:
                d["departure_date"] = date_str

            # Arrival date
            try:
                # If arrival time < departure time => next day
                dh, dm = map(int, d["departure_time"].split(":"))
                ah, am = map(int, d["arrival_time"].split(":"))
                if (ah,am) < (dh,dm):
                    dt = journey_date + datetime.timedelta(days=1)
                else:
                    dt = journey_date
                d["arrival_date"] = dt.strftime("%d %b")
            except:
                d["arrival_date"] = d["departure_date"]

            # Parse station names correctly (separating name and code)
            # Format is typically "STATION NAME - CODE" in the UI
            
            d["from_station_name"], d["from_station_code"] = [part.strip() for part in name_from.split("-")]
          
            d["to_station_name"], d["to_station_code"] = [part.strip() for part in name_to.split("-")]
                
            # Operating days
            try:
                days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
                elems_day = sched.find_elements(By.CSS_SELECTOR, ".remove-padding.col-xs-4 .Y")
                d["operating_days"] = [day for day, e_day in zip(days, elems_day) if e_day.text.strip()=="Y"]
            except:
                d["operating_days"] = []

            # Classes
            # Classes
            try:
                cls = el.find_elements(By.CSS_SELECTOR, ".pre-avl strong")
                class_codes = []
                for c in cls:
                    class_text = c.text.strip()
                    # Extract just the code in parentheses like (3A), (2A), (1A), (SL), etc.
                    if "(" in class_text and ")" in class_text:
                        code = class_text.split("(")[1].split(")")[0].strip()
                        class_codes.append(code)
                    else:
                        class_codes.append(class_text)  # Fallback in case format changes
                d["available_classes"] = class_codes
            except:
                d["available_classes"] = []

            trains.append(d)
            print(f"Processed train {idx}: {d['train_name']}")

        print(f"Total trains scraped: {len(trains)}")

    except Exception as e:
        print("Error:", e)
    finally:
        driver.quit()

    # Save JSON
    if trains:
        with open("train_data.json", "w", encoding="utf-8") as f:
            json.dump(trains, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved {len(trains)} trains to train_data.json")
    else:
        print("❌ No trains scraped.")

    return trains

if __name__ == "__main__":
    src = input("Source station code (e.g. GKP): ").strip().upper()
    dst = input("Destination station code (e.g. DEE): ").strip().upper()
    date = input("Journey date (dd/mm/yyyy or dd-mm-yyyy): ").strip()
    scrape_irctc_trains(src, dst, date)
