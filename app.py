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
SEO_MODE = st.sidebar.radio(
    "Select Content Type",
    ["News Article", "Blog / Evergreen"]
)

# ---------------- PREMIUM LAYOUT CSS ----------------
st.markdown("""
<style>
header[data-testid="stHeader"] {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
footer {display: none !important;}
html, body, [data-testid="stAppViewContainer"] {
background: linear-gradient(135deg, #141E30, #243B55) !important; color: white !important;}
h1, h2, h3, h4, h5, h6, p, label { color: white !important; }
.stTextArea textarea, .stTextInput input {
background: #1e2a3b !important; color: white !important;
border: 2px solid #4F81BD !important; border-radius: 12px !important;}
.stButton>button {
background: #4F81BD !important; color: white !important;
border-radius: 10px; font-size: 18px; padding: 10px 20px;}
</style>
""", unsafe_allow_html=True)

# ---------------- SAFE TEXT ----------------
def safe_get_text(tag):
    try: return tag.get_text(" ", strip=True)
    except: return ""

# ---------------- REQUEST HEADERS ----------------
REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

# ---------------- TRUSTED DOMAINS ----------------
TRUSTED_DOMAINS = [
    "bbc.com","reuters.com","ndtv.com","indiatimes.com",
    "thehindu.com","timesofindia.com","patrika.com"
]

def authority_score(url):
    domain = urlparse(url).netloc.lower()
    return 25 if any(d in domain for d in TRUSTED_DOMAINS) else 8

# ---------------- ARTICLE EXTRACTOR ----------------
def extract_article(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url
        r = requests.get(url, headers=REQ_HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text.strip() if soup.title else ""
        md = soup.find("meta", attrs={"name":"description"})
        meta = md.get("content","") if md else ""

        paras = soup.find_all("p")
        article = " ".join([safe_get_text(p) for p in paras])
        words = article.split()

        imgs = soup.find_all("img")
        anchors = soup.find_all("a")

        domain = urlparse(url).netloc.lower()
        internal = external = 0
        for a in anchors:
            href = a.get("href","")
            if not href: continue
            parsed = urlparse(href if href.startswith("http") else "https://"+domain+href)
            if parsed.netloc and parsed.netloc.lower()!=domain:
                external+=1
            else: internal+=1

        return {
            "title": title,
            "meta": meta,
            "word_count": len(words),
            "paragraph_count": len(paras),
            "img_count": len(imgs),
            "alt_with": sum(1 for i in imgs if (i.get("alt") or "").strip()),
            "internal_links": internal,
            "external_links": external,
            "avg_wps": round(len(words)/max(1,len(re.split(r"[.!?]",article))),2)
        }
    except:
        return {
            "title":"", "meta":"", "word_count":0, "paragraph_count":0,
            "img_count":0,"alt_with":0,"internal_links":0,"external_links":0,"avg_wps":0
        }

# ---------------- ONPAGE SCORE ----------------
def onpage_score(d, mode):
    score = 0
    if mode=="News Article":
        if d["word_count"]>=250: score+=15
        if d["paragraph_count"]>=4: score+=10
        if d["img_count"]>=1: score+=10
        if d["title"]: score+=10
        score+=10  # News freshness bias
    else:
        if d["word_count"]>=600: score+=20
        if d["paragraph_count"]>=8: score+=10
        if d["img_count"]>=3: score+=10
        if d["meta"]: score+=10
        if 10<=d["avg_wps"]<=20: score+=10
    return score

# ---------------- FINAL SEO SCORE ----------------
def final_score(data, url, mode):
    onpage = onpage_score(data, mode)
    authority = authority_score(url)
    final = onpage*0.55 + authority*0.25 + (20 if mode=="News Article" else 10)
    final = round(min(final,100))
    grade = "A+" if final>=85 else "A" if final>=70 else "B" if final>=55 else "C" if final>=40 else "D"
    return final, grade

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.caption("Google News + Blog SEO Compatible")

urls = st.text_area("Paste URLs (one per line)", height=200)
process = st.button("Analyze")

if process:
    rows=[]
    for url in urls.splitlines():
        if not url.strip(): continue
        data = extract_article(url)
        score, grade = final_score(data, url, SEO_MODE)
        rows.append({
            "URL":url,
            "SEO Mode":SEO_MODE,
            "SEO Score":score,
            "SEO Grade":grade,
            "Words":data["word_count"],
            "Paragraphs":data["paragraph_count"],
            "Images":data["img_count"],
            "Internal Links":data["internal_links"],
            "External Links":data["external_links"]
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    excel = BytesIO()
    df.to_excel(excel,index=False)
    st.download_button("📥 Download Report", excel.getvalue(),
        file_name="SEO_Report.xlsx")
