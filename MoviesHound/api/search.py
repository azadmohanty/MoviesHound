from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import cloudscraper
from bs4 import BeautifulSoup

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

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"results": results}).encode())
