import os
import sys
import math
import time
import requests
import csv
import json
import glob
from dotenv import load_dotenv

# Load .env and get your Basic auth header
load_dotenv()
AUTH = os.getenv("DECODO_AUTH")
if not AUTH:
    print("Error: DECODO_AUTH not found in .env")
    sys.exit(1)

API_URL     = "https://scraper-api.decodo.com/v2/scrape"
HEADERS     = {
    "accept":       "application/json",
    "content-type": "application/json",
    "authorization": AUTH
}
MAX_PER_CALL = 12
MAX_TOTAL    = 60

def fetch_posts(profile: str, desired: int) -> list:
    desired   = min(desired, MAX_TOTAL)
    calls     = math.ceil(desired / MAX_PER_CALL)
    cursor    = None
    all_posts = []

    for page in range(1, calls + 1):
        payload = {
            "target": "instagram_graphql_user_posts",
            "query":  profile,
            "count":  MAX_PER_CALL
        }
        if cursor:
            payload["cursor"] = cursor

        resp = requests.post(API_URL, json=payload, headers=HEADERS)
        print(f"[{profile}] HTTP {resp.status_code} (page {page})")
        if resp.status_code != 200:
            print(resp.text)
            break

        js      = resp.json()
        results = js.get("results", [])
        if not results:
            print(f"[{profile}] no results on page {page}")
            break

        # each 'batch' wraps a GraphQL connection
        for batch in results:
            conn  = (batch["content"]
                           ["data"]
                           ["xdt_api__v1__feed__user_timeline_graphql_connection"])
            edges = conn.get("edges", [])
            for edge in edges:
                all_posts.append(edge["node"])

            # pull the real next‐page token from page_info
            page_info = conn.get("page_info", {})
            cursor    = page_info.get("end_cursor")

        # if no more cursor, stop paginating
        if not cursor:
            print(f"[{profile}] reached end of pages after {page} calls")
            break

        time.sleep(1)

    return all_posts[:desired]


def append_to_csv(profile: str, posts: list, min_comments=0):
    filename = os.path.join(OUTPUT_DIR, f"{profile}_posts.csv")
    new_file = not os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["posturl","comment_count","caption"])
        if new_file:
            writer.writeheader()
        for node in posts:
            url   = f"https://www.instagram.com/p/{node.get('code','')}/"
            count = node.get("comment_count") or node \
                        .get("edge_media_to_comment", {}) \
                        .get("count", 0)
            if count < min_comments:
                continue
            # caption may be nested or flat
            cap = node.get("caption", {}).get("text") \
                  or node.get("edge_media_to_caption", {}) \
                         .get("edges", [{}])[0] \
                         .get("node", {}) \
                         .get("text","")
            writer.writerow({
                "posturl":      url,
                "comment_count": count,
                "caption":       cap
            })

def main():
    existing = glob.glob("run*_outputs")
    run_nums = []
    for d in existing:
        try:
            num = int(d.replace("run", "").split("_")[0])
            run_nums.append(num)
        except:
            pass
    next_run   = max(run_nums, default=0) + 1
    output_dir = f"run{next_run}_outputs"
    os.makedirs(output_dir, exist_ok=True)
    print(f"→ Writing all CSVs into folder: {output_dir}/\n")

    global OUTPUT_DIR
    OUTPUT_DIR = output_dir
    
    # 1) Load your niches file
    try:
        with open("profiles.json", "r", encoding="utf-8") as f:
            profiles_json = json.load(f)
    except FileNotFoundError:
        print("Error: profiles.json not found in current directory.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in profiles.json ({e})")
        sys.exit(1)

    # 2) List available niches and prompt
    niches = list(profiles_json.keys())
    print("Available niches:")
    for idx, n in enumerate(niches, start=1):
        print(f"  {idx}. {n}")
    choice = input("Select a niche by name: ").strip()
    if choice not in profiles_json:
        print(f"Error: '{choice}' is not a valid niche. Exiting.")
        return

    # 3) Ask how many profiles to scrape from that niche
    max_profiles = len(profiles_json[choice])
    try:
        m = int(input(f"How many profiles to scrape from '{choice}' (1–{max_profiles})? "))
        if not (1 <= m <= max_profiles):
            raise ValueError
    except ValueError:
        print(f"Invalid number; must be 1 through {max_profiles}. Exiting.")
        return

    selected_profiles = profiles_json[choice][:m]
    print(f"Profiles to be scraped: {selected_profiles}")

    # 4) Ask once for how many posts per profile (1–60)
    try:
        n = int(input(f"How many posts to fetch per profile (1–{MAX_TOTAL})? "))
        if not (1 <= n <= MAX_TOTAL):
            raise ValueError
    except ValueError:
        print(f"Invalid number; must be 1 through {MAX_TOTAL}. Exiting.")
        return
    
    try:
        min_comments = int(input("Minimum comments required per post (0=any)?"))
    except ValueError:
        print("Invalid number; using 0 (any comments).")
        min_comments = 0

    # 5) Loop over the selected profiles
    for profile in selected_profiles:
        print(f"[{profile}] Fetching up to {n} posts…")
        posts = fetch_posts(profile, n)
        if not posts:
            print(f"[{profile}] No posts retrieved.")
            continue

        append_to_csv(profile, posts, min_comments)
        print(f"[{profile}] Saved {len(posts)} posts to '{output_dir}/{profile}_posts.csv'.")

if __name__ == "__main__":
    main()

