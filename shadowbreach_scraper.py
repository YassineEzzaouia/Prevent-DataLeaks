import praw
import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import datetime

# --- Leak Keywords ---
LEAK_KEYWORDS = [
    "password", "passwd", "token", "apikey", "api_key",
    "confidential", "internal", "secret", "access_key", 
    "authorization", "credentials", "db_dump", "leak"
]

# --- SQLite Setup ---
def init_db():
    conn = sqlite3.connect("shadowbreach.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leaks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        source TEXT,
        content TEXT,
        fetched_at TEXT
    )
    ''')
    conn.commit()
    return conn, cursor

def save_to_db(cursor, conn, results):
    for entry in results:
        cursor.execute('''
            INSERT INTO leaks (platform, source, content, fetched_at)
            VALUES (?, ?, ?, ?)
        ''', (
            entry['platform'],
            entry.get('url', entry.get('source', 'unknown')),
            entry['content'][:10000],
            entry['timestamp']
        ))
    conn.commit()

# --- Reddit Scraper ---
def fetch_reddit():
    reddit = praw.Reddit(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
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
                    "url": post.url,
                    "content": post.title + "\n\n" + post.selftext,
                    "timestamp": datetime.datetime.utcfromtimestamp(post.created_utc).isoformat()
                })
    return results

# --- GitHub Gists Scraper ---
def fetch_github_gists():
    results = []
    response = requests.get("https://api.github.com/gists/public")
    if response.status_code != 200:
        return results
    for gist in response.json():
        for file_info in gist.get("files", {}).values():
            try:
                raw = requests.get(file_info["raw_url"], timeout=5).text.lower()
                if any(k in raw for k in LEAK_KEYWORDS):
                    results.append({
                        "platform": "github",
                        "url": gist["html_url"],
                        "content": raw,
                        "timestamp": gist["created_at"]
                    })
            except:
                continue
    return results

# --- Pastebin Scraper ---
def fetch_pastebin():
    BASE_URL = "https://pastebin.com"
    ARCHIVE_URL = BASE_URL + "/archive"
    results = []

    try:
        soup = BeautifulSoup(requests.get(ARCHIVE_URL).text, "html.parser")
        pastes = soup.select("table.maintable tr td a")[:10]
    except:
        return results

    for a in pastes:
        paste_url = BASE_URL + a['href']
        try:
            text = requests.get(paste_url).text.lower()
            if any(k in text for k in LEAK_KEYWORDS):
                results.append({
                    "platform": "pastebin",
                    "url": paste_url,
                    "content": text,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
        except:
            continue
    return results

# --- Main ---
if __name__ == "__main__":
    print("🚀 ShadowBreach Scraper Starting...")
    conn, cursor = init_db()

    all_results = []

    print("🔎 Scraping Reddit...")
    reddit_results = fetch_reddit()
    print(f"✅ Reddit: {len(reddit_results)} results")
    all_results.extend(reddit_results)

    print("🔎 Scraping GitHub Gists...")
    github_results = fetch_github_gists()
    print(f"✅ GitHub: {len(github_results)} results")
    all_results.extend(github_results)

    print("🔎 Scraping Pastebin...")
    pastebin_results = fetch_pastebin()
    print(f"✅ Pastebin: {len(pastebin_results)} results")
    all_results.extend(pastebin_results)

    if all_results:
        print(f"💾 Saving {len(all_results)} items to DB...")
        save_to_db(cursor, conn, all_results)
    else:
        print("⚠️ No matching content found.")

    conn.close()
    print("✅ Done.")
