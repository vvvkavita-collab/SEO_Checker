import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

url = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

# ---- REAL NEWS PARAGRAPHS ONLY ----
def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(photo|file|agency|inputs|also read|read more)", text.lower()):
            continue
        paras.append(text)
    return paras

# ---- HERO / NEWS IMAGE ONLY ----
def get_real_images(article):
    images = []

    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img:
            src = img.get("src") or ""
            if src and not any(x in src.lower() for x in ["logo", "icon", "sprite", "ads"]):
                images.append(img)

    if not images:
        for img in article.find_all("img"):
            cls = " ".join(img.get("class", []))
            src = img.get("src") or ""
            if any(x in cls.lower() for x in ["featured", "post", "hero"]) and src:
                images.append(img)

    return images[:1]

# ---- INTERNAL / EXTERNAL LINKS ----
def get_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            h = a["href"]
            if h.startswith("http"):
                if domain in h:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
    return internal, external

# ---- META CLEAN ----
def clean_meta(text):
    return " ".join(text.replace("\n", " ").split()).strip()

# ---- IMPROVED SEO TITLE SHORTENER (FIXED) ----
def seo_optimized_title(title):
    """
    Returns FULL usable SEO title (no truncation)
    """
    title = clean_meta(title)

    # Remove junk brackets / extra spacing
    title = re.sub(r"\s+", " ", title)

    return title

    # Prefer natural separators
    separators = [" | ", " – ", " - ", " : ", "।"]
    for sep in separators:
        parts = title.split(sep)
        if len(parts) > 1 and len(parts[0]) <= limit:
            return parts[0].strip()

    # Fallback: cut by words, not characters
    words = title.split()
    new_title = ""
    for w in words:
        if len(new_title) + len(w) + 1 > limit:
            break
        new_title += w + " "

    return new_title.strip() + "…"

# ================= ANALYSIS =================
if analyze and url:
    try:
        soup = get_soup(url)
        domain = urlparse(url).netloc

        article = soup.find("article") or soup.find("div", class_=re.compile("content|story", re.I)) or soup

        # -------- TITLE --------
        h1_tag = soup.find("h1")
        title = h1_tag.get_text(strip=True) if h1_tag else soup.title.string.strip()
        title_len = len(title)
        seo_title = seo_optimized_title(title)

        # -------- META --------
        meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", attrs={"property": "og:description"}
        )
        meta = clean_meta(meta_tag["content"]) if meta_tag and meta_tag.get("content") else ""
        meta_chars = len(meta)

        # -------- HEADINGS --------
        h1_count = len(article.find_all("h1"))
        h2_count = len(article.find_all("h2"))

        # -------- CONTENT --------
        paragraphs = get_real_paragraphs(article)
        word_count = sum(len(p.split()) for p in paragraphs)

        # -------- IMAGES --------
        images = get_real_images(article)
        img_count = len(images)

        # -------- LINKS --------
        internal, external = get_links(article, domain)

        # ================= REPORT =================
        report = [
            ["Title Character Count", title_len, "≤ 60", "✅" if title_len <= 60 else "❌"],
            ["Suggested SEO Title", short_title, "Auto Optimized", "—"],
            ["Meta Description Characters", meta_chars, "70–160", "✅" if 70 <= meta_chars <= 160 else "❌"],
            ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "❌"],
            ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "❌"],
            ["Word Count", word_count, "250+", "✅" if word_count >= 250 else "❌"],
            ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "❌"],
            ["Internal Links", internal, "2–10", "✅" if 2 <= internal <= 10 else "❌"],
            ["External Links", external, "0–2", "✅" if external <= 2 else "❌"],
        ]

        df = pd.DataFrame(report, columns=["Metric", "Actual", "Ideal", "Verdict"])

        st.subheader("📊 SEO Audit Report")
        st.dataframe(df, use_container_width=True)

        st.subheader("✂️ Title Optimization")
        st.write("**Original Title:**", title)
        st.write("**Suggested SEO Title:**", short_title)

        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("⬇️ Download SEO Report", output.getvalue(), "seo_report.xlsx")

    except Exception as e:
        st.error("Error occurred while analyzing the page")
        st.exception(e)


