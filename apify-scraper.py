import os
import json
import csv
import time
import logging
import random
import pickle
import nltk
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient
from nltk.sentiment import SentimentIntensityAnalyzer
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (NoSuchElementException, TimeoutException)

# === CONFIGURATION ===
nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

load_dotenv()

MIN_LIKES = 1000
MIN_COMMENTS = 50

class InstagramScraper:
    def __init__(self):
        self.driver = None
        self.cookies_file = "instagram_cookies.pkl"
        self.ig_username = os.getenv("IG_USERNAME")
        self.ig_password = os.getenv("IG_PASSWORD")
        self.apify_key = os.getenv("APIFY_API_KEY")

    def human_delay(self, min=2, max=5):
        time.sleep(random.uniform(min, max))

    def init_driver(self):
        """Initialize browser with human-like settings (no proxy)"""
        try:
            options = uc.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            self.driver = uc.Chrome(
                options=options,
                headless=False,
                # version_main=114  # Uncomment and set if needed
            )
            self.driver.set_window_size(
                random.randint(1200, 1400),
                random.randint(800, 1000)
            )
            return self.driver
        except Exception as e:
            logging.error(f"Driver initialization failed: {str(e)}")
            return None

    def save_cookies(self):
        """Save session cookies to file"""
        with open(self.cookies_file, "wb") as f:
            pickle.dump(self.driver.get_cookies(), f)

    def load_cookies(self):
        """Load cookies from previous session"""
        try:
            with open(self.cookies_file, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']
                    self.driver.add_cookie(cookie)
            return True
        except Exception as e:
            logging.warning(f"Cookie load failed: {str(e)}")
            return False

    def is_logged_in(self):
        """Check if logged in status"""
        try:
            self.driver.get("https://www.instagram.com/")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav[role='navigation']"))
            )
            return True
        except Exception:
            return False

    def manual_login(self):
        """Handle login with manual intervention and CAPTCHA solving"""
        self.driver.get("https://www.instagram.com/accounts/login/")
        print("\n=== ACTION REQUIRED ===")
        print("1. Log in manually in the browser window that opened.")
        print("2. Solve any CAPTCHA if it appears.")
        print("3. After you see your Instagram home feed, come back here and press Enter.")
        input(">>> Press Enter ONLY after you are fully logged in... ")
        if self.is_logged_in():
            self.save_cookies()
            print("Login successful. Cookies saved for future runs.")
            return True
        else:
            print("Login failed. Please try again.")
            return False

    def ensure_login(self):
        """Main login handler with cookie persistence and manual fallback"""
        try:
            self.driver.get("https://www.instagram.com/")
            self.human_delay(2, 4)
            if self.load_cookies() and self.is_logged_in():
                logging.info("Logged in via cookies")
                return True
            return self.manual_login()
        except Exception as e:
            logging.error(f"Login flow failed: {str(e)}")
            return False

    def scrape_comments(self, url):
        """Scrape comments from a post/reel"""
        try:
            self.driver.get(url)
            self.human_delay(3, 5)
            # Load all comments
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                try:
                    load_button = WebDriverWait(self.driver, 7).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'more comments')]"))
                    )
                    load_button.click()
                    self.human_delay(1, 2)
                except (TimeoutException, NoSuchElementException):
                    pass
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.human_delay(1, 2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            # Extract comments
            comments = []
            comment_blocks = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//ul/div/li")
            for block in comment_blocks:
                try:
                    username = block.find_element(By.XPATH, ".//h3").text
                    comment_text = block.find_element(By.XPATH, ".//span[contains(@style, '-webkit-line-clamp')]").text
                    sentiment = sia.polarity_scores(comment_text)
                    comments.append({
                        'post_url': url,
                        'username': username,
                        'comment': comment_text[:200],
                        'sentiment': 'positive' if sentiment['compound'] >= 0.05 else 
                                    'negative' if sentiment['compound'] <= -0.05 else 
                                    'neutral',
                        'sentiment_score': sentiment['compound']
                    })
                except NoSuchElementException:
                    continue
            return comments
        except Exception as e:
            logging.error(f"Comment scrape failed: {str(e)}")
            return []

    def scrape_posts_reels(self, username):
        """Apify integration for content discovery"""
        client = ApifyClient(self.apify_key)
        try:
            # Posts
            posts_run = client.actor("apify/instagram-post-scraper").call(
                run_input={"username": [username], "resultsLimit": 5}
            )
            raw_posts = list(client.dataset(posts_run["defaultDatasetId"]).iterate_items())
            filtered_posts = [
                p for p in raw_posts 
                if p.get('likesCount', 0) >= MIN_LIKES 
                and p.get('commentsCount', 0) >= MIN_COMMENTS
            ]
            # Reels
            reels_run = client.actor("apify/instagram-reel-scraper").call(
                run_input={"username": [username], "resultsLimit": 5}
            )
            raw_reels = list(client.dataset(reels_run["defaultDatasetId"]).iterate_items())
            filtered_reels = [
                r for r in raw_reels 
                if r.get('likesCount', 0) >= MIN_LIKES 
                and r.get('commentsCount', 0) >= MIN_COMMENTS
            ]
            return {
                'posts': filtered_posts,
                'reels': filtered_reels
            }
        except Exception as e:
            logging.error(f"Apify error: {str(e)}")
            return {'posts': [], 'reels': []}

    def save_to_csv(self, data, filename):
        """Save data to CSV"""
        if not data:
            logging.warning(f"No data to save for {filename}")
            return
        keys = data[0].keys() if data else []
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        logging.info(f"Saved {len(data)} items to {filename}")

    def run(self):
        """Main execution flow"""
        try:
            if not self.init_driver():
                return
            if not self.ensure_login():
                logging.error("Permanent login failure")
                return
            # Load targets
            with open("target_accounts.json") as f:
                targets = json.load(f)
            for account in targets["crypto"]:
                # Discover content
                content = self.scrape_posts_reels(account["username"])
                self.save_to_csv(content['posts'], "high_engagement_posts.csv")
                self.save_to_csv(content['reels'], "high_engagement_reels.csv")
                # Scrape comments
                all_urls = [p['url'] for p in content['posts'] if 'url' in p]
                all_urls += [r['url'] for r in content['reels'] if 'url' in r]
                all_comments = []
                for url in all_urls:
                    self.human_delay(7, 12)
                    comments = self.scrape_comments(url)
                    all_comments.extend(comments)
                # Save results
                positive_comments = [c for c in all_comments if c['sentiment'] in ('positive', 'neutral')]
                self.save_to_csv(positive_comments, "positive_commenters.csv")
        except Exception as e:
            logging.error(f"Critical error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = InstagramScraper()
    scraper.run()
