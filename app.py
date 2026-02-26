import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from difflib import SequenceMatcher

# --- Config ---
TOOL_NAME = "Bluehost Blog ContentGuard"
CACHE_TTL = 86400  # 24 hours

SITEMAPS = [
    "https://www.bluehost.com/blog/post-sitemap.xml",
    "https://www.bluehost.com/blog/post-sitemap2.xml",
    "https://www.bluehost.com/blog/post-sitemap3.xml",
    "https://www.bluehost.com/blog/post-sitemap4.xml",
    "https://www.bluehost.com/blog/post-sitemap5.xml",
    "https://www.bluehost.com/blog/post-sitemap6.xml",
    "https://www.bluehost.com/blog/post-sitemap7.xml",
    "https://www.bluehost.com/blog/post-sitemap8.xml",
    "https://www.bluehost.com/blog/post-sitemap9.xml",
    "https://www.bluehost.com/blog/post-sitemap10.xml"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

st.set_page_config(page_title=TOOL_NAME, page_icon="🛡️", layout="wide")
st.title(f"🛡️ {TOOL_NAME}")
st.caption("Duplicate & topic detection using sitemap inventory")

# --- Manual Cache Refresh ---
if st.button("🔄 Refresh Sitemap Cache"):
    st.cache_data.clear()
    st.success("Cache cleared. Next audit will fetch fresh sitemap data.")

# --- Filters ---
def is_valid_blog_post(url):
    return (
        "/blog/" in url
        and "/wp-content/" not in url
        and "/tag/" not in url
        and "/category/" not in url
        and "/page/" not in url
        and "/in/blog/" not in url
    )

# --- Sitemap Fetch ---
@st.cache_data(ttl=CACHE_TTL)
def get_all_blog_urls():
    urls = []

    for sitemap in SITEMAPS:
        success = False

        for attempt in range(3):
            try:
                resp = requests.get(sitemap, headers=HEADERS, timeout=15)

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml-xml")
                    urls.extend([loc.text for loc in soup.find_all("loc")])
                    success = True
                    break

                else:
                    time.sleep(2)

            except Exception:
                time.sleep(2)

        if not success:
            st.warning(f"⚠ Could not fetch sitemap: {sitemap}")

    clean_urls = [u for u in urls if is_valid_blog_post(u)]
    return list(set(clean_urls))

# --- Helpers ---
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extract_slug(url):
    return url.rstrip("/").split("/")[-1].replace("-", " ").lower()

# --- Input ---
raw_input = st.text_area(
    "Enter Keywords (comma separated)",
    placeholder="e.g. how to create a website, wordpress hosting guide"
)

# --- Run Audit ---
if st.button("Run Blog Audit"):

    if raw_input:
        keywords = [k.strip().lower() for k in raw_input.split(",") if k.strip()]
        results = []

        with st.spinner("Loading blog inventory..."):
            blog_urls = get_all_blog_urls()

        st.caption(f"Loaded {len(blog_urls)} blog URLs")

        progress = st.progress(0)

        for i, kw in enumerate(keywords):
            keyword_slug = kw.replace(" ", "-")

            exact = [u for u in blog_urls if u.rstrip("/").split("/")[-1] == keyword_slug]
            partial = [u for u in blog_urls if keyword_slug in u and u not in exact]

            semantic = []
            if not exact and not partial:
                for u in blog_urls:
                    if similarity(extract_slug(u), kw) > 0.7:
                        semantic.append(u)

            if exact:
                match, status = exact[0], "❌ Duplicate (Exact Slug)"
            elif partial:
                match, status = partial[0], "❌ Duplicate (Partial Slug)"
            elif semantic:
                match, status = semantic[0], "⚠ Similar Topic Exists"
            else:
                match, status = None, "✅ Clear"

            results.append({
                "Keyword": kw,
                "Status": status,
                "Match Title": extract_slug(match).title() if match else "No match",
                "Existing URL": match if match else "N/A"
            })

            progress.progress((i + 1) / len(keywords))

        # --- Display ---
        df = pd.DataFrame(results)

        def color_status(val):
            if "Duplicate" in val:
                return "color:red; font-weight:bold"
            elif "Similar" in val:
                return "color:orange; font-weight:bold"
            else:
                return "color:green; font-weight:bold"

        st.subheader("Audit Results")
        st.dataframe(df.style.applymap(color_status, subset=["Status"]), use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export CSV", data=csv, file_name="bluehost_blog_audit.csv")

    else:
        st.error("Please enter keywords")
