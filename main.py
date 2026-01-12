#!/usr/bin/env python3
"""
Yandex Maps Scraper - Open Source Edition
Author: Koveh Bot
Description: A robust RPA tool to scrape business data, photos, and reviews from Yandex Maps.
"""

import argparse
import sys
import os
from dotenv import load_dotenv

# Add src to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.scraper import YandexMapsScraper
from src.decorators import logger

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Yandex Maps Data Scraper")
    
    parser.add_argument(
        "query", 
        type=str, 
        help="Search query (e.g., 'Coffee shop Moscow')"
    )
    
    parser.add_argument(
        "--max", "-m", 
        type=int, 
        default=int(os.getenv("MAX_RESULTS", 10)),
        help="Maximum number of results to scrape"
    )
    
    parser.add_argument(
        "--headless", 
        action="store_true",
        default=os.getenv("HEADLESS", "False").lower() == "true",
        help="Run in headless mode (no browser window)"
    )

    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Capture screenshots of websites after scraping"
    )

    args = parser.parse_args()

    print("\n🗺️  Yandex Maps Scraper")
    print("=================================")
    print(f"🔎 Query: {args.query}")
    print(f"📊 Limit: {args.max} places")
    print(f"🖥️  Headless: {args.headless}")
    print(f"📸 Screenshots: {args.screenshots}")
    print("=================================\n")

    scraper = YandexMapsScraper(headless=args.headless, max_results=args.max)
    scraper.run(args.query)

    if args.screenshots:
        import asyncio
        from website_screenshotter.screenshotter import WebsiteScreenshotter
        
        session_dir = scraper.data_manager.current_session_dir
        if session_dir:
            csv_path = os.path.join(session_dir, "places_data.csv")
            if os.path.exists(csv_path):
                logger.info("📸 Starting website screenshots...")
                screenshotter = WebsiteScreenshotter(csv_path)
                asyncio.run(screenshotter.process_websites())
            else:
                logger.warning("No CSV found to screenshot.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n🛑 Process interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"🔥 Unexpected error: {e}")
        sys.exit(1)


