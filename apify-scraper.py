import os
import json
import csv
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("apify_scraper.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

PROFILE_SCRAPE_LIMIT = 10  # Limit number of profiles to scrape

def scrape_comments_for_urls(urls, output_csv, max_comments=10):
    """Scrape all comments for post/reel URLs and save commenter usernames"""
    client = ApifyClient(APIFY_API_KEY)
    all_comments = []
    
    for i, url in enumerate(urls, 1):
        try:
            logging.info(f"Scraping comments for {url} ({i}/{len(urls)})")
            run = client.actor("apify/instagram-comment-scraper").call(
                run_input={"directUrls": [url], "resultsLimit": max_comments}
            )
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                for comment in item.get("comments", []):
                    all_comments.append({
                        'post_url': url,
                        'commenter_username': comment.get('ownerUsername'),
                        'comment_text': comment.get('text', '')[:200],  # Truncate long comments
                        'timestamp': comment.get('timestamp')
                    })
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error scraping comments for {url}: {str(e)}")
    
    if all_comments:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['post_url', 'commenter_username', 'comment_text', 'timestamp'])
            writer.writeheader()
            writer.writerows(all_comments)
        logging.info(f"✅ Saved {len(all_comments)} comments to {output_csv}")
    else:
        logging.info("No comments found for the provided URLs.")
    return output_csv

def scrape_and_save_instagram_data(hashtags, results_type="posts", results_limit=20):
    """
    Scrape Instagram posts by hashtag using Apify API.
    Args:
        hashtags (list): List of hashtags (without #).
        results_type (str): Type of Instagram content to scrape (only 'posts' supported).
        results_limit (int): Maximum number of results per hashtag.
    Returns:
        str: Path to the generated CSV file.
    """
    client = ApifyClient(APIFY_API_KEY)
    
    if results_type.lower() != "posts":
        logging.warning("Only 'posts' is currently supported. Using 'posts' instead.")
        results_type = "posts"

    run_input = {
        "hashtags": hashtags,
        "resultsType": results_type,
        "resultsLimit": results_limit
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"instagram_{results_type}_{timestamp}.csv"

    try:
        logging.info(f"Starting Apify scrape for {results_type} with hashtags: {hashtags}")
        run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer_initialized = False
            count = 0
            
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                if not writer_initialized:
                    fieldnames = item.keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer_initialized = True
                
                writer.writerow(item)
                count += 1
            
            logging.info(f"✅ Saved {count} {results_type} to {filename}")
            return filename
        
    except Exception as e:
        logging.error(f"❌ Error scraping {results_type}: {str(e)}")
        return None

def get_usernames_from_csv(csv_file):
    """Extract unique usernames from scraped CSV"""
    usernames = set()
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'ownerUsername' in row:
                usernames.add(row['ownerUsername'])
    logging.info(f"Extracted {len(usernames)} unique usernames from {csv_file}")
    return list(usernames)

def scrape_user_profiles(usernames):
    """Scrape follower counts for list of usernames"""
    client = ApifyClient(APIFY_API_KEY)
    user_data = []

    # Limit the number of profiles scraped
    usernames = usernames[:PROFILE_SCRAPE_LIMIT]
    
    for i, username in enumerate(usernames, 1):
        try:
            logging.info(f"Scraping profile for @{username} ({i}/{len(usernames)})")
            run = client.actor("apify/instagram-profile-scraper").call(
                run_input={"usernames": [username]}
            )
            item = next(client.dataset(run["defaultDatasetId"]).iterate_items(), None)
            if item and not item.get('isPrivate', False):
                user_data.append({
                    'username': username,
                    'followers': item.get('followersCount', 0)
                })
            time.sleep(1)  # Rate limiting
        except Exception as e:
            logging.error(f"Error scraping {username}: {str(e)}")
    
    logging.info(f"Scraped {len(user_data)} public user profiles.")
    return user_data

def scrape_targetted_reels(usernames, min_likes=1000, min_comments=20):
    """Scrape reels from targetted users with engagement filters"""
    client = ApifyClient(APIFY_API_KEY)
    all_reels = []
    
    for i, username in enumerate(usernames, 1):
        try:
            logging.info(f"Scraping reels for @{username} ({i}/{len(usernames)})")
            run = client.actor("apify/instagram-reel-scraper").call(
                run_input={"username": [username], "resultsLimit": 20}
            )
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                if (item.get('likesCount', 0) >= min_likes and 
                    item.get('commentsCount', 0) >= min_comments):
                    all_reels.append({
                        'username': username,
                        'url': item.get('url'),
                        'likes': item.get('likesCount'),
                        'comments': item.get('commentsCount'),
                        'caption': item.get('caption', '')[:100]
                    })
            time.sleep(2)  # Rate limiting
        except Exception as e:
            logging.error(f"Error scraping reels for {username}: {str(e)}")
    
    logging.info(f"Scraped {len(all_reels)} high-engagement reels.")
    return all_reels

def main():
    # Load hashtags
    with open("parsed_hashtags.json", "r", encoding="utf-8") as f:
        parsed_hashtags = json.load(f)
    logging.info(f"Using hashtags: {parsed_hashtags}")

    # Step 1: Scrape posts only (Apify doesn't support reels via hashtags)
    posts_csv = scrape_and_save_instagram_data(parsed_hashtags, results_type="posts", results_limit=50)
    if not posts_csv:
        logging.error("No posts CSV generated. Exiting.")
        return

    # Step 1a: Scrape comments for posts
    post_urls = []
    with open(posts_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('url'):
                post_urls.append(row['url'])
    # LIMIT: Only scrape comments for the first N posts
    COMMENT_SCRAPE_LIMIT = 5 # <-- Set your desired limit here
    post_urls = post_urls[:COMMENT_SCRAPE_LIMIT]
    
    if post_urls:
        scrape_comments_for_urls(post_urls, "post_comments.csv")
    else:
        logging.warning("No post URLs found for comment scraping")

    # Step 2: Get usernames from scraped posts
    usernames = get_usernames_from_csv(posts_csv)
    if not usernames:
        logging.error("No usernames found in scraped posts. Exiting.")
        return

    # Step 3: Scrape and filter user profiles
    user_profiles = scrape_user_profiles(usernames)
    target_users = [u for u in user_profiles if u['followers'] >= 100]
    
    # Save targetted users
    with open("targetted_usernames.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'followers'])
        writer.writeheader()
        writer.writerows(target_users)
    logging.info(f"✅ Saved {len(target_users)} target users to targetted_usernames.csv")

    # Step 4: Scrape reels from target users
    if target_users:
        target_usernames = [u['username'] for u in target_users]
        reels_data = scrape_targetted_reels(target_usernames)
        
        with open("reels.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['username', 'url', 'likes', 'comments', 'caption'])
            writer.writeheader()
            writer.writerows(reels_data)
        logging.info(f"✅ Saved {len(reels_data)} high-engagement reels to reels.csv")

        # Step 4a: Scrape comments for reels
        reel_urls = [reel['url'] for reel in reels_data if 'url' in reel]
        if reel_urls:
            scrape_comments_for_urls(reel_urls, "reel_comments.csv")
        else:
            logging.warning("No reel URLs found for comment scraping")

if __name__ == "__main__":
    main()
