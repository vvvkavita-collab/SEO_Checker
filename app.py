import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Advanced SEO Auditor – Premium Edition", layout="wide")

# ---------------- PREMIUM LAYOUT CSS ----------------
st.markdown("""
<style>
header[data-testid="stHeader"] {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {display: none;}
[data-testid="stDecoration"] {display: none;}
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #141E30, #243B55);
    color: white;
}
h1, h2, h3, h4, h5, h6, p, label { color: white; }
.stTextArea textarea, .stTextInput input {
    background: #1e2a3b; color: white;
}
.stButton>button {
    background: #4F81BD; color: white;
    font-size: 18px; border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SAFE GET TEXT ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except Exception:
        return ""

# ---------------- REQUEST HEADERS ----------------
REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 Chrome/120.0",
    "Accept-Language": "en-US,en;q=0.9"
}

# ---------------- ARTICLE EXTRACTOR ----------------
def extract_article(url):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        r = requests.get(url, headers=REQ_HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip() if soup.title else ""
        meta = ""
        md = soup.find("meta", attrs={"name": "description"})
        if md:
            meta = md.get("content", "")

        paras = soup.find_all("p")
        article = " ".join([safe_get_text(p) for p in paras])
        article = re.sub(r"\s+", " ", article)

        h1 = soup.find_all("h1")
        h2 = soup.find_all("h2")
        imgs = soup.find_all("img")

        img_count = len(imgs)
        alt_with = sum(1 for i in imgs if i.get("alt"))

        anchors = soup.find_all("a")
        internal, external = 0, 0
        domain = urlparse(url).netloc

        for a in anchors:
            href = a.get("href", "")
            if href.startswith("http"):
                if domain in href:
                    internal += 1
                else:
                    external += 1

        words = article.split()
        sentences = re.split(r"[.!?]", article)

        return {
            "title": title,
            "meta": meta,
            "h1": h1,
            "h2": h2,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal,
            "external_links": external,
            "paragraph_count": len(paras),
            "word_count": len(words),
            "avg_words_per_sentence": round(len(words) / max(1, len(sentences)), 2),
            "summary": " ".join(words[:20])
        }
    except Exception:
        return {
            "title": "", "meta": "", "h1": [], "h2": [],
            "img_count": 0, "alt_with": 0,
            "internal_links": 0, "external_links": 0,
            "paragraph_count": 0, "word_count": 0,
            "avg_words_per_sentence": 0, "summary": ""
        }

# ---------------- VERDICT ----------------
def verdict(val, mn=None, mx=None, exact=None):
    try:
        v = float(val)
    except:
        return "❌ Needs Fix"
    if exact is not None:
        return "✅ Good" if v == exact else "❌ Needs Fix"
    if mn is not None and mx is not None:
        return "✅ Good" if mn <= v <= mx else "❌ Needs Fix"
    if mn is not None:
        return "✅ Good" if v >= mn else "❌ Needs Fix"
    return "❌ Needs Fix"

# ---------------- SEO ANALYSIS ----------------
def seo_analysis(data):
    score = 0
    metrics = []

    metrics.append(("Title Length Actual", len(data["title"]), "50–60", verdict(len(data["title"]), 50, 60)))
    metrics.append(("Meta Length Actual", len(data["meta"]), "150–160", verdict(len(data["meta"]), 150, 160)))
    metrics.append(("H1 Count Actual", len(data["h1"]), "1", verdict(len(data["h1"]), exact=1)))
    metrics.append(("H2 Count Actual", len(data["h2"]), "2–5", verdict(len(data["h2"]), 2, 5)))
    metrics.append(("Content Length Actual", data["word_count"], "600+", verdict(data["word_count"], 600)))
    metrics.append(("Paragraph Count Actual", data["paragraph_count"], "8+", verdict(data["paragraph_count"], 8)))
    metrics.append(("Image Count Actual", data["img_count"], "3+", verdict(data["img_count"], 3)))
    metrics.append(("Alt Tags Actual", data["alt_with"], "All", verdict(data["alt_with"], exact=data["img_count"])))
    metrics.append(("Internal Links Actual", data["internal_links"], "2–5", verdict(data["internal_links"], 2, 5)))
    metrics.append(("External Links Actual", data["external_links"], "2–4", verdict(data["external_links"], 2, 4)))
    metrics.append(("Readability Actual", data["avg_words_per_sentence"], "10–20", verdict(data["avg_words_per_sentence"], 10, 20)))

    score = sum(8 for m in metrics if "✅" in m[3])
    grade = "A+" if score >= 80 else "A" if score >= 60 else "B" if score >= 40 else "C"

    return score, grade, metrics

# ---------------- COLUMN GUIDE SHEET ----------------
def column_guide_df():
    data = [
        ("SEO Score", "Overall SEO quality score", "80+", "Higher rank chance"),
        ("SEO Grade", "Score based grade", "A/A+", "Quick quality view"),
        ("Title Length Actual", "Title character count", "50–60", "CTR improvement"),
        ("Meta Length Actual", "Meta description size", "150–160", "Search visibility"),
        ("H1 Count Actual", "Main heading count", "1", "SEO structure"),
        ("H2 Count Actual", "Subheadings", "2–5", "Content clarity"),
        ("Content Length Actual", "Total words", "600+", "Ranking strength"),
        ("Paragraph Count Actual", "Paragraph blocks", "8+", "Readability"),
        ("Image Count Actual", "Images used", "3+", "Engagement"),
        ("Alt Tags Actual", "Images with ALT", "All", "Image SEO"),
        ("Internal Links Actual", "Same site links", "2–5", "Crawl depth"),
        ("External Links Actual", "Outside links", "2–4", "Trust"),
        ("Readability Actual", "Words per sentence", "10–20", "User experience"),
        ("Summary", "Short content preview", "Clear", "Editor help"),
    ]
    return pd.DataFrame(data, columns=["Column Name", "Meaning", "Ideal", "SEO Impact"])

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")

urls = st.text_area("Paste URLs (one per line)")

if st.button("Process & Download Report"):
    rows = []
    for url in urls.splitlines():
        if not url.strip():
            continue
        data = extract_article(url.strip())
        score, grade, metrics = seo_analysis(data)

        row = {"URL": url, "Summary": data["summary"], "SEO Score": score, "SEO Grade": grade}
        for m in metrics:
            row[m[0]] = m[1]
        rows.append(row)

    df = pd.DataFrame(rows)

    excel = BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Audit")
        column_guide_df().to_excel(writer, index=False, sheet_name="Column_Guide")

    st.download_button(
        "📥 Download SEO Report",
        excel.getvalue(),
        "SEO_Audit_Report.xlsx"
    )
