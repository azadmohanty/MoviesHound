import cloudscraper
from bs4 import BeautifulSoup

# Same blacklist as api/sync.py
IGNORED_DOMAINS = [
    't.me', 'telegram.me',               # Telegram
    'facebook.com', 'fb.com',            # Facebook
    'whatsapp.com', 'wa.me',             # WhatsApp
    'instagram.com',                     # Instagram
    'twitter.com', 'x.com',              # Twitter
    'discord.gg', 'discord.com',         # Discord
    'youtube.com', 'youtu.be',           # YouTube
    'pinterest.com',
    'reddit.com',
    'linkedin.com',
    'google.com',
    'bing.com'
]

def test_hub():
    print("\n--- HUB TESTER TOOL ---")
    hub_url = input("Enter Hub URL to scrape (e.g. https://vglist.cv/): ").strip()
    if not hub_url: return

    print(f"\n[1] Scraping Hub: {hub_url}...")
    
    # IMPROVED SCRAPER: Uses headers to look like a real chrome user coming from google
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    
    try:
        # Extract the hub's own domain to avoid self-referencing links
        hub_domain = hub_url.split('//')[-1].split('/')[0].replace('www.', '')
        
        response = scraper.get(hub_url, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Hub unreachable.")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        print(f"Found {len(links)} total links. Filtering...")
        
        found_sites = {}
        
        for a in links:
            url = a['href'].lower()
            
            # Basic validity check
            if not url.startswith('http'): continue

            # FILTER: Don't add the hub's own internal links
            if hub_domain in url: 
                # print(f"  [Skipped - Internal] {url}")
                continue
            
            # Apply Blacklist Logic
            is_ignored = False
            for bad in IGNORED_DOMAINS:
                if bad in url:
                    is_ignored = True
                    break
            
            if is_ignored:
                # print(f"  [Skipped - Blacklist] {url}")
                continue
                
            if not url.endswith('/'): url += '/'
            
            # Heuristic Name Extraction
            try:
                clean_url = url.replace('www.', '')
                clean_name = clean_url.split('//')[-1].split('.')[0].upper()
                # Avoid short garbage names and ensure it looks like a domain
                if len(clean_name) > 3 and '.' in url:
                    found_sites[url] = clean_name
            except:
                continue
        
        print(f"\n✅ Found {len(found_sites)} Valid Movie Sites:")
        for url, name in found_sites.items():
            print(f"   - {name}: {url}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    while True:
        test_hub()
        if input("\nTest another? (y/n): ").lower() != 'y':
            break
