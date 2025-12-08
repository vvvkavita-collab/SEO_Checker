import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ----------------------------------------------------
# PAGE CONFIG — GitHub ribbon removed
# ----------------------------------------------------
st.set_page_config(
    page_title="Advanced SEO Auditor",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={}  # disables GitHub & About menu
)

# ----------------------------------------------------
# PREMIUM UI CSS — Dark mode + fixed file uploader
# ----------------------------------------------------
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #141E30, #243B55) !important;
    color: white !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F2027, #203A43, #2C5364);
    color: white !important;
}
h1, h2, h3, h4, h5, h6, p, span, div, label {
    color: white !important;
}
.stTextArea textarea, .stTextInput input {
    background: #1e2a3b !important;
    border: 2px solid #4F81BD !important;
    border-radius: 12px !important;
    color: white !important;
}
.stFileUploader {
    background: #1e2a3b !important;
    color: white !important;
    border: 2px dashed #4F81BD !important;
    border-radius: 12px !important;
    padding: 15px;
}
.stButton>button {
    background: #4F81BD !important;
    color: white !important;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 18px;
    border: none;
    box-shadow: 0px 4px 10px rgba(79,129,189,0.5);
}
.stButton>button:hover {
    background: #3A6EA5 !important;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# SAFE GET TEXT
# ----------------------------------------------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# ----------------------------------------------------
# ARTICLE EXTRACTOR
# ----------------------------------------------------
def extract_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        md = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", attrs={"property": "og:description"}
        )
        if md and md.get("content"):
            meta_desc = md.get("content").strip()
        paras = soup.find_all("p")
        article = " ". ".join([safe_get_text(p) for p in paras]).strip()
        article = re.sub(r"\s+", " ", article)
        h1 = [safe_get_text(t) for t in soup.find_all("h1")]
        h2 = [safe_get_text(t) for t in soup.find_all("h2")]
        imgs = soup.find_all("img")
        img_count = len(imgs)
        alt_with = sum(1 for im in imgs if (im.get("alt") or "").strip())
        anchors = soup.find_all("a")
        internal_links = 0
        external_links = 0
        domain = urlparse(url).netloc.lower()
        for a in anchors:
            href = a.get("href") or ""
            if href.startswith("#") or href.startswith("mailto:") or href.strip() == "":
                continue
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc.lower() != domain:
                external_links += 1
            else:
                internal_links += 1
        paragraph_count = len([p for p in paras if safe_get_text(p)])
        sentences = re.split(r"[.!?]\s+", article)
        sentence_count = len([s for s in sentences if s.strip()])
        words = article.split()
        word_count = len(words)
        avg_words_per_sentence = round(word_count / max(1, sentence_count), 2)
        summary = ""
        if sentence_count >= 1:
            summary = ". ".join(sentence.strip() for sentence in sentences[:2]).strip()
            if summary and not summary.endswith("."):
                summary += "."
        return {
            "title": title[:20],
            "meta": meta_desc,
            "article": article,
            "h1": h1,
            "h2": h2,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal_links,
            "external_links": external_links,
            "paragraph_count": paragraph_count,
            "sentence_count": sentence_count,
            "word_count": word_count,
            "avg_words_per_sentence": avg_words_per_sentence,
            "summary": summary[:20],
        }
    except:
        return {
            "title": "",
            "meta": "",
            "article": "",
            "h1": [],
            "h2": [],
            "img_count": 0,
            "alt_with": 0,
            "internal_links": 0,
            "external_links": 0,
            "paragraph_count": 0,
            "sentence_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "summary": "",
        }

# ----------------------------------------------------
# SEO ANALYSIS
# ----------------------------------------------------
def seo_analysis_struct(data):
    title = data["title"]
    meta = data["meta"]
    word_count = data["word_count"]
    paragraph_count = data["paragraph_count"]
    img_count = data["img_count"]
    alt_with = data["alt_with"]
    h1_count = len(data["h1"])
    h2_count = len(data["h2"])
    internal_links = data["internal_links"]
    external_links = data["external_links"]
    avg_wps = data["avg_words_per_sentence"]

    keyword_density = 0

    pairs = [
        ("Title Length Ideal", "50-60", "Title Length Actual", len(title)),
        ("Meta Length Ideal", "150-160", "Meta Length Actual", len(meta)),
        ("H1 Count Ideal", "1", "H1 Count Actual", h1_count),
        ("H2 Count Ideal", "2-5", "H2 Count Actual", h2_count),
        ("Content Length Ideal", "600+", "Content Length Actual", word_count),
        ("Paragraph Count Ideal", "8+", "Paragraph Count Actual", paragraph_count),
        ("Keyword Density Ideal", "1-2%", "Keyword Density Actual", keyword_density),
        ("Image Count Ideal", "3+", "Image Count Actual", img_count),
        ("Alt Tags Ideal", "All", "Alt Tags Actual", alt_with),
        ("Internal Links Ideal", "2-5", "Internal Links Actual", internal_links),
        ("External Links Ideal", "2-4", "External Links Actual", external_links),
        ("Readability Ideal", "10-20", "Readability Actual", avg_wps),
    ]

    score = 0
    if 50 <= len(title) <= 60: score += 10
    if 150 <= len(meta) <= 160: score += 10
    if h1_count == 1: score += 8
    if 2 <= h2_count <= 5: score += 6
    if word_count >= 600: score += 12
    if paragraph_count >= 8: score += 6
    if img_count >= 3: score += 8
    if img_count > 0 and alt_with == img_count: score += 6
    if 2 <= internal_links <= 5: score += 4
    if 2 <= external_links <= 4: score += 4
    if 10 <= avg_wps <= 20: score += 8

    score = min(score, 100)
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
    predicted_rating = round(score / 10, 1)
    extras = {"Summary": data["summary"]}
    return score, grade, predicted_rating, pairs, extras

# ----------------------------------------------------
# EXCEL FORMATTING
# ----------------------------------------------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb["Audit"]
    ws.sheet_view.showGridLines = False
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    red_fill = PatternFill("solid", fgColor="
