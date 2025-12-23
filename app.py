import streamlit as st
import pandas as pd
import requests, re, unicodedata
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – News & Blog", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= INPUT =================
bulk_file = st.sidebar.file_uploader("Upload URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def visible_len(txt):
    return sum(1 for c in txt if not unicodedata.category(c).startswith("C"))

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return soup.find("article") or soup.find("div", class_=re.compile("story|content|article", re.I)) or soup

# ---------- FIXED IMAGE LOGIC ----------
def get_images(article):
    imgs = []
    for img in article.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        if re.search(r"(logo|icon|sprite|ads)", src, re.I):
            continue
        imgs.append(src)
    return imgs

def get_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) >= 80:
            paras.append(t)
    return paras

def get_h2(article):
    return [h for h in article.find_all("h2") if len(h.get_text(strip=True)) > 15]

def get_links(article, domain):
    i = e = 0
    for a in article.find_all("a", href=True):
        h = a["href"]
        if h.startswith("http"):
            e += 0 if domain in h else 1
            i += 1 if domain in h else 0
        elif h.startswith("/"):
            i += 1
    return i, e

STOP_WORDS = {"is","the","and","of","to","in","for","on","with","by"}

def clean_slug(text):
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    words = [w for w in text.split() if w not in STOP_WORDS]
    return "-".join(words[:10])

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else "No H1"

    clean_url = f"{urlparse(url).scheme}://{domain}/{clean_slug(title)}"

    paras = get_paragraphs(article)
    words = sum(len(p.split()) for p in paras)

    images = get_images(article)
    h2s = get_h2(article)
    internal, external = get_links(article, domain)

    score = 100
    if visible_len(title) > 60: score -= 20
    if words < 300: score -= 20
    if len(images) < 1: score -= 10
    if internal < 2: score -= 10
    if external > 2: score -= 10
    if url.rstrip("/") != clean_url.rstrip("/"): score -= 10
    score = max(score, 0)

    audit = pd.DataFrame([
        ["Title Length", visible_len(title), "50–60", "❌" if visible_len(title) > 60 else "✅"],
        ["Word Count", words, "300+", "❌" if words < 300 else "✅"],
        ["Paragraphs", len(paras), "6+", "❌" if len(paras) < 6 else "✅"],
        ["Images", len(images), "1–3", "❌" if len(images) < 1 else "✅"],
        ["H1 Count", 1 if h1 else 0, "Exactly 1", "❌" if not h1 else "✅"],
        ["H2 Count", len(h2s), "2–6", "❌" if len(h2s) < 2 else "✅"],
        ["Internal Links", internal, "2–10", "❌" if internal < 2 else "✅"],
        ["External Links", external, "0–2", "❌" if external > 2 else "✅"],
        ["Actual URL", url, "—", "—"],
        ["Ideal SEO URL", clean_url, "Clean SEO URL", "❌" if url != clean_url else "✅"],
        ["Final SEO Score", score, "≥ 80", "⚠️" if score < 80 else "✅"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    score_df = pd.DataFrame([
        ["Base Score", 100],
        ["Title > 60", -20 if visible_len(title) > 60 else 0],
        ["Low Word Count", -20 if words < 300 else 0],
        ["No Image", -10 if len(images) < 1 else 0],
        ["Poor Links", -10 if internal < 2 else 0],
        ["URL not clean", -10 if url != clean_url else 0],
        ["Final Score", score],
    ], columns=["Rule", "Impact"])

    guideline = pd.DataFrame([
        ["Title", "50–60 chars", "Higher CTR"],
        ["Content Length", "300+ words", "Topical depth"],
        ["Paragraphs", "6+", "Readability"],
        ["Images", "1–3", "Engagement"],
        ["H1", "Exactly 1", "Structure"],
        ["H2", "2–6", "Scannability"],
        ["Internal Links", "2–10", "Crawl & retention"],
        ["External Links", "0–2", "Trust"],
        ["URL", "Clean & short", "Indexing"],
        ["Mobile Friendly", "Yes", "Ranking factor"],
        ["Page Speed", "<3 sec", "User experience"],
    ], columns=["Metric", "Ideal", "SEO Impact"])

    return audit, score_df, guideline

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = bulk_file.read().decode().splitlines()
    elif url_input:
        urls = [url_input]

    for u in urls:
        audit, score, guide = analyze_url(u)

        st.subheader(f"SEO Audit – {u}")
        st.dataframe(audit, use_container_width=True)

        st.subheader("SEO Score Logic")
        st.table(score)

        st.subheader("SEO / Google Guidelines")
        st.table(guide)
