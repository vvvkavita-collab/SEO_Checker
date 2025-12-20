import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pandas as pd
import re

# --------------------------------------------------
st.set_page_config(
    page_title="Advanced SEO Auditor – News & Blog",
    layout="wide"
)
# --------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (SEO Auditor Bot)"
}

# --------------------------------------------------
def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def clean(txt):
    return re.sub(r"\s+", " ", txt).strip()

# --------------------------------------------------
def extract_article(url):
    soup = BeautifulSoup(fetch_html(url), "lxml")

    # -------- Title ----------
    title = soup.title.text.strip() if soup.title else ""

    # -------- Meta ----------
    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_desc = meta["content"].strip()

    # -------- H1 / H2 ----------
    h1 = soup.find("h1")
    h2_count = len([h for h in soup.find_all("h2") if len(h.text.strip()) > 10])

    # -------- Article Body (Patrika safe) ----------
    article = None
    story = soup.find("div", class_="storyContent")
    if story:
        article = story.find("div", class_="content") or story

    if not article:
        article = soup.find("article")

    if not article:
        article = soup.find("div", {"itemprop": "articleBody"})

    if not article:
        return None

    # -------- Paragraphs ----------
    paragraphs = []
    for p in article.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if (
            len(txt) >= 50
            and not txt.lower().startswith(("also read", "read more"))
        ):
            paragraphs.append(txt)

    paragraph_count = len(paragraphs)
    word_count = sum(len(p.split()) for p in paragraphs)

    # -------- Images (news only) ----------
    images = []
    for img in article.find_all("img"):
        src = img.get("src") or ""
        if (
            src
            and "patrika" in src
            and not any(x in src.lower() for x in ["logo", "icon", "ads"])
        ):
            images.append(img)

    image_count = len(images)

    # -------- Links ----------
    domain = urlparse(url).netloc
    internal = 0
    external = 0

    for a in article.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#"):
            continue
        if domain in href:
            internal += 1
        elif href.startswith("http"):
            external += 1

    return {
        "Title Length": len(title),
        "Meta Characters": len(meta_desc),
        "H1 Count": 1 if h1 else 0,
        "H2 Count": h2_count,
        "Word Count": word_count,
        "Image Count": image_count,
        "Internal Links": internal,
        "External Links": external,
        "Paragraph Count": paragraph_count,
        "Title": title
    }

# --------------------------------------------------
def verdict(actual, low, high=None):
    if high:
        return low <= actual <= high
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

def hindi_ctr_score(title):
    power = ["बड़ा", "खुलासा", "देखें", "जानिए", "ऐलान"]
    score = 50
    score += sum(5 for w in power if w in title)
    score += 10 if "?" in title else 0
    return min(score, 100)

# --------------------------------------------------
st.title("🧠 Advanced SEO Auditor – News & Blog")

urls = st.text_area("Paste URLs (one per line)")
if st.button("Analyze"):

    for url in urls.splitlines():
        url = url.strip()
        if not url:
            continue

        data = extract_article(url)
        if not data:
            st.warning(f"Content not detected: {url}")
            continue

        rows = [
            ("Title Length", data["Title Length"], "50–60", verdict(data["Title Length"], 50, 60)),
            ("Meta Characters", data["Meta Characters"], "70–160", verdict(data["Meta Characters"], 70, 160)),
            ("H1 Count", data["H1 Count"], "1", data["H1 Count"] == 1),
            ("H2 Count", data["H2 Count"], "2+", data["H2 Count"] >= 2),
            ("Word Count", data["Word Count"], "250+", data["Word Count"] >= 250),
            ("Image Count", data["Image Count"], "1+", data["Image Count"] >= 1),
            ("Internal Links", data["Internal Links"], "2–10", verdict(data["Internal Links"], 2, 10)),
            ("External Links", data["External Links"], "0–2", verdict(data["External Links"], 0, 2)),
        ]

        df = pd.DataFrame(rows, columns=["Metric", "Actual", "Ideal", "Verdict"])
        df["Verdict"] = df["Verdict"].apply(lambda x: "✅" if x else "❌")

        st.subheader("SEO Audit Report")
        st.dataframe(df, use_container_width=True)

        # Discover
        dscore = discover_score(data)
        st.subheader("📈 Google Discover Friendly Score")
        st.progress(dscore / 100)
        st.write(f"Score: {dscore}/100")

        # CTR
        ctr = hindi_ctr_score(data["Title"])
        st.subheader("📰 Hindi Headline CTR Predictor")
        st.progress(ctr / 100)
        st.write(f"Estimated CTR Strength: {ctr}%")

        # CMS Suggestions
        st.subheader("📝 CMS Editor Suggestions")
        if data["Title Length"] > 60:
            st.write("• Title छोटा करें (60 characters से कम)")
        if data["Meta Characters"] > 160:
            st.write("• Meta description छोटा करें")
        if data["Image Count"] == 0:
            st.write("• खबर से संबंधित 1 image जोड़ें")
        if data["Internal Links"] < 2:
            st.write("• 2–3 internal news links जोड़ें")
