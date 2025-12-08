import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# -----------------------------
# SAFE GET TEXT
# -----------------------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# -----------------------------
# ARTICLE EXTRACTOR
# -----------------------------
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
        article = " ".join([safe_get_text(p) for p in paras]).strip()
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
        sentences = re.split(r'[.!?]\s+', article)
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
            "summary": summary
        }
    except:
        return {
            "title": "", "meta": "", "article": "", "h1": [], "h2": [],
            "img_count": 0, "alt_with": 0, "internal_links": 0, "external_links": 0,
            "paragraph_count": 0, "sentence_count": 0, "word_count": 0,
            "avg_words_per_sentence": 0, "summary": ""
        }

# -----------------------------
# STREAMLIT UI STYLING
# -----------------------------
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide", page_icon="🔍")

# Gradient background and card style
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e0f7fa, #b2ebf2);
}
.stButton>button {
    background-color: #007acc;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 0.5em 1.5em;
}
.stTextArea>div>textarea {
    border: 2px solid #007acc;
    border-radius: 10px;
}
.stFileUploader>div {
    border: 2px solid #007acc;
    border-radius: 10px;
    padding: 10px;
    background-color: #ffffff90;
}
.stDataFrame th {
    background-color: #007acc;
    color: white;
    text-align: center;
}
.stDataFrame td {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("🔍 Advanced SEO Auditor")
st.markdown("Upload URLs or paste manually. Tool crawls pages & generates Excel with SEO scoring & red-flag highlights.")

uploaded = st.file_uploader("Upload URL file (txt/csv/xlsx)", type=["txt","csv","xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)

# Load uploaded file
try:
    if uploaded:
        if uploaded.name.endswith(".txt"):
            urls = uploaded.read().decode("utf-8").splitlines()
        elif uploaded.name.endswith(".csv"):
            urls = pd.read_csv(uploaded, header=None)[0].dropna().tolist()
        else:
            urls = pd.read_excel(uploaded, header=None)[0].dropna().tolist()
        urls_input = "\n".join([u.strip() for u in urls if u.strip()])
        st.success(f"Loaded {len(urls)} URLs.")
except Exception as e:
    st.error(f"Error reading file: {e}")

process_btn = st.button("Process & Create Excel")

# -----------------------------
# PROCESSING
# -----------------------------
if process_btn:
    raw = urls_input.strip()
    if not raw:
        st.error("No URLs entered.")
    else:
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        rows = []
        progress = st.progress(0)
        status = st.empty()
        for i, url in enumerate(urls, start=1):
            status.text(f"Processing {i}/{len(urls)}: {url}")
            data = extract_article(url)
            # Basic row
            row = {
                "URL": data["title"][:20],
                "Title": data["title"][:20],
                "Summary": data["summary"][:20],
                "Word Count": data["word_count"],
                "H1 Count": len(data["h1"]),
                "H2 Count": len(data["h2"]),
                "Images": data["img_count"]
            }
            rows.append(row)
            progress.progress(int(i / len(urls) * 100))
        df = pd.DataFrame(rows)
        st.subheader("SEO Analysis Preview")
        st.dataframe(df, use_container_width=True)

        # Excel download
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")
        out.seek(0)
        st.download_button(
            "📥 Download Excel",
            data=out,
            file_name="seo_audit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
