from http.server import BaseHTTPRequestHandler
import json
import cloudscraper
from bs4 import BeautifulSoup

# Fallback defaults if sync fails completely
DEFAULT_SITES = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.gratis/": "VegaMovies"
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        found_sites = DEFAULT_SITES.copy()
        hubs = ["https://vglist.cv/", "https://www.modlist.in/"]
        
        scraper = cloudscraper.create_scraper()
        
        for hub in hubs:
            try:
                response = scraper.get(hub, timeout=4)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        url = a['href'].lower()
                        # Logic from original app.py
                        if any(ext in url for ext in ['.town', '.zip', '.dad', '.loan', '.world', '.fo', '.gratis']):
                            if 't.me' not in url and 'facebook' not in url:
                                if not url.endswith('/'): url += '/'
                                name = url.split('//')[-1].split('.')[0].upper()
                                found_sites[url] = name
            except Exception as e:
                continue

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"sites": found_sites}).encode())
