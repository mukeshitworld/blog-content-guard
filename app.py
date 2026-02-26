import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from difflib import SequenceMatcher

# --- Config ---
TOOL_NAME = "Bluehost Blog ContentGuard"
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

st.set_page_config(page_title=TOOL_NAME, page_icon="🛡️", layout="wide")
st.title(f"🛡️ {TOOL_NAME}")
st.caption("Duplicate & topic detection using sitemap inventory")

# --- URL Filters ---
def is_valid_blog_post(url):
    return (
        "/blog/" in url
        and "/wp-content/" not in url
        and "/tag/" not in url
        and "/category/" not in url
        and "/page/" not in url
        and "/in/blog/" not in url
    )

# --- Fetch Sitemap URLs ---
@st.cache_data(ttl=360000)
def get_all_blog_urls():
    headers = {"User-Agent": "Mozilla/5.0 (SEO-ContentGuard)"}
    urls = []

    for sitemap in SITEMAPS:
        try:
            resp = requests.get(sitemap, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "xml")
            urls.extend([loc.text for loc in soup.find_all("loc")])
        except:
            pass

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

        with st.spinner("Fetching blog sitemap inventory..."):
            blog_urls = get_all_blog_urls()

        progress = st.progress(0)

        for i, kw in enumerate(keywords):

            keyword_slug = kw.replace(" ", "-")

            # 1) Exact slug match
            exact_matches = [
                u for u in blog_urls
                if u.rstrip("/").split("/")[-1] == keyword_slug
            ]

            # 2) Partial slug match
            partial_matches = [
                u for u in blog_urls
                if keyword_slug in u and u not in exact_matches
            ]

            # 3) Semantic similarity
            semantic_matches = []
            if not exact_matches and not partial_matches:
                for u in blog_urls:
                    slug_text = extract_slug(u)
                    if similarity(slug_text, kw) > 0.7:
                        semantic_matches.append(u)

            # --- Decision ---
            if exact_matches:
                match = exact_matches[0]
                status = "❌ Duplicate (Exact Slug)"

            elif partial_matches:
                match = partial_matches[0]
                status = "❌ Duplicate (Partial Slug)"

            elif semantic_matches:
                match = semantic_matches[0]
                status = "⚠ Similar Topic Exists"

            else:
                match = None
                status = "✅ Clear"

            results.append({
                "Keyword": kw,
                "Status": status,
                "Match Title": extract_slug(match).title() if match else "No match",
                "Existing URL": match if match else "N/A"
            })

            progress.progress((i + 1) / len(keywords))
            time.sleep(0.1)

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