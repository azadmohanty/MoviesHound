import cloudscraper
from bs4 import BeautifulSoup
import sys

def test_site():
    print("\n--- LINK TESTER TOOL ---")
    url = input("Enter URL to test (e.g. https://vegamovies.kg): ").strip()
    if not url: return

    print(f"\n[1] Testing Connection & Redirects for: {url}...")
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        # TEST 1: REDIRECTS
        response = scraper.get(url, timeout=10, allow_redirects=True)
        print(f"Status Code: {response.status_code}")
        print(f"Final URL:   {response.url}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "No Title"
        print(f"Page Title:  {title}")
        
        if response.status_code != 200:
            print("❌ Site unreachable.")
            return

        # TEST 2: SEARCH
        query = input("\n[2] Enter search term (or press Enter to skip): ").strip()
        if query:
            search_url = f"{response.url.rstrip('/')}/?s={query.replace(' ', '+')}"
            print(f"Searching: {search_url} ...")
            
            search_res = scraper.get(search_url, timeout=10)
            if search_res.status_code == 200:
                search_soup = BeautifulSoup(search_res.text, 'html.parser')
                # Count results (naive count of <a> tags with title in them somewhat)
                results_found = 0
                print("\nResults Found:")
                for a in search_soup.find_all('a', href=True):
                    link_title = a.get_text().strip()
                    link_href = a['href']
                    if len(link_title) > 3 and query.lower() in link_title.lower():
                        if link_href.startswith('http') and "/?s=" not in link_href:
                            print(f"- {link_title} -> {link_href}")
                            results_found += 1
                            if results_found >= 5: # Limit output
                                print("... (more results hidden)")
                                break
                
                if results_found == 0:
                    print("⚠️ No results found (check if site uses ?s= query params)")
            else:
                print(f"❌ Search failed with status {search_res.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    while True:
        test_site()
        if input("\nTest another? (y/n): ").lower() != 'y':
            break
