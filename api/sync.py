from http.server import BaseHTTPRequestHandler
import json
import cloudscraper
import os
from bs4 import BeautifulSoup

# --- CONFIGURATION START ---

# 1. DIRECT REDIRECTS ("Magic URLs")
# These are single URLs that automatically redirect to the latest working domain.
# Format: { "Magic Link": "Site Name" }
REDIRECT_SOURCES = {
    "https://vegamovies.kg/": "VegaMovies",
    "https://bolly4u.cl": "Bolly4u"
}

# 2. HUB LISTS
# These are "Hubs" or "Lists" that contain links to multiple movie sites.
# We scrape them to find new domains.
HUB_SOURCES = [
    "https://hdhub4u.tv/", # HDHub4u's redirector often lands on an intermediate page, so we scrape it
    "https://www.modlist.in/",
    "https://mmodlist.net/",
    "https://vglist.cv/"
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

# Default sites list (Fallback if scraping fails completely)
DEFAULT_SITES = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.kg/": "VegaMovies",
    "https://bolly4u.fyi/": "Bolly4u"
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Check for ?cron=true parameter to force refresh
        is_cron = "cron=true" in self.path
        
        # --- 1. REDIS CACHE CHECK ---
        # We try to fetch the list from Redis first (unless it's a cron job forcing update)
        redis_client = None
        try:
            redis_url = os.environ.get("KV_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
            if redis_url:
                import redis
                redis_client = redis.from_url(redis_url)
                
                # Only return cached data if this IS NOT a cron job
                if not is_cron:
                    cached_sites = redis_client.get('app:site_config')
                    if cached_sites:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('X-Sync-Source', 'Redis-Cache')
                        self.end_headers()
                        self.wfile.write(cached_sites)
                        return
        except Exception as e:
            print(f"Redis Cache Error: {e}")

        # --- 2. THE HEAVY LIFTING (Scraping) ---
        found_sites = DEFAULT_SITES.copy()
        
        # IMPROVED SCRAPER: Uses headers to look like a real chrome user coming from google
        # This helps bypass Cloudflare on sites like ModList
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        scraper.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/"
        })
        
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
                # Extract the hub's own domain to avoid self-referencing links
                # e.g. "https://modlist.in/" -> "modlist.in"
                hub_domain = hub.split('//')[-1].split('/')[0].replace('www.', '')

                response = scraper.get(hub, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        url = a['href'].lower()
                        
                        # Basic validity check
                        if not url.startswith('http'): continue

                        # FILTER: Don't add the hub's own internal links
                        if hub_domain in url: continue
                        
                        # Apply Blacklist Logic (Permissive Mode)
                        if not any(bad in url for bad in IGNORED_DOMAINS):
                            if not url.endswith('/'): url += '/'
                            
                            # Heuristic Name Extraction
                            # We can force specific names for known brands to fix subdomains (e.g. new3.hdhub4u...)
                            clean_name = ""
                            if "hdhub4u" in url:
                                clean_name = "HDHub4u"
                            elif "vegamovies" in url:
                                clean_name = "VegaMovies"
                            elif "bolly4u" in url:
                                clean_name = "Bolly4u"
                            elif "moviesmod" in url:
                                clean_name = "MoviesMod"
                            else:
                                # Default: Extract from domain
                                try:
                                    clean_url = url.replace('www.', '')
                                    clean_name = clean_url.split('//')[-1].split('.')[0].upper()
                                except: continue

                            # Avoid short garbage names and ensure it looks like a domain
                            if len(clean_name) > 2 and '.' in url:
                                found_sites[url] = clean_name
            except Exception as e:
                print(f"Failed to scrape hub {hub}: {e}")
                continue

        # DEDUPLICATION STEP
        # We might have found the same site via multiple methods (e.g. HTTP vs HTTPS, www vs non-www)
        # We want to keep only UNIQUE site names.
        unique_sites = {}
        seen_names = set()
        
        for url, name in found_sites.items():
            name_upper = name.upper()
            if name_upper not in seen_names:
                unique_sites[url] = name # Keep the first one we found
                seen_names.add(name_upper)
            else:
                # OPTIONAL: If we prefer HTTPS, we could swap it here, but keeping first found is usually fine
                pass

        # Prepare Response
        final_json = json.dumps({"sites": unique_sites})

        # --- 3. SAVE TO CACHE ---
        # Store this result for 12 hours (43200 seconds) since we only get 1 free Cron run per day.
        # This ensures the cache stays valid longer, minimizing user-triggered scrapes.
        try:
            if redis_client:
                redis_client.set('app:site_config', final_json, ex=43200)
        except Exception as e:
            print(f"Failed to save to Redis: {e}")

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('X-Sync-Source', 'Live-Scrape')
        self.end_headers()
        self.wfile.write(final_json.encode())
