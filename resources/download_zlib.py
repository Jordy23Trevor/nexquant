import os
import sys
import json
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("zlib_downloader")

BASE_DIR = Path(__file__).parent
BOOKS_DIR = BASE_DIR / "books"
CREDS_FILE = BASE_DIR / "credentials.json"
STATUS_FILE = BASE_DIR / "download_status.json"

BOOKS_TO_DOWNLOAD = [
    {"title": "Trading Psychology 2.0", "author": "Brett Steenbarger", "filename": "Brett N. Steenbarger - Trading Psychology 2.0.pdf"},
    {"title": "The Little Book of Behavioral Investing", "author": "James Montier", "filename": "James Montier - The Little Book of Behavioral Investing.pdf"},
    {"title": "Technical Analysis of the Financial Markets", "author": "John J. Murphy", "filename": "John J. Murphy - Technical Analysis of the Financial Markets.pdf"},
    {"title": "Algorithmic Trading", "author": "Ernest Chan", "filename": "Ernest Chan - Algorithmic Trading.pdf"},
    {"title": "Cryptoassets", "author": "Chris Burniske", "filename": "Chris Burniske - Cryptoassets.pdf"},
    {"title": "Forex Price Action Scalping", "author": "Bob Volman", "filename": "Bob Volman - Forex Price Action Scalping.pdf"},
    {"title": "The Hacking of the American Mind", "author": "Robert Lustig", "filename": "Robert Lustig - The Hacking of the American Mind.pdf"},
]

def load_credentials():
    if CREDS_FILE.exists():
        with open(CREDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"email": "jordytrevor633@gmail.com", "password": "Ksjt@237"}

def update_status(book_title, status, path=None, error=None):
    current_status = {}
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                current_status = json.load(f)
        except Exception:
            pass
    
    if "books" not in current_status:
        current_status["books"] = {}
    
    entry = {"status": status}
    if path:
        entry["path"] = str(path)
    if error:
        entry["error"] = error
    
    current_status["books"][book_title] = entry
    current_status["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(current_status, f, indent=2, ensure_ascii=False)

def download_book(page, book_info):
    title = book_info["title"]
    author = book_info["author"]
    filename = book_info["filename"]
    dest_path = BOOKS_DIR / filename
    
    if dest_path.exists() and dest_path.stat().st_size > 100000:
        log.info(f"✅ Book already exists: {filename}")
        update_status(title, "ALREADY_EXISTS", dest_path)
        return True
    
    log.info(f"Searching for: {title} by {author}")
    
    # Navigate to Z-Lib home / search page
    page.goto("https://z-lib.gd/", timeout=60000)
    page.wait_for_load_state("networkidle")
    
    # Close any popups if they appear
    try:
        page.click("button:has-text('Cool')", timeout=3000)
    except Exception:
        pass
        
    try:
        page.click("button:has-text('Close')", timeout=3000)
    except Exception:
        pass

    # Type query in search field
    search_query = f"{title} {author}"
    search_input = page.locator("input#searchField, input[name='q'], input[placeholder*='Search']").first
    search_input.fill(search_query)
    
    # Click search button or press Enter
    search_input.press("Enter")
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    
    # Find book links
    # Look for list of results
    book_links = page.locator("a[href*='/book/'], .bookRow a, #booksList a").all()
    if not book_links:
        log.warning(f"❌ No search results found for: {title}")
        update_status(title, "NOT_FOUND", error="No search results")
        return False
    
    # Filter to find the best link (preferring PDF format if visible)
    # Let's inspect the results
    target_link = None
    for link in book_links:
        text = link.inner_text().lower()
        href = link.get_attribute("href")
        # Ensure it's a detail book page, not user profile or tag
        if href and "/book/" in href:
            target_link = link
            break
            
    if not target_link:
        log.warning(f"❌ No valid book detail link found for: {title}")
        update_status(title, "NOT_FOUND", error="No valid detail link")
        return False
        
    log.info(f"Clicking book link: {target_link.inner_text()}")
    target_link.click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    
    # On the book detail page, check if the download option is available
    download_btn = page.locator("a.btn-download, a[href*='/dl/'], a[href*='/download/'], .addDownloadedBook").first
    if not download_btn.is_visible():
        # Check for copyright block message
        block_msg = page.locator("text*='copyright', text*='blocked'").first
        if block_msg.is_visible():
            log.warning(f"❌ Book is blocked due to copyright: {title}")
            update_status(title, "BLOCKED_COPYRIGHT", error="Copyright block")
            return False
        
        log.warning(f"❌ Download button not found for: {title}")
        update_status(title, "DOWNLOAD_BUTTON_NOT_FOUND")
        return False
        
    # Check format or change format to PDF if dropdown exists
    # If the file format is not PDF (e.g. EPUB), see if PDF is available in format dropdown
    try:
        dropdown = page.locator("button.dropdown-toggle, .format-dropdown").first
        if dropdown.is_visible():
            dropdown.click()
            time.sleep(1)
            pdf_option = page.locator("a:has-text('PDF'), button:has-text('PDF')").first
            if pdf_option.is_visible():
                log.info("Switching to PDF format...")
                pdf_option.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
    except Exception as e:
        log.debug(f"Error handling format dropdown: {e}")

    log.info("Starting download...")
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        with page.expect_download(timeout=120000) as download_info:
            download_btn.click()
        download = download_info.value
        download.save_as(dest_path)
        log.info(f"✅ Successfully downloaded: {filename}")
        update_status(title, "DOWNLOADED", dest_path)
        return True
    except Exception as e:
        log.error(f"❌ Error during download of {title}: {e}")
        update_status(title, "DOWNLOAD_FAILED", error=str(e))
        return False

def main():
    creds = load_credentials()
    email = creds["email"]
    password = creds["password"]
    
    log.info("Starting Z-Library downloader script...")
    
    with sync_playwright() as p:
        # Launch browser (non-headless makes it much easier to bypass basic bot detection and see captchas)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Go to singlelogin page or z-lib.gd
        log.info("Navigating to z-lib.gd / login page...")
        page.goto("https://z-lib.gd/", timeout=60000)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        
        # If not logged in, go to login page
        # Check if we need to click Login
        login_btn = page.locator("a:has-text('Sign In'), a:has-text('Login'), a[href*='login']").first
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
        # Fill credentials
        email_input = page.locator("input[name='email'], input[type='email'], input[placeholder*='Email']").first
        pass_input = page.locator("input[name='password'], input[type='password'], input[placeholder*='Password']").first
        
        if email_input.is_visible() and pass_input.is_visible():
            email_input.fill(email)
            pass_input.fill(password)
            
            # Press Enter to submit the form (more robust than clicking which might get intercepted)
            pass_input.press("Enter")
            page.wait_for_load_state("networkidle")
            time.sleep(5)
            log.info("Login submitted via Enter key.")
        else:
            log.info("Login inputs not found, maybe already logged in?")
            
        # Check if we logged in successfully by looking for search page features
        # If there is a welcome popup, close it
        try:
            page.click("button:has-text('Cool')", timeout=5000)
        except Exception:
            pass

        # Loop through books to download
        for book in BOOKS_TO_DOWNLOAD:
            try:
                download_book(page, book)
            except Exception as e:
                log.error(f"Failed to process book {book['title']}: {e}")
            time.sleep(5)
            
        browser.close()
        log.info("Finished downloading books.")

if __name__ == "__main__":
    main()
