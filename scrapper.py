from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import datetime

def format_run_days(operating_days):
    day_map = {
        "M": "Mon", "T": "Tue", "W": "Wed", "T": "Thu", "F": "Fri", "S": "Sat", "S": "Sun"
    }
    days = []
    for i, day in enumerate(operating_days):
        if day == "Y":
            days.append(day_map.get(i, ""))
    return days

def convert_time_to_24hr(time_str):
    """Convert time format to 24-hour format if needed."""
    try:
        return datetime.datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M")
    except ValueError:
        return time_str  # Already in 24-hour format

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
        
        # Handle any initial popups
        try:
            alert_close = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'OK')]")))
            alert_close.click()
        except:
            pass
        
        # Enter From and To station
        from_input = short_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p-autocomplete[formcontrolname='origin'] input.ui-autocomplete-input")))
        from_input.clear()
        from_input.send_keys(from_station)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-panel .ui-autocomplete-items")))
        from_input.send_keys(Keys.DOWN)
        from_input.send_keys(Keys.ENTER)

        to_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "p-autocomplete[formcontrolname='destination'] input.ui-autocomplete-input")))
        to_input.clear()
        to_input.send_keys(to_station)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-autocomplete-panel .ui-autocomplete-items")))
        to_input.send_keys(Keys.DOWN)
        to_input.send_keys(Keys.ENTER)

        # Enter date
        date_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.ui-calendar > input.ui-inputtext")))
        date_input.clear()
        driver.execute_script("arguments[0].value = arguments[1]", date_input, date)
        driver.find_element(By.TAG_NAME, 'body').click()
        
        # Click Search button
        search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search_btn.train_Search")))
        search_button.click()
        
        # Wait for results
        train_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
            "div.form-group.no-pad.col-xs-12.bull-back.border-all")))

        # Extracting train information
        train_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 
            "div.form-group.no-pad.col-xs-12.bull-back.border-all > app-train-avl-enq > div.ng-star-inserted")))
        
        if len(train_elements) == 0:
            print("No trains found.")
        
        for train_element in train_elements:
            train_dict = {}

            # Extract train name and number
            train_info = train_element.find_element(By.CSS_SELECTOR, ".train-heading strong").text.strip()
            if '(' in train_info and ')' in train_info:
                train_dict['train_name'], train_dict['train_number'] = train_info.split('(')
                train_dict['train_number'] = train_dict['train_number'][:-1]
                train_dict['train_name'] = train_dict['train_name'].strip()
            else:
                train_dict['train_name'] = train_info

            # Extract schedule (Departure & Arrival Time)
            schedule_div = train_element.find_element(By.CSS_SELECTOR, ".white-back.no-pad")
            times = schedule_div.find_elements(By.CSS_SELECTOR, ".time")
            train_dict['from_std'] = convert_time_to_24hr(times[0].text.strip()) if len(times) > 0 else "N/A"
            train_dict['to_std'] = convert_time_to_24hr(times[1].text.strip()) if len(times) > 1 else "N/A"
            
            # Extract Stations
            stations = schedule_div.find_elements(By.CSS_SELECTOR, ".col-xs-12.hidden-lg.hidden-md.hidden-sm")
            if stations:
                train_dict['from_station_name'] = stations[0].text.strip()
                train_dict['to_station_name'] = stations[1].text.strip()

            # Extract Days of Operation
            days_div = schedule_div.find_element(By.CSS_SELECTOR, ".remove-padding.col-xs-4.text-center")
            operating_days = ''.join([day.text for day in days_div.find_elements(By.CSS_SELECTOR, ".Y")])
            train_dict['run_days'] = format_run_days(operating_days)

            # Extract Available Classes
            class_elements = train_element.find_elements(By.CSS_SELECTOR, ".pre-avl")
            train_dict['class_type'] = []
            for class_elem in class_elements:
                class_name = class_elem.find_element(By.TAG_NAME, 'strong').text.strip()
                train_dict['class_type'].append(class_name)

            # Duration
            train_dict['duration'] = schedule_div.find_element(By.CSS_SELECTOR, ".duration").text.strip()

            # Add to train list
            train_dict['train_date'] = date
            train_dict['special_train'] = False  # Assuming no special trains unless specified
            train_dict['train_type'] = "RAJ"  # Can be dynamic based on specific data
            train_dict['from_sta'] = train_dict['from_std']
            train_dict['to_sta'] = train_dict['to_std']
            train_dict['local_train_from_sta'] = int(train_dict['from_std'].split(":")[0])*60 + int(train_dict['from_std'].split(":")[1])  # Example conversion
            
            # Add formatted dictionary to list
            train_list.append(train_dict)
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Close the browser
        driver.quit()
    
    return train_list

def main():
    # Get user input for stations and date
    from_station = input("Enter the source station: ")
    to_station = input("Enter the destination station: ")
    date = input("Enter the date (format: dd-mm-yyyy): ")
    
    # Scrape the train data
    train_data = scrape_irctc_trains(from_station, to_station, date)

    # Format data to match the mockTrains format
    mock_trains = []
    for train in train_data:
        mock_train = {
            "train_number": train['train_number'],
            "train_name": train['train_name'],
            "run_days": train['run_days'],
            "train_src": train['from_station_name'],
            "train_dstn": train['to_station_name'],
            "from_std": train['from_std'],
            "from_sta": train['from_sta'],
            "local_train_from_sta": train['local_train_from_sta'],
            "to_sta": train['to_sta'],
            "to_std": train['to_std'],
            "from_day": 0,  # Can be computed based on the train data
            "to_day": 1,  # Can be computed based on the train data
            "d_day": 0,  # Can be computed based on train's departure
            "from": train['from_station_name'],
            "to": train['to_station_name'],
            "from_station_name": train['from_station_name'],
            "to_station_name": train['to_station_name'],
            "duration": train['duration'],
            "special_train": train['special_train'],
            "train_type": train['train_type'],
            "train_date": train['train_date'],
            "class_type": train['class_type'],
        }
        mock_trains.append(mock_train)

    # Example output
    print(mock_trains)

if __name__ == "__main__":
    main()
