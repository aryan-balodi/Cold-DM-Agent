# Instagram DM CRM Agent

This repository provides an end-to-end automation pipeline for Instagram outreach, lead generation, and engagement. It allows you to scrape posts and comments from Instagram profiles, extract potential leads, and send personalized DMs—all with minimal manual effort.

## Features
- **Profile Management:** Organize target profiles by niche in `profiles.json`.
- **Post Scraping:** Fetch recent posts and metadata for each profile using the Decodo API.
- **Comment Scraping:** Collect comments from each post to identify potential leads.
- **Automated DM Sending:** Send DMs to selected users using the official Instagram API via `instagrapi`.
- **Session Management:** Caches Instagram login sessions for convenience.

## Pipeline Overview
1. **Edit `profiles.json`:** Add your target Instagram profiles, grouped by niche.
2. **Run `post_scraper.py`:** Scrape recent posts (up to 60–72 per profile) to get posts with high engagement metrics, which are customizable. Outputs `*_posts.csv` files.
3. **Run `comment_scraper.py`:** Scrape comments from each post. Outputs `comments_*.csv` files.
4. **Prepare `targets.csv`:** Add usernames and messages for DMing (can be automated or manual).
5. **Run `dm.py`:** Send DMs to all users in `targets.csv`.

## File Descriptions
- `profiles.json` — Stores Instagram profiles grouped by niche.
- `post_scraper.py` — Scrapes posts for each profile and saves to CSV.
- `comment_scraper.py` — Scrapes comments from posts and saves to CSV.
- `dm.py` — Sends DMs to users listed in `targets.csv`.
- `targets.csv` — List of target usernames and messages to send.
- `requirements.txt` — Python dependencies.
- `*_posts.csv` — Output: Posts scraped for each profile.
- `comments_*.csv` — Output: Comments scraped for each post.

## Setup
1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd Cold-DM-Agent
   ```
2. **Create and activate a virtual environment:**
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   pip install instagrapi
   ```
4. **Set up environment variables:**
   - Create a `.env` file with your Decodo API key:
     ```env
     DECODO_AUTH=Basic <your-decodo-api-key>
     ```

## Usage
1. **Scrape Posts:**
   ```sh
   python post_scraper.py
   ```
2. **Scrape Comments:**
   ```sh
   python comment_scraper.py
   ```
3. **Prepare `targets.csv`:**
   - Add usernames and messages (one per line, comma-separated).
4. **Send DMs:**
   ```sh
   python dm.py
   ```

## Notes
- All scripts are interactive and will prompt for required input.
- Make sure your Decodo API key is valid and you comply with Instagram's terms of service.
- For large-scale outreach, always throttle requests to avoid being rate-limited or banned.

## License
MIT License
