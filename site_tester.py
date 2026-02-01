import cloudscraper
from bs4 import BeautifulSoup
import time

# --- CONFIGURATION (Edit this to test new sites) ---
TEST_SITE_URL = "https://new3.hdhub4u.fo/"
TEST_SITE_NAME = "Bollyflix"
TEST_KEYWORD = "strange"
# ---------------------------------------------------

def test_site():
    print(f"🧪 Testing {TEST_SITE_NAME} ({TEST_SITE_URL})...")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    # 1. MIRROR PRODUCTION HEADERS
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": TEST_SITE_URL 
    })

    search_url = f"{TEST_SITE_URL.rstrip('/')}/?s={TEST_KEYWORD.replace(' ', '+')}"
    print(f"🔗 Requesting: {search_url}")

    try:
        start_time = time.time()
        response = scraper.get(search_url, timeout=10)
        duration = time.time() - start_time
        
        print(f"📡 Status Code: {response.status_code} ({duration:.2f}s)")

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_title = soup.title.get_text().strip() if soup.title else "No Title"
            print(f"📄 Page Title: {page_title}")

            # --- HYBRID LOGIC (Production Copy) ---
            results = []
            
            # 1. Smart
            for header in soup.find_all(['h2', 'h3', 'h4', 'h1'], class_=lambda c: c and ('title' in c or 'entry' in c or 'post' in c)):
                link_tag = header.find('a', href=True)
                if link_tag:
                    title = link_tag.get_text().strip()
                    link = link_tag.get('href')
                    if TEST_KEYWORD.lower() in title.lower():
                         if not any(r['link'] == link for r in results):
                            results.append({"title": title, "link": link})

            # 2. Greedy Fallback
            if not results:
                print("⚠️ Smart Search empty, trying Greedy...")
                for link_tag in soup.find_all('a', href=True):
                    title = link_tag.get_text().strip()
                    link = link_tag.get('href')
                    if len(title) > 3 and TEST_KEYWORD.lower() in title.lower():
                        if link.startswith('http') and "/?s=" not in link:
                            if not any(r['link'] == link for r in results):
                                results.append({"title": title, "link": link})
            
            # REPORT
            print(f"\n✅ Found {len(results)} results:")
            for r in results:
                print(f" - {r['title']} -> {r['link']}")
            
            if len(results) == 0:
                print("\n❌ 0 Results found (Scraper loaded page but extraction failed).")
                print("Possible fixes: Check keyword, check if site uses diverse HTML classes, or if Cloudflare returned a challenge.")

        elif response.status_code == 403:
            print("\n🚫 BLOCKED (403). Cloudflare or IP Block.")
        else:
            print(f"\n❌ HTTP Error {response.status_code}")

    except Exception as e:
        print(f"\n💥 CRASH: {e}")

if __name__ == "__main__":
    test_site()
