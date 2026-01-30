from http.server import BaseHTTPRequestHandler
import json
import cloudscraper
from bs4 import BeautifulSoup

# --- CONFIGURATION START ---

# 1. DIRECT REDIRECTS ("Magic URLs")
# These are single URLs that automatically redirect to the latest working domain.
# Format: { "Magic Link": "Site Name" }
REDIRECT_SOURCES = {
    "https://vegamovies.la": "VegaMovies",
    "https://hdhub4u.tv": "HDHub4u",
    "https://bolly4u.cl": "Bolly4u"
}

# 2. HUB LISTS
# These are index pages that list multiple working proxies.
# logic: We scrape all <a> tags and filter for known patterns.
HUB_SOURCES = [
    "https://vglist.cv/",
    "https://www.modlist.in/",
    "https://mmodlist.net/",
    "https://hdhub4u.catering/"
]

# 3. FILTER PATTERNS (For Hubs)
# We now block known extraneous links instead of whitelisting specific extensions.
# This makes the app future-proof against new domain extensions (e.g. .pizza, .xyz).
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

# --- CONFIGURATION END ---

# Hardcoded fallback defaults (Safety net)
DEFAULT_SITES = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.gratis/": "VegaMovies",
    "https://vegamovies.kg/": "VegaMovies",
    "https://bolly4u.fyi/": "Bolly4u"
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        found_sites = DEFAULT_SITES.copy()
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        
        # STRATEGY 1: RESOLVE REDIRECTS
        for magic_url, name in REDIRECT_SOURCES.items():
            try:
                # We request the 'magic' url. cloudscraper automatically follows redirects.
                # 'allow_redirects=True' is default, but we're explicit.
                response = scraper.get(magic_url, timeout=5, allow_redirects=True)
                
                if response.status_code == 200:
                    final_url = response.url
                    # Basic validation: ensure we didn't land on a parking page
                    page_title = ""
                    try:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        if soup.title: page_title = soup.title.string.lower()
                    except: pass

                    if "domain" not in page_title and "sale" not in page_title:
                        # Ensure trailing slash for consistency
                        if not final_url.endswith('/'): final_url += '/'
                        found_sites[final_url] = name
            except Exception as e:
                print(f"Failed to resolve {magic_url}: {e}")
                continue

        # STRATEGY 2: SCRAPE HUBS
        for hub in HUB_SOURCES:
            try:
                response = scraper.get(hub, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        url = a['href'].lower()
                        
                        # Basic validity check
                        if not url.startswith('http'): continue
                        
                        # Apply Blacklist Logic (Permissive Mode)
                        if not any(bad in url for bad in IGNORED_DOMAINS):
                            if not url.endswith('/'): url += '/'
                            
                            # Heuristic Name Extraction
                            # e.g. https://moviesmod.town/ -> MOVIESMOD
                            try:
                                clean_url = url.replace('www.', '')
                                clean_name = clean_url.split('//')[-1].split('.')[0].upper()
                                # Avoid short garbage names and ensure it looks like a domain
                                if len(clean_name) > 3 and '.' in url:
                                    found_sites[url] = clean_name
                            except:
                                continue
            except Exception as e:
                print(f"Failed to scrape hub {hub}: {e}")
                continue

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"sites": found_sites}).encode())
