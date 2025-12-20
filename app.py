import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO

st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

url = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    return BeautifulSoup(r.text, "html.parser")

def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)

        if len(text) < 80:
            continue
        if any(x in text.lower() for x in ["photo", "file", "agency", "inputs"]):
            continue

        paras.append(text)
    return paras

def get_real_images(article):
    imgs = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            imgs.append(img)
    return imgs

def get_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            h = a["href"]
            if h.startswith("http"):
                external += 0 if domain in h else 1
                internal += 1 if domain in h else 0
            else:
                internal += 1
    return internal, external

def clean_meta(text):
    text = text.replace("\n", " ")
    return " ".join(text.split()).strip()

# ================= ANALYSIS =================
if analyze and url:
    try:
        soup = get_soup(url)
        domain = urlparse(url).netloc
        article = soup.find("article") or soup

        title = soup.find("h1").get_text(strip=True)
        title_len = len(title)

        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta = clean_meta(meta_tag["content"]) if meta_tag else ""
        meta_chars = len(meta)

        h1_count = len(article.find_all("h1"))
        h2_count = len(article.find_all("h2"))

        paragraphs = get_real_paragraphs(article)
        word_count = sum(len(p.split()) for p in paragraphs)

        images = get_real_images(article)
        img_count = len(images)

        internal, external = get_links(article, domain)

        report = [
            ["Title Length", title_len, "50–60", "✅" if 50 <= title_len <= 60 else "❌"],
            ["Meta Characters", meta_chars, "70–160", "✅" if 70 <= meta_chars <= 160 else "❌"],
            ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "❌"],
            ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "❌"],
            ["Word Count", word_count, "250+", "✅" if word_count >= 250 else "❌"],
            ["Image Count", img_count, "1+", "✅" if img_count >= 1 else "❌"],
            ["Internal Links", internal, "2–10", "✅" if 2 <= internal <= 10 else "❌"],
            ["External Links", external, "0–2", "✅" if external <= 2 else "❌"],
        ]

        df = pd.DataFrame(report, columns=["Metric", "Actual", "Ideal", "Verdict"])

        st.subheader("SEO Audit Report")
        st.dataframe(df, use_container_width=True)

        # DOWNLOAD
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("⬇ Download SEO Report", output.getvalue(), "seo_report.xlsx")

    except Exception as e:
        st.error("Error occurred")
        st.exception(e)
