import asyncio
import os
import sys
import pandas as pd
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import List, Dict, Optional

# Add root directory to path to allow imports from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.decorators import log_execution, logger

class WebsiteScreenshotter:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.base_dir = os.path.dirname(csv_path)
        self.output_dir = os.path.join(self.base_dir, "all_sources")
        self.flat_dir = os.path.join(self.base_dir, "all_screenshots_flat")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.flat_dir, exist_ok=True)
        
    @log_execution
    async def process_websites(self) -> None:
        if not os.path.exists(self.csv_path):
            logger.error(f"CSV file not found: {self.csv_path}")
            return

        df = pd.read_csv(self.csv_path)
        tasks = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            semaphore = asyncio.Semaphore(5)
            
            for index, row in df.iterrows():
                website = row.get('website')
                
                if pd.isna(website) or not isinstance(website, str) or not website.strip():
                    continue
                    
                if not website.startswith(('http://', 'https://')):
                    # Attempt to prepend https if missing, or skip?
                    # Some data might be just domain.com
                    if not website.startswith('http'):
                         website = f"https://{website}"

                tasks.append(
                    self._process_single_website(semaphore, browser, website, row)
                )
            
            if tasks:
                await asyncio.gather(*tasks)
            else:
                logger.info("No websites found to process.")
                
            await browser.close()

    async def _process_single_website(self, semaphore: asyncio.Semaphore, browser, url: str, row_data: pd.Series) -> None:
        async with semaphore:
            place_id = row_data.get('id', 'unknown')
            name = row_data.get('name', 'unknown')
            
            folder_name = f"{str(place_id).zfill(3)}_{self._sanitize_filename(str(name))}"
            target_dir = os.path.join(self.output_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)
            
            self._write_info(target_dir, row_data)

            context_desktop = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            context_mobile = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                is_mobile=True
            )
            
            try:
                # Desktop
                page_desktop = await context_desktop.new_page()
                logger.info(f"Processing Desktop: {url} for {name}")
                desktop_path = os.path.join(target_dir, "desktop_full.png")
                await self._capture_page(page_desktop, url, desktop_path)
                
                # Copy to flat directory
                if os.path.exists(desktop_path):
                    import shutil
                    flat_name = f"{folder_name}_desktop_full.png"
                    shutil.copy2(desktop_path, os.path.join(self.flat_dir, flat_name))
                
                # Mobile
                page_mobile = await context_mobile.new_page()
                logger.info(f"Processing Mobile: {url} for {name}")
                mobile_path = os.path.join(target_dir, "mobile_full.png")
                await self._capture_page(page_mobile, url, mobile_path)
                
                # Copy to flat directory
                if os.path.exists(mobile_path):
                    import shutil
                    flat_name = f"{folder_name}_mobile_full.png"
                    shutil.copy2(mobile_path, os.path.join(self.flat_dir, flat_name))
                
            except Exception as e:
                # Log error but continue
                logger.error(f"Failed to process {url}: {e}")
            finally:
                await context_desktop.close()
                await context_mobile.close()

    async def _capture_page(self, page: Page, url: str, output_path: str) -> None:
        try:
            await page.goto(url, timeout=30000, wait_until='networkidle')
            await self._scroll_to_bottom(page)
            await page.screenshot(path=output_path, full_page=True)
        except Exception as e:
            logger.warning(f"Error capturing {url}: {e}")
            # Attempt partial screenshot if full page fails
            try:
                await page.screenshot(path=output_path, full_page=False)
            except Exception:
                pass

    async def _scroll_to_bottom(self, page: Page) -> None:
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    var totalHeight = 0;
                    var distance = 100;
                    var timer = setInterval(() => {
                        var scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;

                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 50); 
                });
            }
        """)
        await page.wait_for_timeout(1000)

    def _sanitize_filename(self, name: str) -> str:
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ' or c in ['_', '-']]).strip().replace(" ", "_")

    def _write_info(self, target_dir: str, row: pd.Series) -> None:
        info_path = os.path.join(target_dir, "info.txt")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"Name: {row.get('name', '')}\n")
            f.write(f"Category: {row.get('category', '')}\n")
            f.write(f"Address: {row.get('address', '')}\n")
            f.write(f"Website: {row.get('website', '')}\n")
            f.write(f"Phone: {row.get('phone', '')}\n")
            f.write(f"Rating: {row.get('rating', '')}\n")
            f.write(f"Reviews Count: {row.get('reviews_count', '')}\n")
            f.write(f"Working Hours: {row.get('working_hours', '')}\n")
            f.write(f"Social Media: {row.get('social_media', '')}\n")
            f.write(f"Top Review: {row.get('top_review', '')}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python screenshotter.py <path_to_places_data.csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    screenshotter = WebsiteScreenshotter(csv_path)
    asyncio.run(screenshotter.process_websites())

