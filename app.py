import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="Advanced SEO Auditor – News & Blog",
    layout="wide"
)

st.title("📰 Advanced SEO Auditor – News & Blog")

# ================== SIDEBAR ==================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio(
    "Select Content Type",
    ["News Article", "Blog / Evergreen"]
)

# ================== INPUT ==================
url = st.text_input("Paste News / Blog URL")

analyze = st.button("Analyze")

# ================== HELPER FUNCTIONS ==================

def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(url, headers=headers, timeout=15)
    return BeautifulSoup(r.text, "html.parser")

def clean_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)

        if len(text) < 60:
            continue

        if any(x in text.lower() for x in [
            "photo", "file photo", "agency", "inputs", "social media"
        ]):
            continue

        paras.append(text)
    return paras

def clean_images(article):
    images = []
    for img in article.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        if "svg" in src.lower():
            continue
        if img.get("width") or img.get("height"):
            images.append(img)
    return images

def clean_meta(meta):
    meta = meta.replace("\n", " ")
    meta = " ".join(meta.split())
    return meta.strip()

def clean_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http"):
                if domain in href:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
    return internal, external

# ================== GOOGLE DISCOVER SCORE ==================
def discover_score(d):
    score = 0
    score += 20 if d["Word Count"] >= 300 else 10
    score += 20 if d["Image Count"] >= 1 else 0
    score += 15 if d["Title Length"] <= 70 else 0
    score += 15 if d["Meta Length"] <= 160 else 0
    score += 15 if d["H2 Count"] >= 2 else 0
    score += 15 if d["Paragraph Count"] >= 4 else 0
    return score

# ================== HINDI CTR PREDICTOR ==================
def hindi_ctr_predictor(title):
    score = 0
    power_words = [
        "बड़ा", "खुलासा", "जानिए", "तस्वीरें", "वीडियो",
        "सच", "क्या", "क्यों", "कैसे", "अब"
    ]
    score += sum(1 for w in power_words if w in title) * 5
    score += 20 if 40 <= len(title) <= 65 else 10
    score += 10 if "?" in title else 0
    return min(score, 100)

# ================== CMS SUGGESTION ==================
def cms_suggestions(d):
    tips = []
    if d["Paragraph Count"] < 4:
        tips.append("कम से कम 4 मजबूत पैराग्राफ जोड़ें")
    if d["Image Count"] < 1:
        tips.append("एक high-quality news image ज़रूर जोड़ें")
    if d["Meta Length"] > 160:
        tips.append("Meta description 160 characters से कम रखें")
    if d["H2 Count"] < 2:
        tips.append("कम से कम 2 H2 sub-headings जोड़ें")
    if d["Internal Links"] < 2:
        tips.append("2–5 internal links जोड़ें")
    if not tips:
        tips.append("Article CMS-ready है 👍")
    return " | ".join(tips)

# ================== MAIN ANALYSIS ==================
if analyze and url:
    try:
        soup = get_soup(url)
        domain = urlparse(url).netloc

        article = soup.find("article") or soup

        title = soup.find("h1").get_text(strip=True)
        title_length = len(title)

        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta = clean_meta(meta_tag["content"]) if meta_tag else ""
        meta_length = len(meta)

        paragraphs = clean_paragraphs(article)
        images = clean_images(article)
        internal_links, external_links = clean_links(article, domain)

        h2_count = len(article.find_all("h2"))

        data = {
            "URL": url,
            "Title": title,
            "Title Length": title_length,
            "Word Count": sum(len(p.split()) for p in paragraphs),
            "Paragraph Count": len(paragraphs),
            "Image Count": len(images),
            "Internal Links": internal_links,
            "External Links": external_links,
            "Meta Length": meta_length,
            "H2 Count": h2_count
        }

        df = pd.DataFrame([
            ["Word Count", data["Word Count"], "250+", "✅" if data["Word Count"] >= 250 else "❌"],
            ["Paragraph Count", data["Paragraph Count"], "4+", "✅" if data["Paragraph Count"] >= 4 else "❌"],
            ["Image Count", data["Image Count"], "1+", "✅" if data["Image Count"] >= 1 else "❌"],
            ["Internal Links", data["Internal Links"], "2–10", "✅" if 2 <= data["Internal Links"] <= 10 else "❌"],
            ["External Links", data["External Links"], "0–2", "✅" if data["External Links"] <= 2 else "❌"],
            ["Meta Length", data["Meta Length"], "70–160", "✅" if 70 <= data["Meta Length"] <= 160 else "❌"],
            ["Title Length", data["Title Length"], "50–60", "✅" if 50 <= data["Title Length"] <= 60 else "❌"],
            ["H2 Count", data["H2 Count"], "2+", "✅" if data["H2 Count"] >= 2 else "❌"]
        ], columns=["Metric", "Actual", "Ideal", "Verdict"])

        st.subheader("SEO Audit Report")
        st.dataframe(df, use_container_width=True)

        # EXTRA PANELS
        st.subheader("📈 Google Discover Friendly Score")
        discover = discover_score(data)
        st.progress(discover / 100)
        st.write(f"Score: **{discover}/100**")

        st.subheader("🎯 Hindi Headline CTR Prediction")
        ctr = hindi_ctr_predictor(title)
        st.progress(ctr / 100)
        st.write(f"Estimated CTR Strength: **{ctr}%**")

        st.subheader("🛠 CMS Editor Suggestions")
        st.info(cms_suggestions(data))

        # DOWNLOAD
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button(
            "⬇ Download SEO Report",
            data=output.getvalue(),
            file_name="seo_audit_report.xlsx"
        )

    except Exception as e:
        st.error("Error occurred while analyzing URL")
        st.exception(e)
