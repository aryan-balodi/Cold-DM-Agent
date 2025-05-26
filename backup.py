# apify-scraper.py


import os
import json
import csv
import time
import logging
import nltk
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient
from nltk.sentiment import SentimentIntensityAnalyzer

# Download NLTK resources
nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("apify_scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

load_dotenv()
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
SESSIONID = os.getenv("IG_SESSION_ID")  # Add your dummy IG sessionid to .env

# Engagement thresholds
MIN_LIKES = 1000
MIN_COMMENTS = 50

def analyze_sentiment(text):
    """Analyze comment sentiment using VADER"""
    scores = sia.polarity_scores(text)
    return {
        'negative': scores['neg'],
        'neutral': scores['neu'],
        'positive': scores['pos'],
        'compound': scores['compound'],
        'label': 'positive' if scores['compound'] >= 0.05 else 'negative' if scores['compound'] <= -0.05 else 'neutral'
    }

def scrape_high_engagement_posts(username):
    """Scrape AND filter posts in one step"""
    client = ApifyClient(APIFY_API_KEY)
    try:
        logging.info(f"Scraping posts for {username}")
        run = client.actor("apify/instagram-post-scraper").call(
            run_input={"username": [username], "resultsLimit": 5}
        )
        raw_posts = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        filtered = [p for p in raw_posts 
                    if p.get('likesCount', 0) >= MIN_LIKES 
                    and p.get('commentsCount', 0) >= MIN_COMMENTS]
        logging.info(f"Fetched {len(raw_posts)} posts, {len(filtered)} passed engagement filter for {username}")
        return filtered
    except Exception as e:
        logging.error(f"Error scraping posts for {username}: {str(e)}")
        return []

def scrape_high_engagement_reels(username):
    """Scrape AND filter reels in one step"""
    client = ApifyClient(APIFY_API_KEY)
    try:
        logging.info(f"Scraping reels for {username}")
        run = client.actor("apify/instagram-reel-scraper").call(
            run_input={"username": [username], "resultsLimit": 5}
        )
        raw_reels = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        filtered = [r for r in raw_reels 
                    if r.get('likesCount', 0) >= MIN_LIKES 
                    and r.get('commentsCount', 0) >= MIN_COMMENTS]
        logging.info(f"Fetched {len(raw_reels)} reels, {len(filtered)} passed engagement filter for {username}")
        return filtered
    except Exception as e:
        logging.error(f"Error scraping reels for {username}: {str(e)}")
        return []

def scrape_comments_with_login(urls, sessionid, max_comments=70):
    """Scrape comments from posts/reels using a logged-in session."""
    client = ApifyClient(APIFY_API_KEY)
    all_comments = []
    cookies = [{"name": "sessionid", "value": sessionid}]
    for url in urls:
        try:
            logging.info(f"Scraping comments for {url} with login")
            run = client.actor("logical_scrapers/instagram-post-comments-scraper").call(
                run_input={
                    "urls": [url],
                    "maxComments": max_comments,
                    "cookies": cookies
                }
            )
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                comments = item.get("comments", [])
                logging.info(f"Found {len(comments)} comments for {url}")
                for comment in comments:
                    sentiment = analyze_sentiment(comment.get('text', ''))
                    all_comments.append({
                        'post_url': url,
                        'username': comment.get('owner'),
                        'comment': comment.get('text', '')[:200],
                        'timestamp': comment.get('timestamp'),
                        'sentiment': sentiment['label'],
                        'sentiment_score': sentiment['compound']
                    })
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error scraping comments for {url}: {str(e)}")
    logging.info(f"Total comments scraped: {len(all_comments)}")
    return all_comments



def save_to_csv(data, filename, fieldnames=None):
    """Generic CSV saver, collects all unique fieldnames if not provided"""
    if not data:
        logging.warning(f"No data to save for {filename}")
        return
    # Collect all unique fieldnames if not provided
    if fieldnames is None:
        fieldnames_set = set()
        for row in data:
            fieldnames_set.update(row.keys())
        fieldnames = list(fieldnames_set)
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    logging.info(f"✅ Saved {len(data)} items to {filename}")

def main():
    # Load target accounts
    with open("target_accounts.json", "r") as f:
        targets = json.load(f)
    
    crypto_accounts = [acc["username"] for acc in targets["crypto"]]
    logging.info(f"Targeting crypto accounts: {crypto_accounts}")

    # Scrape and save high-engagement content directly
    all_posts = []
    all_reels = []
    
    for username in crypto_accounts:
        posts = scrape_high_engagement_posts(username)
        all_posts.extend(posts)
        reels = scrape_high_engagement_reels(username)
        all_reels.extend(reels)
    
    # Save high-engagement content
    save_to_csv(all_posts, "high_engagement_posts.csv")
    save_to_csv(all_reels, "high_engagement_reels.csv")

    # Scrape and analyze comments with login
    post_urls = [p['url'] for p in all_posts if 'url' in p]
    reel_urls = [r['url'] for r in all_reels if 'url' in r]
    if not SESSIONID:
        logging.error("No IG_SESSIONID found in .env. Cannot scrape comments with login.")
        return
    comments = scrape_comments_with_login(post_urls + reel_urls, SESSIONID)

    # Filter for positive and neutral engagers (potential real users)
    selected_comments = [c for c in comments if c['sentiment'] in ('positive', 'neutral')]
    save_to_csv(selected_comments, "positive_commenters.csv",
               ['post_url', 'username', 'comment', 'sentiment', 'sentiment_score'])

if __name__ == "__main__":
    main()



#(selenium) comment-scraper.py


# import csv
# import random
# import time
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from selenium.common.exceptions import NoSuchElementException, TimeoutException
# from webdriver_manager.chrome import ChromeDriverManager

# # === CONFIGURATION ===

# # Replace these with your actual Webshare proxy credentials and IPs
# PROXY_LIST = [
# "http://198.23.239.134:6540",
#     "http://207.244.217.165:6712",
#     "http://107.172.163.27:6543",
#     "http://161.123.152.115:6360",
#     "http://23.94.138.75:6349",
#     "http://216.10.27.159:6837",
#     "http://136.0.207.84:6661",
#     "http://64.64.118.149:6732",
#     "http://142.147.128.93:6593",
#     "http://154.36.110.199:6853"
# ]

# INSTAGRAM_PASSWORD = "colddmagent@007"

# # List the Instagram post/reel URLs you want to scrape
# POST_URLS = [
#     "https://www.instagram.com/p/POST_ID/",
#     # Add more URLs here
# ]

# # === SCRIPT STARTS HERE ===

# def human_delay(min_seconds=2, max_seconds=5):
#     delay = random.uniform(min_seconds, max_seconds)
#     time.sleep(delay)

# def init_driver(proxy):
#     chrome_options = Options()
#     chrome_options.add_argument("--disable-blink-features=AutomationControlled")
#     chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     chrome_options.add_experimental_option("useAutomationExtension", False)
#     chrome_options.add_argument(f"--proxy-server={proxy}")
#     chrome_options.add_argument("--start-maximized")
#     # Optional: set a mobile user-agent
#     # chrome_options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1")
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
#     driver.set_window_size(random.randint(1200, 1400), random.randint(800, 1000))
#     return driver

# def login_instagram(driver, username, password):
#     driver.get("https://www.instagram.com/accounts/login/")
#     WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "username")))
#     user_input = driver.find_element(By.NAME, "username")
#     pass_input = driver.find_element(By.NAME, "password")
#     user_input.send_keys(username)
#     pass_input.send_keys(password)
#     pass_input.submit()
#     # Wait for login to complete (look for the home icon)
#     WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav[role='navigation']")))
#     human_delay()

# def load_all_comments(driver):
#     last_height = driver.execute_script("return document.body.scrollHeight")
#     while True:
#         try:
#             load_button = WebDriverWait(driver, 5).until(
#                 EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'more comments')]"))
#             )
#             driver.execute_script("arguments[0].click();", load_button)
#             time.sleep(random.uniform(2, 5))  # Random sleep after clicking
#         except (TimeoutException, NoSuchElementException):
#             pass

#         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(random.uniform(2, 5))  # Random sleep after scrolling

#         new_height = driver.execute_script("return document.body.scrollHeight")
#         if new_height == last_height:
#             break
#         last_height = new_height

# def scrape_comments(driver):
#     comments = []
#     # Instagram's HTML changes often; adjust these selectors if needed
#     comment_blocks = driver.find_elements(By.XPATH, "//ul[contains(@class, '_a9z6')]/div/li")
#     for block in comment_blocks:
#         try:
#             username = block.find_element(By.XPATH, ".//h3").text
#             comment_text = block.find_element(By.XPATH, ".//span[not(ancestor::ul[contains(@class, '_a9ym')])]")  # Exclude reply labels
#             comments.append((username, comment_text.text))
#         except NoSuchElementException:
#             continue
#     return comments

# def save_to_csv(data, filename="instagram_comments.csv"):
#     with open(filename, "a", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         if f.tell() == 0:
#             writer.writerow(["Username", "Comment"])
#         writer.writerows(data)

# def scrape_post(url, proxy):
#     driver = init_driver(proxy)
#     try:
#         login_instagram(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
#         driver.get(url)
#         human_delay()
#         # Wait for comments section to appear
#         WebDriverWait(driver, 15).until(
#             EC.presence_of_element_located((By.XPATH, "//ul[contains(@class, '_a9z6')]"))
#         )
#         load_all_comments(driver)
#         comments = scrape_comments(driver)
#         return comments
#     except Exception as e:
#         print(f"Error scraping {url}: {str(e)}")
#         return []
#     finally:
#         driver.quit()

# if __name__ == "__main__":
#     for url in POST_URLS:
#         proxy = random.choice(PROXY_LIST)
#         print(f"Scraping {url} using proxy {proxy}")
#         human_delay(4, 10)  # Longer delay between posts
#         comments = scrape_post(url, proxy)
#         if comments:
#             save_to_csv(comments)
#             print(f"Saved {len(comments)} comments from {url}")
#         else:
#             print(f"No comments found for {url}")
