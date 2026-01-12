import time
import os
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from .decorators import log_execution, handle_errors, logger
from .storage import DataManager

class YandexMapsScraper:
    """
    Main class for scraping Yandex Maps.
    """

    def __init__(self, headless: bool = False, max_results: int = 10, scrape_photos: bool = True, scrape_reviews: bool = True, photo_format: str = "jpg", max_photos: int = 5, browser_type: str = "chrome"):
        self.headless = headless
        self.max_results = max_results
        self.scrape_photos = scrape_photos
        self.scrape_reviews = scrape_reviews
        self.photo_format = photo_format.lower()
        self.max_photos = max_photos
        self.browser_type = browser_type.lower()
        self.driver: Optional[webdriver.Chrome] = None
        self.on_progress = None # Callback function for progress updates
        self.wait: Optional[WebDriverWait] = None
        self.data_manager = DataManager()
        self.session = requests.Session()
        
        # Configure requests session
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    @log_execution
    def setup_driver(self):
        """Initializes the WebDriver based on the selected browser."""
        if self.browser_type == "chrome":
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            
            # Mac OS specific: Check common Chrome binary locations
            if sys.platform == "darwin":
                binary_locations = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium"
                ]
                for loc in binary_locations:
                    if os.path.exists(loc):
                        options.binary_location = loc
                        break
            
            import tempfile
            options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
            
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
        elif self.browser_type == "firefox":
            from webdriver_manager.firefox import GeckoDriverManager
            options = webdriver.FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")
            
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            
        elif self.browser_type == "edge":
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            options = webdriver.EdgeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--start-maximized")
            
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=options)
            
        elif self.browser_type == "safari":
            if sys.platform != "darwin":
                raise RuntimeError("Safari is only available on macOS.")
            
            options = webdriver.SafariOptions()
            # Safari doesn't support headless mode in the same way via options generally
            # But we can try to minimize interference
            self.driver = webdriver.Safari(options=options)
            if self.headless:
                logger.warning("Headless mode not fully supported for Safari. Running visible.")
            self.driver.maximize_window()
            
        else:
            raise ValueError(f"Unsupported browser: {self.browser_type}")

        self.wait = WebDriverWait(self.driver, 10)
        logger.info(f"🖥️  {self.browser_type.title()} WebDriver initialized")

    @log_execution
    def run(self, query: str):
        """Main execution flow."""
        try:
            self.setup_driver()
            self.data_manager.setup_session_directory(query)
            
            self.driver.get("https://yandex.ru/maps")
            logger.info(f"🔍 Searching for: {query}")
            
            self._perform_search(query)
            
            # Scroll and collect links to all places first
            if self.on_progress:
                self.on_progress(0, self.max_results, "Scrolling and collecting links...")
                
            place_links = self._scroll_and_collect_results()
            total_links = len(place_links)
            logger.info(f"📍 Found {total_links} places to process")
            
            extracted_data = []
            
            for i, link in enumerate(place_links):
                msg = f"Processing place {i+1}/{total_links}"
                logger.info(f"🏢 {msg}...")
                
                if self.on_progress:
                    self.on_progress(i, total_links, msg)
                
                try:
                    # Normalize URL to ensure we start at the main view
                    main_url = link
                    if "/gallery/" in main_url:
                        main_url = main_url.replace("/gallery/", "/")
                    if "tab=gallery" in main_url:
                        import re
                        main_url = re.sub(r'tab=gallery&?', '', main_url)
                    
                    self.driver.get(main_url)
                    time.sleep(3) # Wait for page load
                    
                    place_data = self._extract_details(i + 1, query)
                    if place_data:
                        extracted_data.append(place_data)
                        
                except Exception as e:
                    logger.error(f"Error processing place {i+1}: {e}")
                    continue
            
            # Save final results
            if self.on_progress:
                self.on_progress(total_links, total_links, "Saving data...")

            # Add metadata to each record
            for item in extracted_data:
                item['search_query'] = query
                
            self.data_manager.save_json(extracted_data)
            self.data_manager.export_to_csv(extracted_data)
            self.data_manager.save_to_sqlite(extracted_data)
            self.data_manager.export_to_excel(extracted_data)
            
        except Exception as e:
            logger.critical(f"Critical failure: {e}")
        finally:
            if self.driver:
                self.driver.quit()

    def _perform_search(self, query: str):
        """Enters the query into the search box."""
        try:
            # Try multiple selectors for the search input
            search_input = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "input.input__control, input[type='text']"
            )))
            search_input.clear()
            search_input.send_keys(query)
            search_input.send_keys(Keys.RETURN)
            
            # Wait for results container
            self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, ".search-list-view, .search-snippet-view"
            )))
            time.sleep(2)
        except TimeoutException:
            logger.error("Search box not found or results didn't load.")
            raise

    def _scroll_and_collect_results(self) -> List[str]:
        """
        Scrolls the results list sidebar until enough results are loaded.
        Returns a list of URLs (strings) for the places.
        """
        logger.info("📜 Scrolling to load results...")
        
        last_count = 0
        attempts = 0
        max_attempts = 5 # Stop if no new items after 5 scrolls
        
        links = set()
        
        while True:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".search-snippet-view")
            current_count = len(elements)
            
            # Collect links from current elements
            for el in elements:
                try:
                    href = None
                    # Try multiple selectors for the link
                    selectors = [
                        ".search-snippet-view__link-overlay",
                        ".search-snippet-view__title-link", 
                        "a.search-snippet-view__link-overlay",
                        ".search-snippet-view__body a"
                    ]
                    
                    for sel in selectors:
                        try:
                            link_el = el.find_element(By.CSS_SELECTOR, sel)
                            href = link_el.get_attribute("href")
                            if href:
                                break
                        except:
                            continue
                            
                    if href:
                        links.add(href)
                except:
                    pass
            
            if len(links) >= self.max_results:
                logger.info(f"✅ Collected {len(links)} links (Target: {self.max_results})")
                return list(links)[:self.max_results]
            
            if current_count == last_count:
                attempts += 1
                if attempts >= max_attempts:
                    logger.warning("⚠️ No new results loaded after multiple scrolls. Stopping.")
                    return list(links)[:self.max_results]
            else:
                attempts = 0
                
            last_count = current_count
            logger.info(f"   Loaded {current_count} snippets, {len(links)} unique links...")
            
            try:
                if elements:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", elements[-1])
                    time.sleep(1.5) # Wait for network load
            except Exception:
                break
                
        return list(links)[:self.max_results]

    @handle_errors(default_return=None)
    def _extract_details(self, index: int, query: str) -> Dict[str, Any]:
        """Extracts comprehensive details from the currently opened place panel."""
        
        # Wait for the header to be visible (confirmation that details loaded)
        try:
            self.wait.until(EC.visibility_of_element_located((
                By.CSS_SELECTOR, ".card-title-view__title, .orgpage-header-view__title, .business-card-view"
            )))
        except TimeoutException:
            logger.warning("Details panel didn't load in time.")
            return None

        # Ensure we are on the Overview tab
        self._switch_to_overview()
        
        # Scroll down to load more content (address, contacts, photos)
        self.driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1)
        self.driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1)

        # STEP 1: Get the name first (needed for folder creation)
        name = self._get_text([
            ".orgpage-header-view__title", 
            ".card-title-view__title", 
            "h1",
            ".business-card-title-view__title"
        ])
        if not name:
            name = self._get_attribute(["meta[itemprop='name']"], "content")

        # STEP 2: Extract category and description BEFORE navigating away
        # Category - look for links with /category/ in href
        category = ""
        try:
            category_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/category/']")
            categories = []
            for link in category_links:
                text = link.text.strip()
                if text and text not in categories:
                    categories.append(text)
            if categories:
                category = ", ".join(categories[:3])  # Limit to first 3 categories
        except Exception:
            pass
        
        # Fallback to other selectors
        if not category:
            category = self._get_text([
                ".orgpage-header-view__categories a",
                ".business-categories-view__category",
                ".business-card-title-view__category",
                ".card-title-view__category"
            ])

        # Description - visible in the header area
        description = self._get_text([
            ".orgpage-header-view__description",
            ".business-card-title-view__description",
            ".card-title-view__description",
            ".business-card-title-view__subtitle",
            ".orgpage-header-view__subtitle"
        ])

        # STEP 3: Create folder for photos
        place_folder = self.data_manager.create_place_folder(name or f"Place_{index}", index)
        
        photos = []
        if self.scrape_photos:
            # STEP 4: Navigate to gallery for photos
            try:
                photo_gallery_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".business-photos-view__more, .business-card-title-view__photo, .business-photos-view")
                if photo_gallery_buttons:
                    logger.info("Opening photo gallery...")
                    self.driver.execute_script("arguments[0].click();", photo_gallery_buttons[0])
                    time.sleep(3.5)
            except Exception as e:
                logger.debug(f"Failed to open photo gallery: {e}")

            # Try navigating to /gallery/ URL if images not found
            if not self.driver.find_elements(By.CSS_SELECTOR, ".media-wrapper__media"):
                current_url = self.driver.current_url
                if "/gallery/" not in current_url:
                    try:
                        if "?" in current_url:
                            base, qry = current_url.split("?", 1)
                            gallery_url = f"{base}gallery/?{qry}"
                        else:
                            gallery_url = f"{current_url.rstrip('/')}/gallery/"
                        
                        logger.info(f"Navigating to gallery URL: {gallery_url}")
                        self.driver.get(gallery_url)
                        time.sleep(3.5)
                    except Exception as e:
                        logger.debug(f"Failed to navigate to gallery URL: {e}")

            # STEP 4: Download photos
            photos = self._extract_photos(place_folder)

            # STEP 6: Go back to overview for text extraction
            if "/gallery/" in self.driver.current_url:
                # Navigate back to the main page
                main_url = self.driver.current_url.replace("/gallery/", "/")
                self.driver.get(main_url)
                time.sleep(2)
                self._switch_to_overview()
                # Scroll to load content
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1)

        # STEP 7: Extract remaining text data (address, phone, etc.)
        
        # Features
        features = {}
        try:
            bool_features = self.driver.find_elements(By.CSS_SELECTOR, ".business-features-view__bool-text")
            for bf in bool_features:
                text = bf.text.strip()
                if text:
                    features[text] = True
            
            valued_features = self.driver.find_elements(By.CSS_SELECTOR, ".business-features-view__valued")
            for vf in valued_features:
                try:
                    title = vf.find_element(By.CSS_SELECTOR, ".business-features-view__valued-title").text.strip().rstrip(":")
                    value = vf.find_element(By.CSS_SELECTOR, ".business-features-view__valued-value").text.strip()
                    if title and value:
                        features[title] = value
                except:
                    continue
        except Exception as e:
            logger.debug(f"Features extraction error: {e}")
        
        # Address
        address = self._get_attribute(["meta[itemprop='address']"], "content")
        if not address:
            address = self._get_text([
                ".business-contacts-view__address-link",
                ".business-contacts-view__address",
                "[data-id='address']"
            ])

        # Website
        website = self._get_attribute([".business-urls-view__link", "a[itemprop='url']"], "href")
        if not website:
            website = self._get_text([".business-urls-view__text"])

        # Phone
        phone = self._get_text([
            "span[itemprop='telephone']",
            ".card-phones-view__number",
            ".business-phone-view__number"
        ])

        # Working Hours
        working_hours = self._get_all_attributes("meta[itemprop='openingHours']", "content")
        if not working_hours:
            working_hours_text = self._get_text([".business-working-status-view__text"])
            if working_hours_text:
                working_hours = [working_hours_text]

        # Social media
        social_media = self._extract_social_links()

        # STEP 7: Build data dict
        data = {
            "id": index,
            "name": name,
            "category": category,
            "description": description,
            "features": features,
            "address": address,
            "website": website,
            "phone": phone,
            "rating": self._extract_rating(),
            "reviews_count": self._extract_reviews_count(),
            "working_hours": working_hours,
            "folder_path": place_folder,
            "link": self.driver.current_url,
            "social_media": social_media,
            "photos": photos
        }
        
        # STEP 8: Extract reviews (requires tab switch)
        if self.scrape_reviews:
            data["reviews"] = self._extract_reviews()
        else:
            data["reviews"] = []
        
        return data

    def _switch_to_overview(self):
        """Switches to the Overview/About tab if not already active."""
        try:
            tabs = self.driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'tabs-view__tab')] | //div[contains(text(), 'Обзор')] | //div[contains(text(), 'Overview')] | //div[contains(@class, '_name_overview')]")
            
            for tab in tabs:
                text = tab.text.lower()
                if "обзор" in text or "overview" in text or "about" in text:
                    if "_selected" not in tab.get_attribute("class"):
                        try:
                            self.driver.execute_script("arguments[0].click();", tab)
                            time.sleep(1.5)
                        except:
                            pass
                    break
        except Exception:
            pass

    def _get_text(self, selectors: List[str]) -> str:
        """Helper to try multiple selectors and return the first match's text."""
        for selector in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                # Try getting visible text first
                text = el.text.strip()
                if text:
                    return text
                # Fallback to textContent (hidden text)
                text = el.get_attribute("textContent").strip()
                if text:
                    return text
            except NoSuchElementException:
                continue
        return ""

    def _get_text_list(self, selectors: List[str]) -> List[str]:
        """Helper to get text from all matching elements."""
        results = []
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    text = el.text.strip()
                    if not text:
                        text = el.get_attribute("textContent").strip()
                    if text and text not in results:
                        results.append(text)
                if results: # If we found something with this selector, stop
                    break
            except Exception:
                continue
        return results

    def _get_attribute(self, selectors: List[str], attribute: str) -> str:
        """Helper to get an attribute from the first matching selector."""
        for selector in selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                val = el.get_attribute(attribute)
                if val:
                    return val.strip()
            except NoSuchElementException:
                continue
        return ""

    def _get_all_attributes(self, selector: str, attribute: str) -> List[str]:
        """Helper to get an attribute from all matching elements."""
        results = []
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                val = el.get_attribute(attribute)
                if val:
                    results.append(val.strip())
        except Exception:
            pass
        return results

    def _extract_rating(self) -> str:
        """Extract rating as a clean number."""
        rating_text = self._get_text([
            ".business-rating-view__rating",
            ".business-rating-badge-view__rating"
        ])
        if rating_text:
            # Extract number from text like "Rating 4.9" or just "4.9"
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
            if match:
                return match.group(1)
        return ""

    def _extract_reviews_count(self) -> str:
        """Extract reviews count as a clean number."""
        count_text = self._get_text([
            ".business-header-rating-view__text",
            ".business-rating-view__count",
            ".business-rating-badge-view__count",
            ".business-header-rating-view__count",
            "span.business-rating-amount-view",
            ".orgpage-header-view__rating-label"
        ])
        if count_text:
            # Extract number from text like "1611 ratings" or "123 reviews" or just "123"
            import re
            match = re.search(r'(\d+)', count_text)
            if match:
                return match.group(1)
        return ""

    def _extract_social_links(self) -> List[str]:
        """Extracts social media links."""
        links = []
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".business-contacts-view__social-button a")
            for el in elements:
                href = el.get_attribute("href")
                if href:
                    links.append(href)
        except Exception:
            pass
        return links

    def _extract_photos(self, folder: str) -> List[str]:
        """Downloads visible photos from gallery."""
        downloaded_paths = []
        try:
            # Transfer cookies from driver to session
            for cookie in self.driver.get_cookies():
                self.session.cookies.set(cookie['name'], cookie['value'])

            # Based on user HTML: img.media-wrapper__media has src directly
            imgs = self.driver.find_elements(By.CSS_SELECTOR,
                "img.media-wrapper__media, "
                ".media-wrapper__media[src], "
                ".media-gallery img, "
                ".business-photos-view__photo-image img, "
                ".orgpage-photos-view__photo img"
            )
            
            logger.info(f"Found {len(imgs)} potential images in gallery")

            for i, img in enumerate(imgs[:self.max_photos]):  # Limit to max_photos
                src = img.get_attribute("src")
                
                # Check for srcset if src is missing or small
                srcset = img.get_attribute("srcset")
                if srcset:
                    # simplistic srcset parsing: take the last url (usually largest)
                    try:
                        # "url 1x, url 2x" -> split comma, take last, split space, take first part
                        src = srcset.split(",")[-1].strip().split(" ")[0]
                    except:
                        pass

                if not src:
                    logger.debug(f"Image {i+1}: no src attribute")
                    continue
                    
                # Skip non-image sources (check path, not domain)
                url_path = src.split("?")[0].split("/")[-1] if "/" in src else src
                if any(x in url_path.lower() for x in ["icon", "logo", "svg"]):
                    logger.debug(f"Image {i+1}: skipping (icon/logo/svg in path)")
                    continue
                
                logger.debug(f"Image {i+1} original src: {src[:80]}...")
                
                # Skip very small thumbnails by checking URL patterns
                if "S_height" in src or "XXS" in src or "XS_height" in src:
                    # Replace with high-res version
                    src = src.replace("S_height", "XL").replace("XXS_height", "XL").replace("XS_height", "XL")
                
                # Other high-res replacements
                src = src.replace("M_height", "XL").replace("L_height", "XL")
                src = src.replace("200x200", "orig").replace("400x400", "orig").replace("600x600", "orig")
                src = src.replace("priority-headline-background", "XL")

                try:
                    filename = f"photo_{i+1}.jpg"
                    path = os.path.join(folder, "photos", filename)

                    resp = self.session.get(src, timeout=15, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://yandex.com/maps'
                    })
                    
                    logger.debug(f"Image {i+1}: HTTP {resp.status_code}, size {len(resp.content)} bytes")
                    
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        # Save logic with optional conversion
                        if self.photo_format in ["webp", "png"] and self.photo_format != "jpg":
                            try:
                                from PIL import Image
                                from io import BytesIO
                                
                                img_data = BytesIO(resp.content)
                                image = Image.open(img_data)
                                
                                filename = f"photo_{i+1}.{self.photo_format}"
                                path = os.path.join(folder, "photos", filename)
                                
                                image.save(path, format=self.photo_format.upper())
                                downloaded_paths.append(path)
                                logger.info(f"📷 Saved photo {i+1} as {self.photo_format}: {filename}")
                            except Exception as conversion_error:
                                logger.warning(f"Failed to convert image {i+1}, saving as original: {conversion_error}")
                                # Fallback to original
                                filename = f"photo_{i+1}.jpg"
                                path = os.path.join(folder, "photos", filename)
                                with open(path, 'wb') as f:
                                    f.write(resp.content)
                                downloaded_paths.append(path)
                        else:
                            # Standard save
                            with open(path, 'wb') as f:
                                f.write(resp.content)
                            downloaded_paths.append(path)
                            logger.info(f"📷 Downloaded photo {i+1}: {filename}")
                    else:
                        logger.debug(f"Image {i+1}: skipped (status={resp.status_code}, size={len(resp.content)})")
                except Exception as e:
                    logger.warning(f"Failed to download photo {i+1}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Photo extraction error: {e}")

        return downloaded_paths

    def _extract_reviews(self) -> List[Dict[str, str]]:
        """Extracts top reviews."""
        reviews = []
        try:
            # Switch to reviews tab
            # Try finding the tab button using updated selectors
            tabs = self.driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'tabs-view__tab')] | //div[contains(text(), 'Отзывы')] | //div[contains(text(), 'Reviews')] | //div[contains(@class, '_name_reviews')]")
            
            for tab in tabs:
                if "отзывы" in tab.text.lower() or "reviews" in tab.text.lower():
                    # Check if already selected
                    if "_selected" not in tab.get_attribute("class"):
                        self.driver.execute_script("arguments[0].click();", tab)
                        time.sleep(2)
                    break
            
            # Collect review items
            review_items = self.driver.find_elements(By.CSS_SELECTOR, ".business-review-view")
            
            # If no items found, maybe we need to scroll the reviews container?
            if not review_items:
                # Try scrolling the page a bit
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(1)
                review_items = self.driver.find_elements(By.CSS_SELECTOR, ".business-review-view")

            for item in review_items[:5]: # Top 5
                try:
                    # Rating extraction logic update: rating text might be hidden or in aria-label
                    rating_text = ""
                    try:
                        # Try finding the rating text first
                        rating_el = item.find_element(By.CSS_SELECTOR, ".business-rating-badge-view__rating-text")
                        rating_text = rating_el.text.strip()
                    except:
                        pass
                    
                    if not rating_text:
                        # Try aria-label on stars container
                        try:
                            stars_el = item.find_element(By.CSS_SELECTOR, ".business-rating-badge-view__stars")
                            aria_label = stars_el.get_attribute("aria-label")
                            if aria_label:
                                # Extract number from "Rating 5 Out of 5"
                                import re
                                match = re.search(r"(\d+(\.\d+)?)", aria_label)
                                if match:
                                    rating_text = match.group(1)
                        except:
                            pass
                    
                    # Author extraction
                    author_text = self._get_text_from_element(item, ".business-review-view__author-name span[itemprop='name']")
                    if not author_text:
                         author_text = self._get_text_from_element(item, ".business-review-view__author-name")

                    # Text extraction
                    review_body = self._get_text_from_element(item, ".business-review-view__body .spoiler-view__text")
                    if not review_body:
                        # Fallback for short reviews without spoiler
                        review_body = self._get_text_from_element(item, ".business-review-view__body")

                    r = {
                        "author": author_text,
                        "text": review_body,
                        "rating": rating_text,
                        "date": self._get_text_from_element(item, ".business-review-view__date")
                    }
                    # Only add if we have at least some content
                    if (r["text"] or r["author"]) and r["rating"]:
                        reviews.append(r)
                except Exception as e:
                    logger.debug(f"Failed to parse individual review: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Review extraction error: {e}")
        
        return reviews

    def _get_text_from_element(self, parent, selector):
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return ""