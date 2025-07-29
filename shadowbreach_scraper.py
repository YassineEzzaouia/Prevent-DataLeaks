import praw
import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime

# --- Leak Keywords ---
LEAK_KEYWORDS = [
    "password", "passwd", "token", "apikey", "api_key",
    "confidential", "internal", "secret", "access_key", 
    "authorization", "credentials", "db_dump", "leak"
]

# --- Save Results to JSON File ---
def save_results_to_file(results):
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    file_path = f"results/leaks_{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved results to {file_path}")

# --- Reddit Scraper ---
def fetch_reddit():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        user_agent="shadowbreach-scraper"
    )
    subs = ["netsec", "hacking"]
    results = []
    for sub in subs:
        for post in reddit.subreddit(sub).new(limit=50):
            combined = (post.title + " " + post.selftext).lower()
            if any(k in combined for k in LEAK_KEYWORDS):
                results.append({
                    "platform": "reddit",
                    "source": post.url,
                    "content": post.title + "\n\n" + post.selftext,
                    "timestamp": datetime.utcfromtimestamp(post.created_utc).isoformat() + "Z"
                })
    return results

# --- GitHub Gists Scraper ---
def fetch_github_gists():
    results = []
    try:
        response = requests.get("https://api.github.com/gists/public", timeout=10)
        if response.status_code != 200:
            print("⚠️ GitHub API error:", response.status_code)
            return results

        for gist in response.json():
            for file_info in gist.get("files", {}).values():
                try:
                    raw = requests.get(file_info["raw_url"], timeout=5).text.lower()
                    if any(k in raw for k in LEAK_KEYWORDS):
                        results.append({
                            "platform": "github",
                            "source": gist["html_url"],
                            "content": raw[:10000],  # Optional truncation
                            "timestamp": gist["created_at"]
                        })
                except:
                    continue
    except Exception as e:
        print("❌ GitHub fetch failed:", e)
    return results

# --- Pastebin Scraper ---
def fetch_pastebin():
    BASE_URL = "https://pastebin.com"
    ARCHIVE_URL = BASE_URL + "/archive"
    results = []

    try:
        soup = BeautifulSoup(requests.get(ARCHIVE_URL, timeout=10).text, "html.parser")
        pastes = soup.select("table.maintable tr td a")[:10]
    except:
        print("⚠️ Failed to load Pastebin archive.")
        return results

    for a in pastes:
        paste_url = BASE_URL + a['href']
        try:
            text = requests.get(paste_url, timeout=5).text.lower()
            if any(k in text for k in LEAK_KEYWORDS):
                results.append({
                    "platform": "pastebin",
                    "source": paste_url,
                    "content": text[:10000],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        except:
            continue
    return results

# --- Main ---
if __name__ == "__main__":
    print("🚀 ShadowBreach Scraper Running...")

    all_results = []

    print("🔎 Scraping Reddit...")
    reddit_results = fetch_reddit()
    print(f"✅ Reddit: {len(reddit_results)} leaks found")
    all_results.extend(reddit_results)

    print("🔎 Scraping GitHub Gists...")
    github_results = fetch_github_gists()
    print(f"✅ GitHub: {len(github_results)} leaks found")
    all_results.extend(github_results)

    print("🔎 Scraping Pastebin...")
    pastebin_results = fetch_pastebin()
    print(f"✅ Pastebin: {len(pastebin_results)} leaks found")
    all_results.extend(pastebin_results)

    if all_results:
        save_results_to_file(all_results)
    else:
        print("⚠️ No leaks detected this run.")

    print("✅ Scraper finished.")
