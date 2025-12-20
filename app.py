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

# ---------------- SEO MODE ----------------
st.sidebar.title("SEO Mode")
SEO_MODE = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

# ---------------- CSS ----------------
st.markdown("""
<style>
header, footer, #MainMenu {display:none;}
.good {color:#00ff88;font-weight:bold;}
.bad {color:#ff6b6b;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ---------------- SAFE TEXT ----------------
def safe_text(tag):
    try: return tag.get_text(" ", strip=True)
    except: return ""

# ---------------- REQUEST ----------------
HEADERS = {"User-Agent":"Mozilla/5.0"}

# ---------------- MAIN CONTENT EXTRACTOR ----------------
def extract_article(url):
    if not url.startswith("http"):
        url = "https://" + url

    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    # -------- TITLE & META --------
    title = soup.title.text.strip() if soup.title else ""
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md:
        meta_desc = md.get("content", "").strip()

    # -------- MAIN HEADLINE (H1) --------
    h1 = ""
    h1_tag = soup.find("h1")
    if h1_tag:
        h1 = h1_tag.get_text(strip=True)

    # -------- MAIN STORY CONTENT (CRITICAL FIX) --------
    story_box = soup.find("div", class_="storyDetail")
    story_content = None

    if story_box:
        story_content = story_box.find("div", class_="storyContent")

    if not story_content:
        return None  # agar article hi nahi mila

    # -------- PARAGRAPHS --------
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in story_content.find_all("p")
        if len(p.get_text(strip=True)) > 40
    ]

    # -------- IMAGES --------
    images = story_content.find_all("img")

    # -------- ALT TAG COUNT --------
    alt_count = sum(1 for img in images if img.get("alt"))

    # -------- HEADINGS H2 --------
    h2s = [
        h.get_text(strip=True)
        for h in story_content.find_all("h2")
    ]

    # -------- LINKS (ONLY INSIDE STORY) --------
    domain = urlparse(url).netloc
    internal = external = 0

    for a in story_content.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            if domain in href:
                internal += 1
            else:
                external += 1
        else:
            internal += 1

    # -------- WORD COUNT --------
    full_text = " ".join(paragraphs)
    words = full_text.split()

    return {
        "Title": title,
        "Title Length": len(title),
        "Meta Description": meta_desc,
        "Meta Length": len(meta_desc),
        "H1": h1,
        "H1 Length": len(h1),
        "H2 Count": len(h2s),
        "Paragraph Count": len(paragraphs),
        "Word Count": len(words),
        "Image Count": len(images),
        "Alt Tag Count": alt_count,
        "Internal Links": internal,
        "External Links": external
    }

# ---------------- IDEAL RANGES ----------------
IDEAL = {
    "News Article":{
        "Words":"250+",
        "Paragraphs":"4+",
        "Images":"1+",
        "Internal Links":"2–10",
        "External Links":"1–5"
    }
}

# ---------------- SCORE ----------------
def score_news(d):
    score=0
    score+=15 if d["word_count"]>=250 else 0
    score+=10 if d["paragraph_count"]>=4 else 0
    score+=10 if d["img_count"]>=1 else 0
    score+=10 if 2<=d["internal_links"]<=10 else 0
    score+=10 if 1<=d["external_links"]<=5 else 0
    return min(score+20,100)  # freshness bonus

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
urls = st.text_area("Paste URLs (one per line)", height=180)

if st.button("Analyze"):
    rows=[]
    for url in urls.splitlines():
        if not url.strip(): continue
        d = extract_article(url)
        score = score_news(d)
        grade = "A" if score>=80 else "B" if score>=60 else "C" if score>=40 else "D"

        rows.append({
            "URL":url,
            "SEO Score":score,
            "SEO Grade":grade,
            "Words Actual":d["word_count"],
            "Words Ideal":IDEAL["News Article"]["Words"],
            "Paragraph Actual":d["paragraph_count"],
            "Paragraph Ideal":IDEAL["News Article"]["Paragraphs"],
            "Image Actual":d["img_count"],
            "Image Ideal":IDEAL["News Article"]["Images"],
            "Internal Links Actual":d["internal_links"],
            "Internal Links Ideal":IDEAL["News Article"]["Internal Links"],
            "External Links Actual":d["external_links"],
            "External Links Ideal":IDEAL["News Article"]["External Links"]
        })

    df=pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # ---------------- EXPLANATION SHEET ----------------
    explain = pd.DataFrame([
        ["Title","Main heading of news","Google relevance & CTR"],
        ["Paragraph","Breaks content","Better readability"],
        ["Images","Visual support","Engagement + Discover"],
        ["Internal Links","Same site links","Crawl & authority"],
        ["External Links","Outside reference","Trust & credibility"]
    ], columns=["SEO Element","What it means","Why important"])

    excel = BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as w:
        df.to_excel(w,index=False,sheet_name="Audit")
        explain.to_excel(w,index=False,sheet_name="SEO_Explain")

    st.download_button("📥 Download SEO Report", excel.getvalue(),
        file_name="SEO_Audit_Report.xlsx")

