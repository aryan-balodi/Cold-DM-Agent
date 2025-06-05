import os
import sys
import math
import time
import requests
import csv
from pathlib import Path
import json
from dotenv import load_dotenv

# ─── Configuration & Auth ─────────────────────────────────────────────────
load_dotenv()  # expects DECODO_AUTH=Basic … in .env
AUTH = os.getenv("DECODO_AUTH")
if not AUTH:
    print("Error: DECODO_AUTH not found in .env"); sys.exit(1)

API_URL           = "https://scraper-api.decodo.com/v2/scrape"
HEADERS           = {
    "accept":       "application/json",
    "content-type": "application/json",
    "authorization": AUTH
}
COMMENTS_PER_CALL = 10   # Decodo returns 10 comments per call
MAX_RETRIES       = 5
BASE_BACKOFF      = 2    # seconds initial backoff

# ─── Rate‐Limit Safe Request ───────────────────────────────────────────────
def safe_request(payload):
    """
    POST to API_URL with payload & HEADERS.
    - Retries on 429 up to MAX_RETRIES times (exponential back-off).
    - On any other non-200, logs payload and response body.
    """
    backoff = BASE_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(API_URL, json=payload, headers=HEADERS)

        if resp.status_code == 429:
            print(f"⚠️ Rate limited (429). Backing off {backoff}s (try {attempt}/{MAX_RETRIES})")
            time.sleep(backoff)
            backoff *= 2
            continue

        if not resp.ok:
            print("❌ HTTP", resp.status_code, "Error when fetching comments")
            print("Payload was:\n", json.dumps(payload, indent=2))
            print("Response body:\n", resp.text)
            resp.raise_for_status()

        return resp

    raise RuntimeError("Exceeded max retries due to rate limiting")


# ─── Fetch All Comments (with max_comments) ────────────────────────────────
def fetch_all_comments(shortcode: str, max_comments: int) -> list:
    comments = []
    payload = {
        "target": "instagram_graphql_post",
        "url":    f"https://www.instagram.com/p/{shortcode}/",
        "count":  COMMENTS_PER_CALL
    }

    # 1) Initial request
    resp = safe_request(payload)
    js   = resp.json()

    batch = js["results"][0]  # Decodo returns a single batch
    media = batch["content"]["data"]["xdt_shortcode_media"]  # correct key here
    block = media["edge_media_to_parent_comment"]

    total_comments = block.get("count", 0)
    edges          = block.get("edges", [])
    page_info      = block.get("page_info", {})

    # 2) Collect first page
    for edge in edges:
        if len(comments) >= max_comments:
            break
        node = edge["node"]
        comments.append({
            "username": node["owner"]["username"],
            "comment":  node["text"]
        })
    time.sleep(1)

    # 3) Calculate pages needed (cap at max_comments)
    pages_needed = math.ceil(min(total_comments, max_comments) / COMMENTS_PER_CALL)
    cursor       = page_info.get("end_cursor")

    # 4) Fetch remaining pages
    for _ in range(2, pages_needed + 1):
        if not cursor or len(comments) >= max_comments:
            break
        payload["cursor"] = cursor
        resp = safe_request(payload)
        js   = resp.json()

        # import pprint, sys
        # pprint.pprint(js)
        # sys.exit(0)

        batch = js["results"][0]  # Decodo returns a single batch
        media = batch["content"]["data"]["xdt_shortcode_media"]
        block = media["edge_media_to_parent_comment"]

        for edge in block.get("edges", []):
            if len(comments) >= max_comments:
                break
            node = edge["node"]
            comments.append({
                "username": node["owner"]["username"],
                "comment":  node["text"]
            })

        cursor = block.get("page_info", {}).get("end_cursor")
        print(f"  → fetched page, total collected: {len(comments)}")
        time.sleep(1)

    return comments


# ─── Main Routine ────────────────────────────────────────────────────────
def main():
    # 1) Ask for the posts-CSV path
    path_str = input("Path to posts CSV (with 'posturl' column): ").strip()
    posts_file = Path(path_str)
    if not posts_file.exists():
        print(f"Error: {posts_file} not found."); sys.exit(1)

    # 2) Ask how many comments per post
    try:
        max_comments = int(input("How many comments to fetch per post (1–200)? ").strip())
        if not (1 <= max_comments <= 200):
            raise ValueError
    except ValueError:
        print("Invalid number; must be 1 through 200."); sys.exit(1)

    out_dir = posts_file.parent
    print(f"\nReading posts from: {posts_file}")
    print(f"Writing comment files to: {out_dir}\n")

    # 3) Process each post in the CSV
    with posts_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            posturl = row.get("posturl", "").rstrip("/")
            shortcode = posturl.split("/")[-1]
            print(f"[Post #{idx}] shortcode={shortcode} → fetching up to {max_comments} comments…")

            comments = fetch_all_comments(shortcode, max_comments)
            print(f"[Post #{idx}] Total comments fetched: {len(comments)}")

            # 4) Write to CSV
            out_csv = out_dir / f"comments_{idx}.csv"
            with out_csv.open("w", newline="", encoding="utf-8") as out:
                writer = csv.DictWriter(out, fieldnames=["username","comment"])
                writer.writeheader()
                for c in comments:
                    writer.writerow(c)
            print(f"[Post #{idx}] Saved comments to: {out_csv}\n")

if __name__ == "__main__":
    main()
