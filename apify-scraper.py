# import os
# import json
# import csv
# import time
# import logging
# import random
# import pickle
# import nltk
# from datetime import datetime
# from dotenv import load_dotenv
# from apify_client import ApifyClient
# from nltk.sentiment import SentimentIntensityAnalyzer
# import undetected_chromedriver as uc
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import (NoSuchElementException, TimeoutException)

# # === CONFIGURATION ===
# nltk.download('vader_lexicon')
# sia = SentimentIntensityAnalyzer()

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.FileHandler("scraper.log", encoding="utf-8"),
#         logging.StreamHandler()
#     ]
# )

# load_dotenv()

# MIN_LIKES = 1000
# MIN_COMMENTS = 50

# class InstagramScraper:
#     def __init__(self):
#         self.driver = None
#         self.cookies_file = "instagram_cookies.pkl"
#         self.ig_username = os.getenv("IG_USERNAME")
#         self.ig_password = os.getenv("IG_PASSWORD")
#         self.apify_key = os.getenv("APIFY_API_KEY")

#     def human_delay(self, min=2, max=5):
#         time.sleep(random.uniform(min, max))

#     def init_driver(self):
#         """Initialize browser with human-like settings (no proxy)"""
#         try:
#             options = uc.ChromeOptions()
#             options.add_argument("--disable-blink-features=AutomationControlled")
#             self.driver = uc.Chrome(
#                 options=options,
#                 headless=False,
#                 # version_main=114  # Uncomment and set if needed
#             )
#             self.driver.set_window_size(
#                 random.randint(1200, 1400),
#                 random.randint(800, 1000)
#             )
#             return self.driver
#         except Exception as e:
#             logging.error(f"Driver initialization failed: {str(e)}")
#             return None

#     def save_cookies(self):
#         """Save session cookies to file"""
#         with open(self.cookies_file, "wb") as f:
#             pickle.dump(self.driver.get_cookies(), f)

#     def load_cookies(self):
#         """Load cookies from previous session"""
#         try:
#             with open(self.cookies_file, "rb") as f:
#                 cookies = pickle.load(f)
#                 for cookie in cookies:
#                     if 'expiry' in cookie:
#                         del cookie['expiry']
#                     self.driver.add_cookie(cookie)
#             return True
#         except Exception as e:
#             logging.warning(f"Cookie load failed: {str(e)}")
#             return False

#     def is_logged_in(self):
#         """Check if logged in status"""
#         try:
#             self.driver.get("https://www.instagram.com/")
#             WebDriverWait(self.driver, 15).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, "nav[role='navigation']"))
#             )
#             return True
#         except Exception:
#             return False

#     def manual_login(self):
#         """Handle login with manual intervention and CAPTCHA solving"""
#         self.driver.get("https://www.instagram.com/accounts/login/")
#         print("\n=== ACTION REQUIRED ===")
#         print("1. Log in manually in the browser window that opened.")
#         print("2. Solve any CAPTCHA if it appears.")
#         print("3. After you see your Instagram home feed, come back here and press Enter.")
#         input(">>> Press Enter ONLY after you are fully logged in... ")
#         if self.is_logged_in():
#             self.save_cookies()
#             print("Login successful. Cookies saved for future runs.")
#             return True
#         else:
#             print("Login failed. Please try again.")
#             return False

#     def ensure_login(self):
#         """Main login handler with cookie persistence and manual fallback"""
#         try:
#             self.driver.get("https://www.instagram.com/")
#             self.human_delay(2, 4)
#             if self.load_cookies() and self.is_logged_in():
#                 logging.info("Logged in via cookies")
#                 return True
#             return self.manual_login()
#         except Exception as e:
#             logging.error(f"Login flow failed: {str(e)}")
#             return False

#     def scrape_comments(self, url):
#         """Scrape comments from a post/reel"""
#         try:
#             self.driver.get(url)
#             self.human_delay(3, 5)
#             # Load all comments
#             last_height = self.driver.execute_script("return document.body.scrollHeight")
#             while True:
#                 try:
#                     load_button = WebDriverWait(self.driver, 7).until(
#                         EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'more comments')]"))
#                     )
#                     load_button.click()
#                     self.human_delay(1, 2)
#                 except (TimeoutException, NoSuchElementException):
#                     pass
#                 self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#                 self.human_delay(1, 2)
#                 new_height = self.driver.execute_script("return document.body.scrollHeight")
#                 if new_height == last_height:
#                     break
#                 last_height = new_height
#             # Extract comments
#             comments = []
#             comment_blocks = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//ul/div/li")
#             for block in comment_blocks:
#                 try:
#                     username = block.find_element(By.XPATH, ".//h3").text
#                     comment_text = block.find_element(By.XPATH, ".//span[contains(@style, '-webkit-line-clamp')]").text
#                     sentiment = sia.polarity_scores(comment_text)
#                     comments.append({
#                         'post_url': url,
#                         'username': username,
#                         'comment': comment_text[:200],
#                         'sentiment': 'positive' if sentiment['compound'] >= 0.05 else 
#                                     'negative' if sentiment['compound'] <= -0.05 else 
#                                     'neutral',
#                         'sentiment_score': sentiment['compound']
#                     })
#                 except NoSuchElementException:
#                     continue
#             return comments
#         except Exception as e:
#             logging.error(f"Comment scrape failed: {str(e)}")
#             return []

#     def scrape_posts_reels(self, username):
#         """Apify integration for content discovery"""
#         client = ApifyClient(self.apify_key)
#         try:
#             # Posts
#             posts_run = client.actor("apify/instagram-post-scraper").call(
#                 run_input={"username": [username], "resultsLimit": 5}
#             )
#             raw_posts = list(client.dataset(posts_run["defaultDatasetId"]).iterate_items())
#             filtered_posts = [
#                 p for p in raw_posts 
#                 if p.get('likesCount', 0) >= MIN_LIKES 
#                 and p.get('commentsCount', 0) >= MIN_COMMENTS
#             ]
#             # Reels
#             reels_run = client.actor("apify/instagram-reel-scraper").call(
#                 run_input={"username": [username], "resultsLimit": 5}
#             )
#             raw_reels = list(client.dataset(reels_run["defaultDatasetId"]).iterate_items())
#             filtered_reels = [
#                 r for r in raw_reels 
#                 if r.get('likesCount', 0) >= MIN_LIKES 
#                 and r.get('commentsCount', 0) >= MIN_COMMENTS
#             ]
#             return {
#                 'posts': filtered_posts,
#                 'reels': filtered_reels
#             }
#         except Exception as e:
#             logging.error(f"Apify error: {str(e)}")
#             return {'posts': [], 'reels': []}

#     def save_to_csv(self, data, filename):
#         """Save data to CSV"""
#         if not data:
#             logging.warning(f"No data to save for {filename}")
#             return
#         keys = data[0].keys() if data else []
#         with open(filename, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.DictWriter(f, fieldnames=keys)
#             writer.writeheader()
#             writer.writerows(data)
#         logging.info(f"Saved {len(data)} items to {filename}")

#     def run(self):
#         """Main execution flow"""
#         try:
#             if not self.init_driver():
#                 return
#             if not self.ensure_login():
#                 logging.error("Permanent login failure")
#                 return
#             # Load targets
#             with open("target_accounts.json") as f:
#                 targets = json.load(f)
#             for account in targets["crypto"]:
#                 # Discover content
#                 content = self.scrape_posts_reels(account["username"])
#                 self.save_to_csv(content['posts'], "high_engagement_posts.csv")
#                 self.save_to_csv(content['reels'], "high_engagement_reels.csv")
#                 # Scrape comments
#                 all_urls = [p['url'] for p in content['posts'] if 'url' in p]
#                 all_urls += [r['url'] for r in content['reels'] if 'url' in r]
#                 all_comments = []
#                 for url in all_urls:
#                     self.human_delay(7, 12)
#                     comments = self.scrape_comments(url)
#                     all_comments.extend(comments)
#                 # Save results
#                 positive_comments = [c for c in all_comments if c['sentiment'] in ('positive', 'neutral')]
#                 self.save_to_csv(positive_comments, "positive_commenters.csv")
#         except Exception as e:
#             logging.error(f"Critical error: {str(e)}")
#         finally:
#             if self.driver:
#                 self.driver.quit()

# if __name__ == "__main__":
#     scraper = InstagramScraper()
#     scraper.run()

import os
import json
import csv
import time
import requests
import logging
from dotenv import load_dotenv
from apify_client import ApifyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Apify configuration
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
PHANTOMBUSTER_API_KEY = os.getenv("PHANTOMBUSTER_API_KEY")
PHANTOMBUSTER_PHANTOM_ID = os.getenv("PHANTOMBUSTER_PHANTOM_ID")  # Your comment scraper phantom ID

# Engagement thresholds
MIN_LIKES = 1000
MIN_COMMENTS = 50

# Limit how many URLs to send to PhantomBuster in a run
MAX_URLS_TO_SCRAPE = 1  # Change this to your desired limit

def scrape_high_engagement_posts(username):
    """Apify post scraper"""
    client = ApifyClient(APIFY_API_KEY)
    try:
        run = client.actor("apify/instagram-post-scraper").call(
            run_input={"username": [username], "resultsLimit": 5}
        )
        raw_posts = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return [
            p for p in raw_posts
            if p.get('likesCount', 0) >= MIN_LIKES
            and p.get('commentsCount', 0) >= MIN_COMMENTS
        ]
    except Exception as e:
        logging.error(f"Apify post error: {str(e)}")
        return []

def scrape_high_engagement_reels(username):
    """Apify reel scraper"""
    client = ApifyClient(APIFY_API_KEY)
    try:
        run = client.actor("apify/instagram-reel-scraper").call(
            run_input={"username": [username], "resultsLimit": 5}
        )
        raw_reels = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return [
            r for r in raw_reels
            if r.get('likesCount', 0) >= MIN_LIKES
            and r.get('commentsCount', 0) >= MIN_COMMENTS
        ]
    except Exception as e:
        logging.error(f"Apify reel error: {str(e)}")
        return []

def save_to_csv(data, filename):
    """Generic CSV saver that handles varying fields dynamically"""
    if not data:
        logging.warning(f"No data to save for {filename}")
        return
    # Collect all unique keys from all dicts
    fieldnames_set = set()
    for row in data:
        fieldnames_set.update(row.keys())
    fieldnames = list(fieldnames_set)
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logging.info(f"Saved {len(data)} items to {filename}")

def upload_to_phantombuster(csv_path):
    """Upload CSV to PhantomBuster storage with better error handling"""
    try:
        with open(csv_path, "rb") as f:
            response = requests.post(
                "https://api.phantombuster.com/api/v2/containers/upload",
                headers={"X-Phantombuster-Key-1": PHANTOMBUSTER_API_KEY},
                files={"file": f}
            )
            response.raise_for_status()  # Check for HTTP errors
            response_data = response.json()
            if "url" not in response_data:
                logging.error(f"PhantomBuster upload response missing 'url': {response_data}")
                return None
            return response_data["url"]
    except Exception as e:
        logging.error(f"CSV upload failed: {str(e)}")
        logging.error(f"Response content: {response.content if 'response' in locals() else ''}")
        return None


def launch_phantombuster_scraper(csv_url):
    """Launch PhantomBuster comment scraper"""
    try:
        response = requests.post(
            "https://api.phantombuster.com/api/v2/agents/launch",
            headers={"X-Phantombuster-Key-1": PHANTOMBUSTER_API_KEY},
            json={
                "id": PHANTOMBUSTER_PHANTOM_ID,
                "arguments": {
                    "spreadsheetUrl": csv_url,
                    "csvColumn": "url"  # Must match your CSV column name
                }
            }
        )
        return response.json().get("containerId")
    except Exception as e:
        logging.error(f"Phantom launch failed: {str(e)}")
        return None

def wait_for_completion(container_id, timeout=3600):
    """Wait for PhantomBuster job completion"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"https://api.phantombuster.com/api/v2/containers/fetch?id={container_id}",
                headers={"X-Phantombuster-Key-1": PHANTOMBUSTER_API_KEY}
            )
            status = response.json().get("status")
            
            if status == "error":
                logging.error("PhantomBuster job failed")
                return None
            if status == "done":
                return response.json().get("outputUrl")
            
            logging.info(f"Phantom status: {status}")
            time.sleep(30)
        except Exception as e:
            logging.error(f"Status check failed: {str(e)}")
            return None
    logging.error("PhantomBuster job timed out")
    return None

def main():
    # Load target accounts
    with open("target_accounts.json") as f:
        targets = json.load(f)
    
    all_posts = []
    all_reels = []
    
    # Scrape posts/reels using Apify
    for account in targets["crypto"]:
        all_posts.extend(scrape_high_engagement_posts(account["username"]))
        all_reels.extend(scrape_high_engagement_reels(account["username"]))
    
    # Save discovered content
    save_to_csv(all_posts, "high_engagement_posts.csv")
    save_to_csv(all_reels, "high_engagement_reels.csv")
    
    # Prepare PhantomBuster input: save ALL URLs
    all_urls = [p["url"] for p in all_posts if "url" in p]
    all_urls += [r["url"] for r in all_reels if "url" in r]
    with open("phantom_input.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        writer.writerows([[url] for url in all_urls])

    logging.info(f"Total URLs in phantom_input.csv: {len(all_urls)}")

    # Select only the top MAX_URLS_TO_SCRAPE URLs for this run
    selected_urls = []
    with open("phantom_input.csv", "r", encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if "url" not in reader.fieldnames:
            logging.error(f"CSV header does not contain 'url'. Found: {reader.fieldnames}")
            return
        for i, row in enumerate(reader):
            url_val = row.get("url")
            if i >= MAX_URLS_TO_SCRAPE:
                break
            if not url_val or not url_val.strip():
                logging.warning(f"Skipping row {i} - missing or empty URL")
                continue  # skip blank or missing url rows
            selected_urls.append(url_val.strip())

    logging.info(f"Selected {len(selected_urls)} URLs for PhantomBuster run.")

    # Write only the 'url' column to the subset CSV
    with open("phantom_input_subset.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        for url in selected_urls:
            writer.writerow([url])

    logging.info("phantom_input_subset.csv contents:")
    with open("phantom_input_subset.csv", "r", encoding='utf-8') as f:
        for line in f:
            logging.info(line.strip())

    # Upload and launch PhantomBuster with ONLY the subset
    csv_url = upload_to_phantombuster("phantom_input_subset.csv")
    if not csv_url:
        return
    
    container_id = launch_phantombuster_scraper(csv_url)
    if not container_id:
        return
    
    # Wait for results
    output_url = wait_for_completion(container_id)
    if not output_url:
        return
    
    # Download and save comments
    try:
        response = requests.get(output_url)
        with open("instagram_comments.csv", "wb") as f:
            f.write(response.content)
        logging.info("Successfully downloaded comments CSV")
    except Exception as e:
        logging.error(f"Download failed: {str(e)}")

if __name__ == "__main__":
    main()
