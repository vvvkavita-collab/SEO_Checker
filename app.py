import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
import json
import unicodedata
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Google Guidelines", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Google Ready)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= STOP WORDS =================
TITLE_STOP_WORDS = [
    "breaking", "exclusive", "shocking", "must read", "update", "alert"
]

URL_STOP_WORDS = [
    "for", "today", "latest", "news", "update", "information",
    "details", "story", "article", "this", "that", "here", "now"
]

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return (
        soup.find("article")
        or soup.find("div", class_=re.compile("content|story|article|post-body", re.I))
        or soup
    )

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

def safe_text(el):
    return el.get_text(" ", strip=True) if el else ""

def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(advertisement|also read|read more|inputs|agency)", text, re.I):
            continue
        paras.append(text)
    return paras

def get_real_images(article):
    imgs = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            if not re.search(r"(logo|icon|sprite|ads)", img["src"], re.I):
                imgs.append(img)
    if not imgs:
        for img in article.find_all("img"):
            if img.get("src") and "featured" in " ".join(img.get("class", [])):
                imgs.append(img)
    return imgs[:1]

def get_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            h = a["href"].strip()
            if h.startswith("#") or "javascript" in h:
                continue
            if h.startswith("http"):
                if domain in h:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
    return internal, external

def get_h2_count_fixed(article):
    h2s = article.find_all("h2")
    real = []
    for idx, h2 in enumerate(h2s):
        t = h2.get_text(strip=True)
        if idx == 0 and len(t) > 100:
            continue
        if len(t) < 20:
            continue
        if re.search(r"(advertisement|related|subscribe|promo)", t, re.I):
            continue
        real.append(h2)
    return len(real)

def generate_seo_title(title, max_len=70):
    if visible_len(title) <= max_len:
        return title
    words = title.split()
    out = ""
    for w in words:
        test = (out + " " + w).strip()
        if visible_len(test) > max_len:
            break
        out = test
    return out

# ================= URL CLEAN LOGIC =================
def get_url_words(url):
    path = urlparse(url).path
    path = re.sub(r"[^a-zA-Z0-9\-]", "", path)
    return [w for w in path.lower().strip("/").split("-") if w]

def detect_unnecessary_url_words(url):
    words = get_url_words(url)

    # Allow meaningful "for" usage
    safe_patterns = [
        r"jobs-for-(women|students|farmers)",
        r"scheme-for-(women|students|farmers)",
        r"scholarship-for-(students|girls)"
    ]
    joined = "-".join(words)
    for p in safe_patterns:
        if re.search(p, joined):
            return []

    return [w for w in words if w in URL_STOP_WORDS]

# ================= SCORE LOGIC =================
def calculate_score(title_len, word_count, img_count, h1_count, h2_count,
                    internal_links, external_links, has_stop_title,
                    has_schema, amp_flag, url_clean_flag, meta_image):
    score = 100
    if title_len > 70 or title_len < 55: score -= 12
    if word_count < 300: score -= 12
    if img_count < 1: score -= 10
    if not meta_image: score -= 5
    if h1_count != 1: score -= 10
    if h2_count < 2: score -= 8
    if internal_links < 2 or internal_links > 10: score -= 5
    if external_links > 2: score -= 4
    if has_stop_title: score -= 6
    if not has_schema: score -= 10
    if not amp_flag: score -= 3
    if not url_clean_flag: score -= 5
    return max(score, 0)

def extract_meta_image(soup):
    og = soup.find("meta", property="og:image")
    tw = soup.find("meta", property="twitter:image")
    return og["content"] if og and og.get("content") else (tw["content"] if tw and tw.get("content") else None)

def extract_json_ld(soup):
    scripts = soup.find_all("script", type="application/ld+json")
    out = []
    for s in scripts:
        try:
            out.append(json.loads(s.string))
        except:
            pass
    return out

def has_newsarticle_schema(json_ld_list):
    for jd in json_ld_list:
        if isinstance(jd, dict) and jd.get("@type") == "NewsArticle":
            return True
        if isinstance(jd, list):
            for i in jd:
                if isinstance(i, dict) and i.get("@type") == "NewsArticle":
                    return True
    return False

def is_amp(soup):
    return bool(soup.find("link", rel="amphtml"))

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1") or soup.find("title")
    title = safe_text(title_tag)

    seo_title = generate_seo_title(title)
    title_len = visible_len(title)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    img_count = len(get_real_images(article))
    meta_image = extract_meta_image(soup)

    h1_count = len(article.find_all("h1")) or len(soup.find_all("h1"))
    h2_count = get_h2_count_fixed(article)

    internal, external = get_links(article, domain)

    found_title_stop = [w for w in TITLE_STOP_WORDS if w in title.lower()]
    found_url_stop = detect_unnecessary_url_words(url)

    json_ld = extract_json_ld(soup)
    schema_flag = has_newsarticle_schema(json_ld)
    amp_flag = is_amp(soup)

    url_clean_flag = not bool(found_url_stop)

    score = calculate_score(
        title_len, word_count, img_count, h1_count, h2_count,
        internal, external, bool(found_title_stop),
        schema_flag, amp_flag, url_clean_flag, meta_image
    )

    audit_df = pd.DataFrame([
        ["Title Character Count", title_len, "55–70", "✅" if 55 <= title_len <= 70 else "⚠️"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "300+", "✅" if word_count >= 300 else "⚠️"],
        ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "⚠️"],
        ["Meta Image", meta_image or "None", "Present", "✅" if meta_image else "⚠️"],
        ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "⚠️"],
        ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "⚠️"],
        ["Internal Links", internal, "2–10", "✅" if 2 <= internal <= 10 else "⚠️"],
        ["External Links", external, "0–2", "✅" if external <= 2 else "⚠️"],
        ["Unnecessary Words (Title)", ", ".join(found_title_stop) or "None", "No", "⚠️" if found_title_stop else "✅"],
        ["Unnecessary Words (URL)", ", ".join(found_url_stop) or "None", "No", "⚠️" if found_url_stop else "✅"],
        ["Structured Data", "Yes" if schema_flag else "No", "Yes", "✅" if schema_flag else "⚠️"],
        ["AMP Presence", "Yes" if amp_flag else "No", "Optional", "ℹ️"],
        ["Final SEO Score", f"{score}/100", "≥80", "✅" if score >= 80 else "⚠️"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    return audit_df

# ================= RUN =================
if analyze and url_input:
    st.dataframe(analyze_url(url_input), use_container_width=True)
