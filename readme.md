# IRCTC Train Availability Scraper

A Selenium-based Python script to scrape train availability and schedule details from the IRCTC “Train Search” page. Outputs a JSON file (`train_data.json`) containing all trains, timings, dates, classes, operating days, and station codes for a given source, destination, and journey date.

---

## Table of Contents

1. [Features](#features)  
2. [Prerequisites](#prerequisites)  
3. [Installation](#installation)  
4. [Usage](#usage)  
5. [Output](#output)  
6. [Project Structure](#project-structure)  
7. [Troubleshooting](#troubleshooting)  
8. [Contributing](#contributing)  
9. [License](#license)  

---

## Features

- Headless (optional) Selenium Chrome scraping  
- Automatic station-code autocomplete  
- Custom date normalization (`dd/mm/YYYY` or `dd-mm-YYYY`)  
- Parses:
  - Train name & number  
  - Departure/arrival times & inferred dates  
  - Available classes  
  - Operating days  
  - Origin/destination station names & codes  
- Saves results as pretty-printed JSON  

---

## Prerequisites

- Python 3.7+  
- Google Chrome (compatible with ChromeDriver)  
- Internet connectivity  

---

## Installation

1. **Clone this repository**  
   ```bash
   git clone https://github.com/rajatsinghten/IRCTCScraper.git
   cd irctc-scraper
   ```

2. **Create & activate a virtual environment** (recommended)  
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate    # Windows
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
   _Contents of `requirements.txt`:_
   ```
   selenium
   webdriver-manager
   ```

---

## Usage

1. **Run the script**  
   ```bash
   python train_scraper.py
   ```
2. **Enter prompts**  
   ```
   Source station code (e.g. GKP): GKP
   Destination station code (e.g. DEE): DEE
   Journey date (dd/mm/yyyy or dd-mm-yyyy): 15/05/2025
   ```
3. **Watch the console**  
   - Browser will open (headful by default; uncomment `--headless` to hide it)  
   - Popup “OK” dialogs are auto-dismissed  
   - The script prints each train processed and a summary count  

4. **Result**  
   A file named `train_data.json` will be created in the project root.

---

## Output

`train_data.json` contains an array of objects like:

```json
[
  {
    "train_name": "XYZ EXPRESS",
    "train_number": "12345",
    "departure_time": "14:30",
    "arrival_time": "20:45",
    "departure_date": "15 May",
    "arrival_date": "15 May",
    "from_station_name": "Gorakhpur",
    "from_station_code": "GKP",
    "to_station_name": "Delhi",
    "to_station_code": "DEE",
    "operating_days": ["Mon", "Wed", "Fri"],
    "available_classes": ["1A", "2A", "3A", "SL"]
  }
]
```

---

## Project Structure

```
.
├── train_scraper.py      # Main scraper script
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Troubleshooting

- **ChromeDriver Version Mismatch**  
  Ensure your local Chrome’s major version matches the ChromeDriver installed by `webdriver-manager`.
- **No Trains Found**  
  - Verify station codes and date format.  
  - Check IRCTC site availability and CAPTCHA (may block automated access).
- **Timeouts / Element Not Found**  
  Increase `WebDriverWait` timeouts in `train_scraper.py`.

---

## Contributing

1. Fork the repo  
2. Create a feature branch (`git checkout -b feature/foo`)  
3. Commit your changes (`git commit -am 'Add foo'`)  
4. Push to the branch (`git push origin feature/foo`)  
5. Open a Pull Request

---

## License

This project is licensed under the **MIT License**.  
