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
        cache_key = f"search:{site_name}:{keyword.lower().strip()}"
        redis_client = None
        redis_status = "Not Initialized"
        
        try:
            redis_url = os.environ.get("KV_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
            
            if redis_url:
                redis_client = redis.from_url(redis_url)
                # Build connection to verify
                redis_client.ping() 
                redis_status = "Connected"
                
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('X-Cache', 'HIT')
                    self.send_header('X-Redis-Status', 'Connected')
                    self.end_headers()
                    self.wfile.write(cached_data)
                    return
            else:
                redis_status = "Missing URL Env Var"
        except Exception as e:
            print(f"Redis Error: {e}")
            redis_status = f"Error: {str(e)}"

        # --- 2. SCRAPE (Miss) ---
        results = []
        scrape_status = "unknown"
        
        try:
            # IMPROVED SCRAPER: Uses headers to look like a real browser
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
            )
            scraper.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.google.com/"
            })
            
            # Construct search URL (logic from original app.py)
            search_url = f"{site_url.rstrip('/')}/?s={keyword.replace(' ', '+')}"
            
            response = scraper.get(search_url, timeout=10) # Increased timeout slightly for challenge solving
            
            if response.status_code == 200:
                scrape_status = "ok"
                soup = BeautifulSoup(response.text, 'html.parser')
                for link_tag in soup.find_all('a', href=True):
                    title = link_tag.get_text().strip()
                    link = link_tag.get('href')
                    
                    if len(title) > 3 and keyword.lower() in title.lower():
                        if link.startswith('http') and "/?s=" not in link:
                            # Basic de-duplication
                            if not any(r['link'] == link for r in results):
                                results.append({"title": title, "link": link, "site": site_name})
            elif response.status_code in [403, 503]:
                scrape_status = "blocked"
                print(f"Blocked (403/503) scraping {site_name}")
            else:
                scrape_status = f"http_{response.status_code}"
                print(f"HTTP {response.status_code} scraping {site_name}")

        except Exception as e:
            # We fail silently for the fan-out architecture, just return empty
            scrape_status = "error"
            print(f"Error scraping {site_name}: {e}")
            pass

        response_json = json.dumps({
            "results": results, 
            "status": scrape_status,
            "cached": False
        })

        # --- 3. CACHE SET ---
        # Save for 24 hours (86400 seconds) ONLY if status is "ok" and we have results
        # Don't cache errors/blocks nicely, or cache them for shorter time?
        # For now, let's only cache successful hits to avoid poisoning cache with "blocked" states
        try:
            if redis_client and scrape_status == "ok":
                redis_client.set(cache_key, response_json, ex=86400)
        except: pass

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('X-Cache', 'MISS')
        self.send_header('X-Scrape-Status', scrape_status)
        self.send_header('X-Redis-Status', redis_status)
        self.end_headers()
        self.wfile.write(response_json.encode())
