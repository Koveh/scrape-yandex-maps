# 🗺️ Yandex Maps Scraper - Open Source Edition

**Author**: Daniil Kovekh  
**Project Status**: Educational / Research Prototype  
**License**: MIT (See disclaimer below)

A powerful, user-friendly tool to scrape business data, reviews, and photos from Yandex Maps. Built with Python, Selenium, and Streamlit.

---

## 🚀 Features

-   **Data Extraction**: Scrapes name, address, phone, website, working hours, social media links, and more.
-   **Photos**: Downloads high-quality photos to organized folders.
-   **Reviews**: Extracts recent reviews with ratings and authors.
-   **Multi-Format Export**: Saves data as **CSV**, **JSON**, **SQLite**, and **Excel (.xlsx)**.
-   **User Interface**: Easy-to-use **Streamlit** web dashboard.
-   **Headless Mode**: Runs in the background (server-ready) or visible mode for debugging.

---

## ⚠️ Disclaimer & Legal Notice

**This tool is for EDUCATIONAL and RESEARCH purposes only.**

-   **Not for Commercial Use**: Do not use this tool to scrape data for commercial resale or competitive intelligence without permission.
-   **Terms of Service**: Automated scraping may violate Yandex Maps' Terms of Service. You are solely responsible for compliance with all applicable laws and regulations in your jurisdiction.
-   **Robot Traffic**: This tool uses Selenium to simulate a real user. Excessive use may lead to IP bans. Use responsibly with reasonable limits.

**This is an individual open-source project, not associated with any studio or corporation.**

---

## 🛠️ Installation

### Prerequisites
-   **Python 3.8+** installed on your system.
-   **Web Browser**: One of the following browsers must be installed:
    -   **Google Chrome** (recommended) - [Download](https://www.google.com/chrome/)
    -   **Firefox** - [Download](https://www.mozilla.org/firefox/)
    -   **Microsoft Edge** - Pre-installed on Windows
    -   **Safari** (macOS only) - Pre-installed on macOS
    
    > **Note for macOS users**: If using Chrome and you get a "cannot find Chrome binary" error, make sure Chrome is installed in `/Applications/` (not in your user folder). Alternatively, use Safari which is pre-installed.

### Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Koveh/scrape-yandex-maps.git
    cd scrape-yandex-maps
    ```

2.  **Create a virtual environment (Recommended)**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🖥️ Usage

You can run the scraper in two ways: using the **GUI (Streamlit)** or the **Command Line**.

### Option 1: Web Interface (Streamlit) - Recommended

The easiest way to use the tool.

```bash
streamlit run streamlit_app.py
```

This will open `http://localhost:8501` in your browser.
-   **Region/City**: Enter the target city (e.g., "Moscow").
-   **Search Query**: Enter the business type (e.g., "Coffee shop").
-   **Max Results**: Limit how many places to scrape.
-   **Browser**: Select which browser to use (Chrome, Firefox, Edge, or Safari).
-   **Headless Mode**:
    -   **Checked (Default)**: Browser runs hidden in the background. Use this for servers or if you don't want to be disturbed.
    -   **Unchecked**: You will see the browser window open and navigate automatically. Useful for debugging or seeing what's happening.
    -   **Note**: Safari does not fully support headless mode and will always run visibly.

### Option 2: Command Line Interface (CLI)

For integration into scripts or quick runs.

```bash
python main.py "Coffee shop Moscow" --max 10
```

**Arguments:**
-   `query`: The search term (e.g., "Coffee shop Moscow").
-   `--max`, `-m`: Maximum number of results (default: 10).
-   `--headless`: Run without visible browser window.
-   `--browser`: Browser to use (`chrome`, `firefox`, `edge`, or `safari`). Default: `chrome`.
-   `--screenshots`: Capture a screenshot of each place's website (requires Playwright).

**Example with browser selection:**
```bash
python main.py "Restaurant Moscow" --max 20 --browser firefox --headless
```

---

## 📂 Output Data

All data is saved in the `output_data` directory, organized by timestamp and query.

Example structure:
```
output_data/
└── 20260112_120000_Coffee_shop_Moscow/
    ├── places_data.csv       # Spreadsheet for Excel/Analysis
    ├── places_data.xlsx      # Excel file
    ├── places_data.json      # Full data structure
    ├── places_data.db        # SQLite database
    ├── 001_Coffee_Mania/     # Folder for specific place
    │   └── photos/           # Downloaded images
    └── ...
```

---

## 🤖 Advanced: Running on a Server

This tool uses **Selenium** and **Chrome**. To run it on a headless Linux server (e.g., VPS), ensure you have:
1.  Chrome installed (`google-chrome-stable`).
2.  Drivers installed (`chromedriver` is managed automatically by `webdriver-manager`).
3.  Run with **Headless Mode** enabled.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a Pull Request.

**Author**: Daniil Kovekh
