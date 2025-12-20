import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pandas as pd
import re

st.set_page_config(page_title="Advanced SEO Auditor – News & Blog", layout="wide")

# -----------------------------
# HELPERS
# -----------------------------

def clean_text(txt):
    return re.sub(r"\s+", " ", txt).strip()

def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (SEO Auditor Bot)"
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text

# -----------------------------
# ARTICLE EXTRACTION (NEWS SAFE)
# -----------------------------

def extract_news_data(url):
    html = get_html(url)
    soup = BeautifulSoup(html, "lxml")

    # ---- Title ----
    title = soup.title.text.strip() if soup.title else ""

    # ---- Meta Description ----
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    # ---- H1 / H2 ----
    h1 = soup.find("h1")
    h1_text = clean_text(h1.text) if h1 else ""

    h2s = soup.find_all("h2")
    h2_count = len([h for h in h2s if len(h.text.strip()) > 10])

    # ---- MAIN ARTICLE BODY (Patrika safe selectors) ----
    article = (
        soup.find("div", class_="storyContent")
        or soup.find("article")
        or soup.find("div", {"itemprop": "articleBody"})
    )

    if not article:
        return None

    # ---- Paragraphs (ignore short dek / caption lines) ----
    paragraphs = [
        p.text.strip()
        for p in article.find_all("p")
        if len(p.text.strip()) >= 40
    ]
    paragraph_count = len(paragraphs)

    # ---- Word Count ----
    word_count = sum(len(p.split()) for p in paragraphs)

    # ---- Images (article body only) ----
    images = article.find_all("img")
    valid_images = [
        img for img in images
        if img.get("src") and not any(x in img.get("src").lower() for x in ["logo", "icon", "ads"])
    ]
    image_count = len(valid_images)

    # ---- Links (article body only) ----
    domain = urlparse(url).netloc

    internal_links = 0
    external_links = 0

    for a in article.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#"):
            continue
        if domain in href:
            internal_links += 1
        elif href.startswith("http"):
            external_links += 1

    return {
        "Title Length": len(title),
        "Meta Characters": len(meta_desc),
        "H1 Count": 1 if h1_text else 0,
        "H2 Count": h2_count,
        "Word Count": word_count,
        "Paragraph Count": paragraph_count,
        "Image Count": image_count,
        "Internal Links": internal_links,
        "External Links": external_links,
        "Title": title,
        "Meta": meta_desc,
    }

# -----------------------------
# SCORING & VERDICT
# -----------------------------

def verdict(actual, low, high=None):
    if high:
        return actual >= low and actual <= high
    return actual >= low

def discover_score(d):
    score = 0
    score += 20 if d["Word Count"] >= 300 else 0
    score += 15 if d["Image Count"] >= 1 else 0
    score += 15 if d["H2 Count"] >= 2 else 0
    score += 15 if 50 <= d["Title Length"] <= 70 else 0
    score += 15 if 70 <= d["Meta Characters"] <= 160 else 0
    score += 20 if d["Paragraph Count"] >= 4 else 0
    return min(score, 100)

def hindi_ctr_predictor(title):
    power_words = ["बड़ा", "तगड़ा", "खुलासा", "देखें", "जानिए", "ऐलान"]
    score = 50
    score += sum(5 for w in power_words if w in title)
    score += 10 if "?" in title else 0
    return min(score, 100)

# -----------------------------
# UI
# -----------------------------

st.title("🧠 Advanced SEO Auditor – News & Blog")

urls = st.text_area("Paste URLs (one per line)")
analyze = st.button("Analyze")

if analyze:
    rows = []

    for url in urls.splitlines():
        url = url.strip()
        if not url:
            continue

        data = extract_news_data(url)
        if not data:
            st.warning(f"Content not detected: {url}")
            continue

        rows.extend([
            ("Title Length", data["Title Length"], "50–60", verdict(data["Title Length"], 50, 60)),
            ("Meta Characters", data["Meta Characters"], "70–160", verdict(data["Meta Characters"], 70, 160)),
            ("H1 Count", data["H1 Count"], "1", data["H1 Count"] == 1),
            ("H2 Count", data["H2 Count"], "2+", data["H2 Count"] >= 2),
            ("Word Count", data["Word Count"], "250+", data["Word Count"] >= 250),
            ("Image Count", data["Image Count"], "1+", data["Image Count"] >= 1),
            ("Internal Links", data["Internal Links"], "2–10", verdict(data["Internal Links"], 2, 10)),
            ("External Links", data["External Links"], "0–2", verdict(data["External Links"], 0, 2)),
        ])

        df = pd.DataFrame(rows, columns=["Metric", "Actual", "Ideal", "Verdict"])
        df["Verdict"] = df["Verdict"].apply(lambda x: "✅" if x else "❌")

        st.subheader("SEO Audit Report")
        st.dataframe(df, use_container_width=True)

        # Discover Score
        dscore = discover_score(data)
        st.subheader("📈 Google Discover Friendly Score")
        st.progress(dscore / 100)
        st.write(f"Score: {dscore}/100")

        # CTR Predictor
        ctr = hindi_ctr_predictor(data["Title"])
        st.subheader("📰 Hindi Headline CTR Predictor")
        st.progress(ctr / 100)
        st.write(f"Estimated CTR Strength: {ctr}%")

        # CMS Editor Suggestions
        st.subheader("📝 CMS Editor Suggestions")
        if data["Title Length"] > 60:
            st.write("• Title छोटा करें (60 characters से कम)")
        if data["Meta Characters"] > 160:
            st.write("• Meta description छोटा करें")
        if data["Image Count"] == 0:
            st.write("• कम से कम 1 खबर से संबंधित image जोड़ें")
        if data["Internal Links"] < 2:
            st.write("• 2–3 internal news links जोड़ें")

