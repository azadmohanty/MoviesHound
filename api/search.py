from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import cloudscraper
from bs4 import BeautifulSoup
import redis

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_params = parse_qs(urlparse(self.path).query)
        keyword = query_params.get('q', [''])[0]
        site_url = query_params.get('url', [''])[0]
        site_name = query_params.get('name', [''])[0]

        if not keyword or not site_url:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing params"}).encode())
            return

        # --- 1. CACHE CHECK (Redis) ---
        # We generate a unique key based on the site and query
        cache_key = f"search:{site_name}:{keyword.lower().strip()}"
        redis_client = None
        
        try:
            # Support both Vercel KV and standard Upstash integration
            redis_url = os.environ.get("KV_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
            
            if redis_url:
                redis_client = redis.from_url(redis_url)
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    # HIT! Return instantly
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('X-Cache', 'HIT')
                    self.end_headers()
                    self.wfile.write(cached_data)
                    return
        except Exception as e:
            print(f"Redis Error: {e}")

        # --- 2. SCRAPE (Miss) ---
        results = []
        try:
            scraper = cloudscraper.create_scraper()
            # Construct search URL (logic from original app.py)
            search_url = f"{site_url.rstrip('/')}/?s={keyword.replace(' ', '+')}"
            
            response = scraper.get(search_url, timeout=5) # 5s timeout per site (Vercel limit safety)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link_tag in soup.find_all('a', href=True):
                    title = link_tag.get_text().strip()
                    link = link_tag.get('href')
                    
                    if len(title) > 3 and keyword.lower() in title.lower():
                        if link.startswith('http') and "/?s=" not in link:
                            # Basic de-duplication
                            if not any(r['link'] == link for r in results):
                                results.append({"title": title, "link": link, "site": site_name})
        except Exception as e:
            # We fail silently for the fan-out architecture, just return empty
            print(f"Error scraping {site_name}: {e}")
            pass

        response_json = json.dumps({"results": results})

        # --- 3. CACHE SET ---
        # Save for 24 hours (86400 seconds) if we found active results or empty list (to prevent spam)
        try:
            if redis_client:
                redis_client.set(cache_key, response_json, ex=86400)
        except: pass

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('X-Cache', 'MISS')
        self.end_headers()
        self.wfile.write(response_json.encode())
