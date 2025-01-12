import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Replace with the path to your Chrome user profile
user_data_dir = "C:/Users/modda/AppData/Local/Google/Chrome/User Data"
profile_name = "Default"  # Adjust if your profile name is different

# Ask the user for search keywords and page range
search_keywords = input("Enter search keywords: ")
page_range_input = input("Enter the page range (e.g., 1 or 2-33): ")

# Parse the page range input
if '-' in page_range_input:
    start_page, end_page = map(int, page_range_input.split('-'))
else:
    start_page = end_page = int(page_range_input)

search_keywords = f"{search_keywords} ,inurl:about"

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
chrome_options.add_argument(f"--profile-directory={profile_name}")
chrome_options.add_argument("--remote-debugging-port=9222")

# Initialize the Chrome WebDriver with the specified options
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Set to store emails and visited URLs to avoid duplicates
emails_found = set()
urls_visited = set()

# List of domains to exclude from scraping
excluded_domains = [
    '.gov', '.edu', '.mil', '.fbi', '.cia', '.nsa', '.uscourts.gov',
    'wikipedia.org', 'yelp.com', 'reddit.com',
    'pinterest.com', 'tiktok.com', 'discord.com', 'github.com', 'quora.com'
]

# Multimedia file extensions to exclude
excluded_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.avi', '.mov']

# Keywords to include county or government URLs
county_government_keywords = ['county', 'gov', 'us', 'org']

# Function to search and collect URLs
def search_and_find_urls(keywords, start_page, end_page):
    all_urls = []
    for page_num in range(start_page, end_page + 1):
        search_url = f"https://www.google.com/search?q={keywords}&start={(page_num - 1) * 10}"
        driver.get(search_url)

        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "search"))
        )

        # Modify the URL to include &num=100
        current_url = driver.current_url
        if "&num=100" not in current_url:
            current_url += "&num=100"
            driver.get(current_url)

        # Find all links on the search results page
        results = driver.find_elements(By.CSS_SELECTOR, "a")
        for result in results:
            try:
                url = result.get_attribute("href")
                
                # Skip unwanted URLs
                if any(domain in url for domain in excluded_domains) or "google.com" in url or url in urls_visited:
                    continue
                
                # Include county government-related URLs
                if any(keyword in url.lower() for keyword in county_government_keywords):
                    print(f"Flagged County/Gov URL: {url}")
                    all_urls.append(url)
                    urls_visited.add(url)
                    continue

                if url and url not in urls_visited:
                    print(f"Found URL: {url}")
                    all_urls.append(url)
                    urls_visited.add(url)
            except Exception as e:
                print(f"Error processing result: {e}")

        # Wait before moving to the next page
        time.sleep(3)
    return all_urls

# Function to process URLs and extract emails
def process_urls(urls_to_visit):
    visited_urls = set()
    try:
        with open("contacts.txt", "a+", encoding="utf-8") as f:
            f.seek(0)
            existing_emails = set(f.read().splitlines())

            for url in urls_to_visit:
                if url not in visited_urls:
                    visited_urls.add(url)
                    try:
                        driver.get(url)
                        time.sleep(3)

                        # Extract emails from the page source
                        page_source = driver.page_source
                        contact_info = re.findall(
                            r'[^a-zA-Z0-9]([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[^a-zA-Z0-9]',
                            page_source
                        )

                        # Process and save emails
                        if contact_info:
                            for email in contact_info:
                                if email not in existing_emails and email not in emails_found:
                                    if not any(ext in email for ext in excluded_extensions):
                                        print(f"Found email on {url}: {email}")
                                        f.write(f"{email}\n")
                                        emails_found.add(email)
                                        existing_emails.add(email)

                        # Check for "about" or "contact" links
                        links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
                        for link in links:
                            href = link.get_attribute("href")
                            if href and ("about" in href.lower() or "contact" in href.lower()):
                                print(f"Found additional page to check: {href}")
                                if href not in visited_urls:
                                    visited_urls.add(href)
                                    driver.get(href)
                                    time.sleep(3)
                                    linked_page_source = driver.page_source
                                    linked_emails = re.findall(
                                        r'[^a-zA-Z0-9]([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[^a-zA-Z0-9]',
                                        linked_page_source
                                    )
                                    for email in linked_emails:
                                        if email not in existing_emails and email not in emails_found:
                                            if not any(ext in email for ext in excluded_extensions):
                                                print(f"Found email on linked page {href}: {email}")
                                                f.write(f"{email}\n")
                                                emails_found.add(email)
                                                existing_emails.add(email)

                    except Exception as e:
                        print(f"Error processing URL {url}: {e}")
                        continue
    except Exception as e:
        print(f"Error handling contacts file: {e}")

# Perform search and extract URLs
urls_to_visit = search_and_find_urls(search_keywords, start_page, end_page)

# Process the URLs and extract emails
process_urls(urls_to_visit)

# Keep the browser open for review
input("Press Enter to close the browser...")

# Quit the browser
driver.quit()
