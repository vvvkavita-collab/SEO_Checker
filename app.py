import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")

# ---------------- SAFE GET TEXT ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# ---------------- ARTICLE EXTRACTOR ----------------
def extract_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if md and md.get("content"):
            meta_desc = md.get("content").strip()

        paras = soup.find_all("p")
        article = ".".join([safe_get_text(p) for p in paras]).strip()
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
            "title": title,
            "meta": meta_desc,
            "h1": h1,
            "h2": h2,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal_links,
            "external_links": external_links,
            "paragraph_count": paragraph_count,
            "word_count": word_count,
            "avg_words_per_sentence": avg_words_per_sentence,
            "summary": summary[:20],
        }
    except:
        return {k: "" for k in [
            "title","meta","h1","h2","img_count","alt_with","internal_links",
            "external_links","paragraph_count","word_count","avg_words_per_sentence","summary"
        ]}

# ---------------- VERDICT FUNCTION ----------------
def verdict(actual, ideal_min=None, ideal_max=None, ideal_exact=None):
    try:
        val = float(actual)
    except:
        return "❌ Needs Fix"
    if ideal_exact is not None:
        return "✅ Good" if val == ideal_exact else "❌ Needs Fix"
    if ideal_min is not None and ideal_max is not None:
        if ideal_min <= val <= ideal_max:
            return "✅ Good"
        elif val > ideal_max:
            return "⚠️ Excessive"
        else:
            return "❌ Needs Fix"
    if ideal_min is not None:
        return "✅ Good" if val >= ideal_min else "❌ Needs Fix"
    return "❌ Needs Fix"

# ---------------- SEO ANALYSIS ----------------
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

    pairs = [
        ("Title Length Actual", len(title), verdict(len(title), 50, 60)),
        ("Meta Length Actual", len(meta), verdict(len(meta), 150, 160)),
        ("H1 Count Actual", h1_count, verdict(h1_count, ideal_exact=1)),
        ("H2 Count Actual", h2_count, verdict(h2_count, 2, 5)),
        ("Content Length Actual", word_count, verdict(word_count, 600)),
        ("Paragraph Count Actual", paragraph_count, verdict(paragraph_count, 8)),
        ("Image Count Actual", img_count, verdict(img_count, 3)),
        ("Alt Tags Actual", alt_with, verdict(alt_with, ideal_exact=img_count)),
        ("Internal Links Actual", internal_links, verdict(internal_links, 2, 5)),
        ("External Links Actual", external_links, verdict(external_links, 2, 4)),
        ("Readability Actual", avg_wps, verdict(avg_wps, 10, 20)),
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
    extras = {"Summary": (data["summary"] or "")[:20]}
    return score, grade, pairs, extras

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.subheader("URL Analysis → Excel Report → SEO Guidelines (Auto Generated)")

uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt", "csv", "xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)

if uploaded is not None:
    try:
        if uploaded.type == "text/plain":
            content = uploaded.read().decode("utf-8", errors="ignore")
            uploaded_urls = "\n".join([l.strip() for l in content.splitlines() if l.strip()])
        elif uploaded.type == "text/csv":
            df = pd.read_csv(uploaded, header=None)
            uploaded_urls = "\n".join(df.iloc[:, 0].astype(str).str.strip())
        else:
            df = pd.read_excel(uploaded, header=None)
            uploaded_urls = "\n".join(df.iloc[:, 0].astype(str).str.strip())
        st.info("File processed. Merged into the text area below.")
        existing = urls_input.strip()
        urls_input = (existing + "\n" + uploaded_urls).strip() if existing else uploaded_urls
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")

process = st.button("Process & Create Report")

if process:
    if not urls_input.strip():
        st.error("Please paste some URLs or upload a file.")
    else:
        urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
        rows = []
        progress = st.progress(0)
        status = st.empty()

