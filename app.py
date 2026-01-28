import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import concurrent.futures

# --- APP CONFIG ---
st.set_page_config(page_title="Ultimate Movie Search", page_icon="🚀", layout="wide")
st.title("🚀 Universal Turbo Search")

# 1. PERSISTENT SESSION
if 'scraper' not in st.session_state:
    st.session_state.scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )

DEFAULT_SITES = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.gratis/": "VegaMovies"
}

# --- FUNCTIONS ---

def sync_from_hubs():
    found_sites = DEFAULT_SITES.copy()
    hubs = ["https://vglist.cv/", "https://www.modlist.in/"]
    for hub in hubs:
        try:
            response = st.session_state.scraper.get(hub, timeout=8)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    url = a['href'].lower()
                    if any(ext in url for ext in ['.town', '.zip', '.dad', '.loan', '.world', '.fo', '.gratis']):
                        if 't.me' not in url and 'facebook' not in url:
                            if not url.endswith('/'): url += '/'
                            name = url.split('//')[-1].split('.')[0].upper()
                            found_sites[url] = name
        except:
            continue
    return found_sites

def fetch_site_data(keyword, site_url, site_name):
    """
    PURE DATA FUNCTION: 
    No 'st.' commands here. This prevents the ScriptRunContext error.
    """
    search_url = f"{site_url.rstrip('/')}/?s={keyword.replace(' ', '+')}"
    results = []
    try:
        # We use a fresh scraper instance inside threads for maximum safety
        # or use the session one carefully.
        scraper = cloudscraper.create_scraper() 
        response = scraper.get(search_url, timeout=7)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        for link_tag in soup.find_all('a', href=True):
            title = link_tag.get_text().strip()
            link = link_tag.get('href')
            
            if len(title) > 3 and keyword.lower() in title.lower():
                if link.startswith('http') and "/?s=" not in link:
                    if not any(r['link'] == link for r in results):
                        results.append({"title": title, "link": link, "site": site_name})
        return results
    except:
        return []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ System Status")
    # Using st.cache_data here is fine because it's in the main thread
    @st.cache_data(ttl=3600)
    def cached_sync():
        return sync_from_hubs()
        
    current_active_sites = cached_sync()
    st.success(f"Synced {len(current_active_sites)} sites")
    
    st.markdown("---")
    st.subheader("🛠️ Manual Overrides")
    final_search_list = {}
    for url, name in current_active_sites.items():
        user_url = st.text_input(f"URL: {name}", value=url, key=url)
        final_search_list[user_url] = name

# --- MAIN UI ---
query = st.text_input("Enter Movie Name:", placeholder="e.g. Batman")

if query:
    status_text = st.empty()
    results_container = st.container()
    found_any = False
    
    # 2. THE THREADING BLOCK
    # We do NOT pass Streamlit commands into the threads.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(final_search_list)) as executor:
        status_text.info(f"🔍 Searching {len(final_search_list)} sites in parallel...")
        
        # Submit the tasks
        future_to_url = {
            executor.submit(fetch_site_data, query, url, name): name 
            for url, name in final_search_list.items()
        }

        # 3. THE UI RENDERING (Done only in the Main Thread)
        for future in concurrent.futures.as_completed(future_to_url):
            site_results = future.result() # Get data from thread
            if site_results:
                found_any = True
                with results_container:
                    # All 'st.' calls happen here, safely in the main thread.
                    for item in site_results:
                        st.markdown(f"### [{item['site']}] {item['title']}")
                        st.markdown(f"🔗 [View Movie Page]({item['link']})")
                        st.divider()
    
    status_text.empty()
    if not found_any:
        st.warning("No matches found. Check your keyword or update URLs in the sidebar.")