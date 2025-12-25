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

# ================= UI FIX =================
st.markdown("""
<style>
div[data-testid="stDataFrame"] table th { text-align: center !important; }
div[data-testid="stDataFrame"] table td { vertical-align: middle; }
div[data-testid="stDataFrame"] table td:nth-child(3),
div[data-testid="stDataFrame"] table td:nth-child(4),
div[data-testid="stDataFrame"] table td:nth-child(5) {
    text-align: center !important;
}
</style>
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= STOP WORDS =================
TITLE_STOP_WORDS = [
    "breaking","exclusive","shocking","must read",
    "update","alert","latest","big","viral"
]

URL_STOP_WORDS = [
    "for","today","latest","news","update","information",
    "details","story","article","this","that","here","now",
    "about","on","in","to","of","with",
    "current","recent","new",
    "breaking","exclusive","viral","shocking","must","read",
    "what","why","how","when","where","who",
    "page","pages","index","view","print","amp","category","tag"
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
        t = p.get_text(" ", strip=True)
        if len(t) < 80: continue
        if re.search(r"(advertisement|also read|read more|inputs|agency)", t, re.I):
            continue
        paras.append(t)
    return paras

def get_real_images(article):
    imgs = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src") and not re.search(r"(logo|icon|ads)", img["src"], re.I):
            imgs.append(img)
    return imgs[:1]

def get_links(article, domain):
    internal = external = 0
    for a in article.find_all("a", href=True):
        h = a["href"]
        if h.startswith("http"):
            internal += domain in h
            external += domain not in h
        else:
            internal += 1
    return internal, external

def get_h2_count_fixed(article):
    return len([
        h2 for h2 in article.find_all("h2")
        if len(h2.get_text(strip=True)) >= 20
    ])

def get_url_words(url):
    path = urlparse(url).path
    path = re.sub(r"[^a-zA-Z0-9\-]", "", path)
    return [w for w in path.lower().strip("/").split("-") if w]

# ================= 🔥 AI-STYLE SEO TITLE (NEW) =================
def generate_ai_style_seo_title(title, h1, url, paragraphs, max_len=70):
    clean = re.sub(
        r"(breaking|exclusive|latest|update|viral|alert)",
        "",
        title,
        flags=re.I
    ).strip()

    url_words = [
        w for w in get_url_words(url)
        if w not in URL_STOP_WORDS and len(w) > 3
    ]

    base = h1 if 20 <= len(h1) <= 90 else clean

    for w in url_words[:2]:
        if w.lower() not in base.lower():
            base += f" {w.title()}"

    words = base.split()
    out = ""
    for w in words:
        test = (out + " " + w).strip()
        if visible_len(test) > max_len:
            break
        out = test

    return out

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title = safe_text(soup.find("h1") or soup.find("title"))
    paragraphs = get_real_paragraphs(article)

    seo_title = generate_ai_style_seo_title(
        title=title,
        h1=safe_text(article.find("h1")),
        url=url,
        paragraphs=paragraphs
    )

    audit_df = pd.DataFrame([
        ["Suggested SEO Title", title, seo_title, "—"]
    ], columns=["Metric","Actual","Ideal","Verdict"])

    return audit_df, pd.DataFrame()

# ================= RUN =================
urls = []
if bulk_file:
    raw = bulk_file.read().decode("utf-8", errors="ignore")
    urls = [l.strip() for l in raw.splitlines() if l.strip()]
if url_input:
    urls.append(url_input.strip())

if analyze and urls:
    for u in urls:
        st.subheader(f"📊 SEO Audit – {u}")
        audit_df, _ = analyze_url(u)
        st.dataframe(audit_df, use_container_width=True)
