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
    "https://hdhub4u.tv/", 
    "https://bolly4u.cl/", # Treat as a hub/landing page in case redirect fails
    "https://www.modlist.in/",
    "https://mmodlist.net/",
    "https://vglist.cv/"
]

# 3. IGNORED DOMAINS
# Domains we usually don't want (ads, fake sites, etc)
IGNORED_DOMAINS = [
    "telegram", "whatsapp", "facebook", "instagram", "twitter", "youtube", "discord",
    "gplinks", "droplink", "adshrink", "katmoviehd" # Add specific spam sites if needed
]

# --- CONFIGURATION END ---

# REDIS SETUP (Same as previous steps)
try:
    import redis
    redis_url = os.environ.get('KV_URL', os.environ.get('UPSTASH_REDIS_REST_URL'))
    if redis_url:
        redis_client = redis.from_url(redis_url)
    else:
        redis_client = None
    print("Redis connected for sync")
except Exception as e:
    redis_client = None
    print(f"Redis connection failed: {e}")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. CHECK CACHE (Unless force refresh)
        if redis_client:
            cached = redis_client.get('app:site_config')
            # Check for ?force=true query param to bypass cache (for Cron jobs)
            if cached and "force=true" not in self.path:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('X-Sync-Source', 'Cache')
                self.end_headers()
                self.wfile.write(cached)
                return

        found_sites = {}
        
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
                # TIMEOUT REDUCED TO 2.5s per site to fit within Vercel's 10s limit
                response = scraper.get(magic_url, timeout=2.5, allow_redirects=True)
                
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

                # TIMEOUT REDUCED TO 2.5s
                response = scraper.get(hub, timeout=2.5)
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
                            if len(clean_name) > 3 and '.' in url:
                                found_sites[url] = clean_name
            except Exception as e:
                print(f"Failed to scrape hub {hub}: {e}")
                continue

        # DEDUPLICATION STEP
        # Group all URLs by their Normalized Name
        grouped_sites = {}
        for url, name in found_sites.items():
            name_upper = name.upper().strip()
            if name_upper not in grouped_sites:
                grouped_sites[name_upper] = []
            grouped_sites[name_upper].append({"url": url, "name": name})

        # Select the BEST URL for each Name
        unique_sites = {}
        for name_upper, candidates in grouped_sites.items():
            # Preference: 
            # 1. HTTPS over HTTP
            # 2. Shorter URL (usually the main domain, not a deep link)
            
            best_candidate = candidates[0]
            for candidate in candidates[1:]:
                cw = best_candidate['url']
                nw = candidate['url']
                
                # Check 1: HTTPS Priority
                if nw.startswith('https') and not cw.startswith('https'):
                    best_candidate = candidate
                    continue
                
                # Check 2: Length Priority (Shorter is usually better/cleaner)
                if len(nw) < len(cw) and nw.startswith('https') == cw.startswith('https'):
                    best_candidate = candidate
            
            unique_sites[best_candidate['url']] = best_candidate['name']

        # Prepare Response
        final_json = json.dumps({"sites": unique_sites})

        # --- 3. SAVE TO CACHE ---
        # Store this result for 12 hours (43200 seconds)
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
