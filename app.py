import streamlit as st
import requests
from bs4 import BeautifulSoup

# --- APP CONFIG ---
st.set_page_config(page_title="Movie Searcher", page_icon="🎬")
st.title("🎬 Multi-Site Movie Search")
st.markdown("Searching: `moviesmod.town` and `moviesleech.zip`")

# --- FUNCTIONS ---
def get_search_results(keyword, site_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    search_url = f"{site_url}?s={keyword.replace(' ', '+')}"
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        # These sites typically use <h2> or <a> tags for their movie titles in search results
        for item in soup.find_all(['h2', 'h3']):
            link_tag = item.find('a')
            if link_tag and link_tag.get('href'):
                title = link_tag.get_text().strip()
                link = link_tag.get('href')
                
                # STRICT FILTERING: Only show if keyword is in the title
                if keyword.lower() in title.lower():
                    results.append({"title": title, "link": link})
        
        return results
    except Exception as e:
        st.error(f"Error searching {site_url}: {e}")
        return []

# --- USER INTERFACE ---
query = st.text_input("Enter Movie or Keyword:", placeholder="e.g. Pluribus")

if query:
    sites = [
        "https://moviesmod.town/",
        "https://moviesleech.zip/",
        "https://rogmovies.world/",
        "https://new3.hdhub4u.fo/",
        "https://vegamovies.gratis/"
    ]
    
    all_results = []
    
    with st.spinner(f"Searching for '{query}'..."):
        for site in sites:
            res = get_search_results(query, site)
            for r in res:
                r['site'] = site.split('//')[1].split('/')[0] # Clean site name for display
                all_results.append(r)

    if all_results:
        st.success(f"Found {len(all_results)} matches in titles!")
        for item in all_results:
            with st.container():
                st.markdown(f"### [{item['site']}] {item['title']}")
                st.markdown(f"[View Movie Page]({item['link']})")
                st.divider()
    else:
        st.warning("No exact title matches found. Try a different keyword.")
        