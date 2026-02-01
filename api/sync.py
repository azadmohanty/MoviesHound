from http.server import BaseHTTPRequestHandler
import json
import cloudscraper
import os
from bs4 import BeautifulSoup
import redis

# --- FRESH START CONFIGURATION ---

# 1. HUBS TO SCRAPE
HUB_SOURCES = [
    "https://www.modlist.in/",
    "https://mmodlist.net/",
    "https://vglist.cv/",
    "https://bolly4u.cl/" # Landing page
]

# 2. ALLOWED BRANDS (Whitelist)
# We only accept sites that match these keywords
ALLOWED_BRANDS = {
    "moviesmod": "MoviesMod",
    "vegamovies": "VegaMovies",
    "bolly4u": "Bolly4u",
    "moviesleech": "MoviesLeech",
    "rogmovies": "RogMovies",
    "animeflix": "Animeflix",
    "onlykdrama": "OnlyKDrama",
    "mkvdrama": "MKVDrama",
    "bollyflix": "BollyFlix"
}

# 3. IGNORED DOMAINS
IGNORED_DOMAINS = ["telegram", "whatsapp", "facebook", "instagram", "twitter", "youtube", "discord"]

# -------------------------------

try:
    redis_url = os.environ.get('KV_URL', os.environ.get('UPSTASH_REDIS_REST_URL'))
    if redis_url:
        redis_client = redis.from_url(redis_url)
    else:
        redis_client = None
except:
    redis_client = None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Cache Check
        if redis_client:
            cached = redis_client.get('app:site_config')
            if cached and "force=true" not in self.path:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('X-Sync-Source', 'Cache')
                self.end_headers()
                self.wfile.write(cached)
                return

        found_sites = {}
        
        # Scraper Setup
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        scraper.headers.update({
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # --- 1. SPECIAL: Resolve Bolly4u Redirect ---
        try:
            # We follow the redirect to get the final URL
            # TIMEOUT INCREASED: 4.0s
            resp = scraper.get("https://bolly4u.cl", timeout=4.0, allow_redirects=True)
            if resp.status_code == 200:
                final_b4u = resp.url
                if not final_b4u.endswith('/'): final_b4u += '/'
                if "bolly4u" in final_b4u:
                    found_sites[final_b4u] = "Bolly4u"
        except: pass

        # --- 1b. SPECIAL: Resolve BollyFlix (Landing Page Method) ---
        try:
            # 1. Get Landing Page
            landing = scraper.get("https://bollyflix.to", timeout=4.0)
            if landing.status_code == 200:
                soup = BeautifulSoup(landing.text, 'html.parser')
                # 2. Extract Redir Param from Button
                btn = soup.find("a", attrs={"onclick": True})
                if btn and "location.href" in btn['onclick']:
                    # Extract content between single quotes: location.href = '?re-bollyflix'
                    path = btn['onclick'].split("'")[1] 
                    if path.startswith('?'):
                        final_redir = f"https://bollyflix.to{path}"
                        
                        # 3. Follow Redirect
                        resp = scraper.get(final_redir, timeout=4.0, allow_redirects=True)
                        if resp.status_code == 200:
                            clean_url = resp.url
                            if not clean_url.endswith('/'): clean_url += '/'
                            # Verify valid domain
                            if "bollyflix" in clean_url:
                                found_sites[clean_url] = "BollyFlix"
        except: pass

        # --- 2. SCRAPE HUBS ---
        for hub in HUB_SOURCES:
            try:
                # Skip bolly4u here if we processed it above, but safe to re-check
                # TIMEOUT INCREASED: 4.0s
                response = scraper.get(hub, timeout=4.0)
                if response.status_code != 200: continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                hub_domain = hub.split('//')[-1].split('/')[0].replace('www.', '')

                for a in soup.find_all('a', href=True):
                    url = a['href'].lower()
                    if not url.startswith('http'): continue
                    if hub_domain in url: continue # Skip internal links
                    if any(bad in url for bad in IGNORED_DOMAINS): continue

                    # BRAND MATCHING
                    matched_name = None
                    for key, brand_name in ALLOWED_BRANDS.items():
                        if key in url:
                            matched_name = brand_name
                            break
                    
                    if matched_name:
                        if not url.endswith('/'): url += '/'
                        found_sites[url] = matched_name

            except Exception as e:
                print(f"Error scraping {hub}: {e}")
                continue

        # --- DEDUPLICATION ---
        # Group by Name -> List of URLs
        grouped = {}
        for url, name in found_sites.items():
            if name not in grouped: grouped[name] = []
            grouped[name].append(url)
        
        unique_sites = {}
        for name, urls in grouped.items():
            # Pick Best: HTTPS > HTTP, then Shorter > Longer
            best_url = urls[0]
            for u in urls[1:]:
                # Logic: If new is https and current isn't -> Take new
                if u.startswith('https') and not best_url.startswith('https'):
                    best_url = u
                # Logic: If both same protocol, take shorter
                elif u.startswith('https') == best_url.startswith('https'):
                    if len(u) < len(best_url):
                        best_url = u
            
            unique_sites[best_url] = name

        # Response
        final_json = json.dumps({"sites": unique_sites})

        # Cache
        if redis_client:
            try: redis_client.set('app:site_config', final_json, ex=43200)
            except: pass

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('X-Sync-Source', 'Live')
        self.end_headers()
        self.wfile.write(final_json.encode())
