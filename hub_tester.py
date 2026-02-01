import cloudscraper
from bs4 import BeautifulSoup
import time

# --- CONFIGURATION ---
TEST_HUB_URL = "https://www.modlist.in/"
# Set to None if you only want to test Hubs
TEST_REDIRECT_URL = None 

# MIRROR PRODUCTION WHITELIST
ALLOWED_BRANDS = {
    "moviesmod": "MoviesMod",
    "vegamovies": "VegaMovies",
    "bolly4u": "Bolly4u",
    "moviesleech": "MoviesLeech",
    "rogmovies": "RogMovies",
    "animeflix": "Animeflix",
    "onlykdrama": "OnlyKDrama",
    "mkvdrama": "MKVDrama",
    "bollyflix": "Bollyflix"
}

IGNORED_DOMAINS = ["telegram", "whatsapp", "facebook", "instagram", "twitter", "youtube", "discord"]
# ---------------------

def test_hubs():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    scraper.headers.update({
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    if TEST_HUB_URL:
        print(f"🧪 Testing Hub: {TEST_HUB_URL}")
        try:
            start_time = time.time()
            response = scraper.get(TEST_HUB_URL, timeout=10)
            print(f"📡 Status: {response.status_code} ({time.time() - start_time:.2f}s)")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                hub_domain = TEST_HUB_URL.split('//')[-1].split('/')[0].replace('www.', '')
                
                found_count = 0
                print("\n🔍 Scanning Links...")
                
                for a in soup.find_all('a', href=True):
                    url = a['href'].lower()
                    if not url.startswith('http'): continue
                    if hub_domain in url: continue
                    if any(bad in url for bad in IGNORED_DOMAINS): continue

                    matched_name = None
                    for key, brand_name in ALLOWED_BRANDS.items():
                        if key in url:
                            matched_name = brand_name
                            break
                    
                    if matched_name:
                        print(f"✅ MATCH: {matched_name} -> {url}")
                        found_count += 1
                
                if found_count == 0:
                    print("❌ No whitelisted brands found on this hub.")
            else:
                print("❌ Hub extraction failed (Non-200 Status)")

        except Exception as e:
            print(f"💥 Error: {e}")

    # --- REDIRECT TEST ---
    if TEST_REDIRECT_URL and TEST_REDIRECT_URL != "None":
        print(f"\n🧪 Testing Redirect: {TEST_REDIRECT_URL}")
        try:
            start_time = time.time()
            resp = scraper.get(TEST_REDIRECT_URL, timeout=10, allow_redirects=True)
            print(f"📡 Status: {resp.status_code} ({time.time() - start_time:.2f}s)")
            print(f"↪️  Final URL: {resp.url}")
            
            # DEBUG: Inspect HTML for JS/Meta redirects
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Check Meta Refresh
            meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
            if meta_refresh:
                print(f"found META REFRESH: {meta_refresh}")
                
            # 2. Check Scripts
            print("Scanning scripts for location changes...")
            for script in soup.find_all("script"):
                if script.string:
                    if "location.href" in script.string or "window.location" in script.string:
                        print(f"found SCRIPT REDIRECT: {script.string.strip()[:200]}...")
            
            # 3. Check for obvious links
            print("\nScanning Body Text for clues...")
            print(resp.text[:1000])

            if "bolly4u" in resp.url and resp.status_code == 200:
                print("✅ Bolly4u Redirect SUCCESS")
            else:
                print("⚠️ Redirect didn't land on expected domain pattern.")
                
        except Exception as e:
            print(f"💥 Error: {e}")

if __name__ == "__main__":
    test_hubs()
