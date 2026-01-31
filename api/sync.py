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

# ... (rest of code) ...

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
