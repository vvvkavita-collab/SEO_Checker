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
header[data-testid="stHeader"] {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
footer {display: none !important;}
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #141E30, #243B55) !important;
    color: white !important;
}
h1, h2, h3, h4, h5, h6, p, label { color: white !important; }
.stTextArea textarea, .stTextInput input {
    background: #1e2a3b !important;
    color: white !important;
    border: 2px solid #4F81BD !important;
    border-radius: 12px !important;
}
.stButton>button {
    background: #4F81BD !important;
    color: white !important;
    border-radius: 10px;
    font-size: 18px;
    padding: 10px 20px;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SAFE GET TEXT ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# ---------------- REQUEST HEADERS ----------------
REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# ---------------- ARTICLE EXTRACTOR (FIXED LOGIC) ----------------
def extract_article(url):
    try:
        if not url.lower().startswith(("http://","https://")):
            url = "https://" + url.lstrip("/")

        r = requests.get(url, headers=REQ_HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Meta
        md = soup.find("meta", attrs={"name":"description"}) \
             or soup.find("meta", attrs={"property":"og:description"})
        meta_desc = md.get("content").strip() if md and md.get("content") else ""

        # Article container (news only)
        article = (
            soup.find("article") or
            soup.find("div", itemprop="articleBody") or
            soup.find("div", class_=re.compile("story|article|content", re.I))
        )

        if not article:
            article = soup.body

        # Paragraphs (real only)
        paras = [p for p in article.find_all("p") if safe_get_text(p)]
        paragraph_count = len(paras)

        article_text = " ".join(safe_get_text(p) for p in paras)
        article_text = re.sub(r"\s+", " ", article_text)

        words = article_text.split()
        word_count = len(words)

        sentences = re.split(r"[.!?]\s+", article_text)
        sentence_count = len([s for s in sentences if s.strip()])
        avg_words_per_sentence = round(word_count / max(1, sentence_count), 2)

        summary = ". ".join(sentences[:2]).strip()
        if summary and not summary.endswith("."):
            summary += "."

        # Headings
        h1 = [safe_get_text(h) for h in article.find_all("h1")]
        h2 = [safe_get_text(h) for h in article.find_all("h2")]

        # Images (news related only)
        imgs = []
        for img in article.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if src:
                imgs.append(img)

        img_count = len(imgs)
        alt_with = sum(1 for img in imgs if (img.get("alt") or "").strip())

        # Links
        anchors = article.find_all("a", href=True)
        domain = urlparse(url).netloc.lower()
        internal_links = 0
        external_links = 0

        for a in anchors:
            href = a.get("href").strip()
            if href.startswith(("#", "javascript:", "mailto:")):
                continue
            parsed = urlparse(href if href.startswith("http") else f"https://{domain}{href}")
            if parsed.netloc and parsed.netloc.lower() != domain:
                external_links += 1
            else:
                internal_links += 1

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
            "summary": summary[:200]
        }

    except:
        return {
            "title":"", "meta":"", "h1":[], "h2":[],
            "img_count":0, "alt_with":0,
            "internal_links":0, "external_links":0,
            "paragraph_count":0, "word_count":0,
            "avg_words_per_sentence":0,
            "summary":""
        }

# ---------------- VERDICT ----------------
def verdict(actual, ideal_min=None, ideal_max=None, ideal_exact=None):
    try:
        val = float(actual)
    except:
        return "❌ Needs Fix"
    if ideal_exact is not None:
        return "✅ Good" if val==ideal_exact else "❌ Needs Fix"
    if ideal_min is not None and ideal_max is not None:
        if ideal_min <= val <= ideal_max: return "✅ Good"
        elif val>ideal_max: return "⚠️ Excessive"
        else: return "❌ Needs Fix"
    if ideal_min is not None:
        return "✅ Good" if val>=ideal_min else "❌ Needs Fix"
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

    metrics = [
        ("Title Length Actual", len(title), "Title Length Ideal", "50–60 characters", "Title Verdict", verdict(len(title),50,60)),
        ("Meta Length Actual", len(meta), "Meta Length Ideal", "150–160 characters", "Meta Verdict", verdict(len(meta),150,160)),
        ("H1 Count Actual", h1_count, "H1 Count Ideal", "Exactly 1", "H1 Verdict", verdict(h1_count, ideal_exact=1)),
        ("H2 Count Actual", h2_count, "H2 Count Ideal", "2–5", "H2 Verdict", verdict(h2_count,2,5)),
        ("Content Length Actual", word_count, "Content Length Ideal", "600+ words", "Content Verdict", verdict(word_count,600,None)),
        ("Paragraph Count Actual", paragraph_count, "Paragraph Count Ideal", "8+ paragraphs", "Paragraph Verdict", verdict(paragraph_count,8,None)),
        ("Image Count Actual", img_count, "Image Count Ideal", "3+ images", "Image Verdict", verdict(img_count,3,None)),
        ("Alt Tags Actual", alt_with, "Alt Tags Ideal", "All images must have alt text", "Alt Tags Verdict", verdict(alt_with,ideal_exact=img_count)),
        ("Internal Links Actual", internal_links, "Internal Links Ideal", "2–5", "Internal Links Verdict", verdict(internal_links,2,5)),
        ("External Links Actual", external_links, "External Links Ideal", "2–4", "External Links Verdict", verdict(external_links,2,4)),
        ("Readability Actual", avg_wps, "Readability Ideal", "10–20 words/sentence", "Readability Verdict", verdict(avg_wps,10,20))
    ]

    score = 0
    if 50<=len(title)<=60: score+=10
    if 150<=len(meta)<=160: score+=10
    if h1_count==1: score+=8
    if 2<=h2_count<=5: score+=6
    if word_count>=600: score+=12
    if paragraph_count>=8: score+=6
    if img_count>=3: score+=8
    if img_count>0 and alt_with==img_count: score+=6
    if 2<=internal_links<=5: score+=4
    if 2<=external_links<=4: score+=4
    if 10<=avg_wps<=20: score+=8
    score=min(score,100)

    grade = "A+" if score>=90 else "A" if score>=80 else "B" if score>=65 else "C" if score>=50 else "D"
    extras = {"Summary": data["summary"][:20]}
    return score, grade, metrics, extras

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.subheader("URL Analysis → Excel Report → Actual vs Ideal + Human Verdicts")

urls_input = st.text_area("Paste URLs here", height=220)
process = st.button("Process & Create Report")

if process and urls_input.strip():
    rows=[]
    urls=list(dict.fromkeys([u.strip() for u in urls_input.splitlines() if u.strip()]))

    for url in urls:
        data = extract_article(url)
        score, grade, metrics, extras = seo_analysis_struct(data)

        row={"URL":url,"Summary":extras["Summary"],"SEO Score":score,"SEO Grade":grade}
        for a,av,i,iv,v,vv in metrics:
            row[a]=av; row[i]=iv; row[v]=vv
        rows.append(row)

    df=pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
