import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
import unicodedata

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return (
        soup.find("article")
        or soup.find("div", class_=re.compile("content|story|article", re.I))
        or soup
    )

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

# ================= CONTENT LOGIC (UNCHANGED) =================
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
    return imgs[:1]   # EXACT SAME AS YOUR SCRIPT

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

# ================= SEO TITLE (UNCHANGED) =================
def generate_seo_title(title, max_len=60):
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

# ================= CLEAN URL (UNCHANGED) =================
STOP_WORDS = {"is","the","and","of","to","in","for","on","with","by","who"}

def clean_slug(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    words = [w for w in text.split() if w not in STOP_WORDS]
    return "-".join(words[:10])

def generate_clean_url(url, title):
    parsed = urlparse(url)
    slug = clean_slug(title)
    base = parsed.path.rsplit("/", 1)[0]
    return f"{parsed.scheme}://{parsed.netloc}{base}/{slug}"

# ================= SCORE LOGIC (UNCHANGED) =================
def calculate_score(title_len, url_clean, has_stop):
    score = 100
    if title_len > 60:
        score -= 20
    if not url_clean:
        score -= 30
    if has_stop:
        score -= 10
    return max(score, 0)

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No H1 Found"

    seo_title = generate_seo_title(title)
    clean_url = generate_clean_url(url, seo_title)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    img_count = len(get_real_images(article))
    h1_count = len(article.find_all("h1"))
    h2_count = get_h2_count_fixed(article)
    internal, external = get_links(article, domain)

    found_stop = [w for w in STOP_WORDS if f" {w} " in title.lower()]
    url_clean_flag = url.rstrip("/") == clean_url.rstrip("/")

    score = calculate_score(visible_len(title), url_clean_flag, bool(found_stop))

    # ---- SEO AUDIT (IDEAL WORDING UPDATED, VALUES SAME) ----
    audit_df = pd.DataFrame([
        ["Title Character Count", visible_len(title), "≤ 60 (Google SERP)", "❌" if visible_len(title) > 60 else "✅"],
        ["Suggested SEO Title", seo_title, "SEO friendly title", "—"],
        ["Word Count", word_count, "250+ (News minimum)", "❌" if word_count < 250 else "✅"],
        ["News Image Count", img_count, "1+ relevant image", "❌" if img_count < 1 else "✅"],
        ["H1 Count", h1_count, "Exactly 1", "❌" if h1_count != 1 else "✅"],
        ["H2 Count", h2_count, "2+ subheadings", "❌" if h2_count < 2 else "✅"],
        ["Internal Links", internal, "2–10 internal links", "❌" if internal < 2 else "✅"],
        ["External Links", external, "0–2 authority links", "❌" if external > 2 else "✅"],
        ["Unnecessary Words", ", ".join(found_stop) if found_stop else "None", "Avoid stop words", "❌" if found_stop else "✅"],
        ["Suggested Clean SEO URL", clean_url, clean_url, "✅" if url_clean_flag else "❌"],
        ["Title + URL SEO Score", f"{score} / 100", "≥ 80 (Good)", "⚠️" if score < 80 else "✅"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    # ---- SCORING TABLE (UNCHANGED) ----
    grading_df = pd.DataFrame([
        ["Base Score", 100],
        ["Title > 60 characters", -20 if visible_len(title) > 60 else 0],
        ["URL not clean", -30 if not url_clean_flag else 0],
        ["Unnecessary words", -10 if found_stop else 0],
        ["Final Score", score],
    ], columns=["Scoring Rule", "Value"])

    # ---- GUIDELINE SHEET (NEW, NO CALCULATION IMPACT) ----
    guide_df = pd.DataFrame([
        ["CTR", "Click Through Rate", "High CTR = more traffic, better rankings"],
        ["Title Length", "≤ 60", "Avoid SERP truncation"],
        ["Word Count", "250+", "Minimum news depth"],
        ["Images", "1+", "Visual engagement"],
        ["Internal Links", "2–10", "Better crawl & retention"],
        ["External Links", "0–2", "Trust signals"],
    ], columns=["Metric", "Meaning", "SEO Impact"])

    return audit_df, grading_df, guide_df

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = [l.strip() for l in bulk_file.read().decode("utf-8").splitlines() if l.strip()]
    elif url_input:
        urls = [url_input]

    for u in urls:
        audit, grading, guide = analyze_url(u)

        st.subheader(f"📊 SEO Audit – {u}")
        st.dataframe(audit, use_container_width=True)

        st.subheader("📐 SEO Score / Grading Logic")
        st.dataframe(grading, use_container_width=True)

        st.subheader("📘 SEO Guidelines Reference")
        st.dataframe(guide, use_container_width=True)
