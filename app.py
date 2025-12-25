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

# ================= CSS FIX (CENTER ALIGN + WIDTH) =================
st.markdown("""
<style>
div[data-testid="stDataFrame"] table th {
    text-align: center !important;
}
div[data-testid="stDataFrame"] table td {
    vertical-align: middle;
}
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
TITLE_STOP_WORDS = ["breaking","exclusive","shocking","must read","update","alert"]
URL_STOP_WORDS = ["for","today","latest","news","update","information","details","story","article","this","that","here","now"]

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

def safe_text(el):
    return el.get_text(" ", strip=True) if el else ""

def generate_seo_title(title, max_len=70):
    if visible_len(title) <= max_len:
        return title
    out = ""
    for w in title.split():
        test = (out + " " + w).strip()
        if visible_len(test) > max_len:
            break
        out = test
    return out

def extract_meta_image(soup):
    og = soup.find("meta", property="og:image")
    tw = soup.find("meta", property="twitter:image")
    return og["content"] if og and og.get("content") else (tw["content"] if tw and tw.get("content") else None)

def calculate_score(title_len, word_count, img_count, h1, h2, internal, external, stop, schema, amp, url_clean, meta):
    score = 100
    if title_len < 55 or title_len > 70: score -= 12
    if word_count < 300: score -= 12
    if img_count < 1: score -= 10
    if not meta: score -= 5
    if h1 != 1: score -= 10
    if h2 < 2: score -= 8
    if internal < 2 or internal > 10: score -= 5
    if external > 2: score -= 4
    if stop: score -= 6
    if not schema: score -= 10
    if not amp: score -= 3
    if not url_clean: score -= 5
    return max(score, 0)

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    title = safe_text(soup.find("h1") or soup.find("title"))
    title_len = visible_len(title)
    seo_title = generate_seo_title(title)

    word_count = len(soup.get_text().split())
    img_count = len(soup.find_all("img"))
    meta_image = extract_meta_image(soup)
    h1_count = len(soup.find_all("h1"))
    h2_count = len(soup.find_all("h2"))
    internal = external = 0

    score = calculate_score(
        title_len, word_count, img_count,
        h1_count, h2_count,
        internal, external,
        False, False, False, True, meta_image
    )

    audit_df = pd.DataFrame([
        ["Title Character Count", title_len, "55–70", "⚠️" if title_len > 70 or title_len < 55 else "✅"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "300+", "✅"],
        ["News Image Count", img_count, "1+", "✅"],
        ["Meta Image", meta_image or "None", "Present", "⚠️" if not meta_image else "✅"],
        ["H1 Count", h1_count, "1", "⚠️" if h1_count != 1 else "✅"],
        ["H2 Count", h2_count, "2+", "⚠️" if h2_count < 2 else "✅"],
        ["Final SEO Score", f"{score}/100", "≥80", "⚠️" if score < 80 else "✅"],
    ], columns=["Metric","Actual","Ideal","Verdict"])

    grading_df = pd.DataFrame([
        ["Base Score", 100],
        ["Title outside 55–70", -12 if title_len < 55 or title_len > 70 else 0],
        ["Word Count < 300", -12 if word_count < 300 else 0],
        ["Image < 1", -10 if img_count < 1 else 0],
        ["Final Score", score]
    ], columns=["Scoring Rule","Value"])

    return audit_df, grading_df

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
        audit_df, grading_df = analyze_url(u)

        st.dataframe(
            audit_df,
            use_container_width=True,
            column_config={
                "Metric": st.column_config.TextColumn(width="medium"),
                "Actual": st.column_config.TextColumn(width="small"),
                "Ideal": st.column_config.TextColumn(width="small"),
                "Verdict": st.column_config.TextColumn(width="small"),
            }
        )

        st.subheader("📐 SEO Score / Grading Logic")
        st.dataframe(
            grading_df,
            use_container_width=False,
            column_config={
                "Scoring Rule": st.column_config.TextColumn(width="medium"),
                "Value": st.column_config.NumberColumn(width="small"),
            }
        )
