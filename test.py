import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import concurrent.futures
from streamlit.runtime.scriptrunner import add_script_run_context
import threading

# --- APP CONFIG ---
st.set_page_config(page_title="Ultimate Movie Search 2026", page_icon="🚀", layout="wide")
st.title("🚀 Ultimate Multi-Site Search")

# 1. PERSISTENT SESSION (Network Optimization)
if 'scraper' not in st.session_state:
    st.session_state.scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )

# 2. DEFAULT FALLBACKS
DEFAULT_SITES = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.gratis/": "VegaMovies",
    "https://uhdmovies.loan/": "UHDMovies"
}

# --- FUNCTIONS ---

@st.cache_data(ttl=3600)
def sync_from_hubs():
    """Crawls hubs for new links; falls back to DEFAULT_SITES on failure."""
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
    """Worker function for threads with ScriptRunContext fixed."""
    # This ensures Streamlit features work inside the thread
    add_script_run_context()
    
    search_url = f"{site_url.rstrip('/')}/?s={keyword.replace(' ', '+')}"
    results = []
    
    try:
        # User-Agent mimicry to bypass Cloudflare
        st.session_state.scraper.headers.update({"Referer": site_url})
        response = st.session_state.scraper.get(search_url, timeout=7)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Greedy search for any link containing the movie name
        for link_tag in soup.find_all('a', href=True):
            title = link_tag.get_text().strip()
            link = link_tag.get('href')
            
            # Filter: Title must contain keyword and link must be a direct page
            if len(title) > 3 and keyword.lower() in title.lower():
                if link.startswith('http') and "/?s=" not in link:
                    if not any(r['link'] == link for r in results):
                        results.append({"title": title, "link": link, "site": site_name})
        return results
    except:
        return []

# --- SIDEBAR & LINK DISCOVERY ---
with st.sidebar:
    st.header("⚙️ System Status")
    with st.spinner("Syncing latest domains..."):
        current_active_sites = sync_from_hubs()
    
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
    
    # THREADED SEARCH EXECUTION
    # Using max_workers to ensure all sites are searched simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(final_search_list)) as executor:
        status_text.info(f"🔍 Searching {len(final_search_list)} sites in parallel...")
        
        # Submit all tasks
        futures = [executor.submit(fetch_site_data, query, url, name) 
                   for url, name in final_search_list.items()]

        # Early Yielding: Process results as they arrive
        for future in concurrent.futures.as_completed(futures):
            site_results = future.result()
            if site_results:
                found_any = True
                with results_container:
                    for item in site_results:
                        st.markdown(f"### [{item['site']}] {item['title']}")
                        st.markdown(f"🔗 [View Movie Page]({item['link']})")
                        st.divider()
    
    status_text.empty()
    if not found_any:
        st.warning("No matches found. Check your keyword or update URLs in the sidebar.")