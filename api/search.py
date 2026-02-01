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

        # 1. CACHE CHECK
        cache_key = f"search:{site_name}:{keyword.lower().strip()}"
        redis_client = None
        try:
            redis_url = os.environ.get("KV_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
            if redis_url:
                redis_client = redis.from_url(redis_url)
                cached = redis_client.get(cache_key)
                if cached:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('X-Cache', 'HIT')
                    self.end_headers()
                    self.wfile.write(cached)
                    return
        except: pass

        # 2. SCRAPE
        results = []
        scrape_status = "unknown"
        
        try:
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
            )
            # CRITICAL: Use Referer = site_url (Matches test.py success)
            scraper.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": site_url 
            })
            
            search_url = f"{site_url.rstrip('/')}/?s={keyword.replace(' ', '+')}"
            response = scraper.get(search_url, timeout=10)
            
            if response.status_code == 200:
                scrape_status = "ok"
                soup = BeautifulSoup(response.text, 'html.parser')

                # DEBUG TITLE (Simple)
                page_title = soup.title.get_text().strip()[:20] if soup.title else "No Title"

                # STRATEGY: Hybrid (Smart Header -> Fallback Greedy)
                found_smart = False
                
                # 1. Smart Headers
                for header in soup.find_all(['h2', 'h3', 'h4', 'h1'], class_=lambda c: c and ('title' in c or 'entry' in c or 'post' in c)):
                    link_tag = header.find('a', href=True)
                    if link_tag:
                        title = link_tag.get_text().strip()
                        link = link_tag.get('href')
                        if keyword.lower() in title.lower():
                             if not any(r['link'] == link for r in results):
                                results.append({"title": title, "link": link, "site": site_name})
                                found_smart = True

                # 2. Greedy Fallback (If smart found nothing)
                if not found_smart:
                    for link_tag in soup.find_all('a', href=True):
                        title = link_tag.get_text().strip()
                        link = link_tag.get('href')
                        
                        # LOGIC MATCHING TEST.PY
                        if len(title) > 3 and keyword.lower() in title.lower():
                            if link.startswith('http') and "/?s=" not in link:
                                if not any(r['link'] == link for r in results):
                                    results.append({"title": title, "link": link, "site": site_name})
                
                if not results:
                    scrape_status = f"ok: {page_title}"

            elif response.status_code in [403, 503]:
                scrape_status = "blocked"
            else:
                scrape_status = f"http_{response.status_code}"

        except Exception as e:
            scrape_status = "error"
            print(f"Error scraping {site_name}: {e}")

        response_json = json.dumps({
            "results": results, 
            "status": scrape_status
        })

        # 3. CACHE SAVE
        try:
            if redis_client and scrape_status == "ok" and results:
                redis_client.set(cache_key, response_json, ex=86400)
        except: pass

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('X-Scrape-Status', scrape_status)
        self.end_headers()
        self.wfile.write(response_json.encode())
