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

# ---------------- PREMIUM CSS ----------------
st.markdown("""
<style>
header[data-testid="stHeader"]{visibility:hidden}
#MainMenu{visibility:hidden}
footer{display:none}
html,body,[data-testid="stAppViewContainer"]{
background:linear-gradient(135deg,#141E30,#243B55);
color:white}
h1,h2,h3,h4,h5,h6,p,label{color:white}
</style>
""", unsafe_allow_html=True)

# ---------------- SAFE TEXT ----------------
def txt(tag):
    return tag.get_text(" ", strip=True) if tag else ""

# ---------------- HEADERS ----------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 Chrome/120",
    "Accept-Language": "en-US,en;q=0.9"
}

# ======================================================
# 🔥 FIXED ARTICLE EXTRACTOR (PATRiKA SAFE)
# ======================================================
def extract_article(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url

        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # -------- META --------
        title = soup.title.string.strip() if soup.title else ""
        meta = soup.find("meta", {"name": "description"}) \
               or soup.find("meta", {"property": "og:description"})
        meta_desc = meta["content"].strip() if meta and meta.get("content") else ""

        # -------- H1 / H2 --------
        h1 = [txt(h) for h in soup.find_all("h1")]
        h2 = [txt(h) for h in soup.find_all("h2")]

        # -------- ARTICLE BODY (Patrika Safe) --------
        container = (
            soup.find("div", class_=re.compile("story|detail|content", re.I))
            or soup.find("article")
            or soup.body
        )

        # -------- PARAGRAPHS --------
        paras = []
        for p in container.find_all("p"):
            t = txt(p)
            if len(t) > 20:   # sirf real news paragraph
                paras.append(t)
        paragraph_count = len(paras)
        article_text = " ".join(paras)

        # -------- IMAGES (ONLY NEWS IMAGES) --------
        imgs = []
        for im in container.find_all("img"):
            src = im.get("src","")
            if src and "ad" not in src.lower():
                imgs.append(im)

        img_count = len(imgs)
        alt_with = sum(1 for i in imgs if (i.get("alt") or "").strip())

        # -------- LINKS --------
        domain = urlparse(url).netloc.lower()
        internal_links = external_links = 0

        for a in container.find_all("a"):
            href = a.get("href","").strip()
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue
            p = urlparse(href if href.startswith("http") else f"https://{domain}{href}")
            if p.netloc and p.netloc != domain:
                external_links += 1
            else:
                internal_links += 1

        # -------- WORD / READABILITY --------
        words = article_text.split()
        word_count = len(words)
        sentences = re.split(r"[.!?]", article_text)
        sentence_count = len([s for s in sentences if s.strip()])
        avg_wps = round(word_count / max(1, sentence_count), 2)

        summary = " ".join(sentences[:2]).strip()[:200]

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
            "avg_words_per_sentence": avg_wps,
            "summary": summary
        }

    except Exception as e:
        return {
            "title":"", "meta":"", "h1":[], "h2":[],
            "img_count":0, "alt_with":0,
            "internal_links":0, "external_links":0,
            "paragraph_count":0, "word_count":0,
            "avg_words_per_sentence":0, "summary":""
        }

# ---------------- VERDICT ----------------
def verdict(v, mi=None, ma=None, ex=None):
    try: v=float(v)
    except: return "❌ Needs Fix"
    if ex is not None: return "✅ Good" if v==ex else "❌ Needs Fix"
    if mi and ma: return "✅ Good" if mi<=v<=ma else "❌ Needs Fix"
    if mi: return "✅ Good" if v>=mi else "❌ Needs Fix"
    return "❌ Needs Fix"

# ---------------- SEO STRUCT ----------------
def seo_analysis(data):
    metrics=[
        ("Title Length Actual",len(data["title"]),"Title Ideal","50–60","Verdict",verdict(len(data["title"]),50,60)),
        ("Meta Length Actual",len(data["meta"]),"Meta Ideal","150–160","Verdict",verdict(len(data["meta"]),150,160)),
        ("H1 Count Actual",len(data["h1"]),"H1 Ideal","1","Verdict",verdict(len(data["h1"]),ex=1)),
        ("Paragraph Count Actual",data["paragraph_count"],"Paragraph Ideal","8+","Verdict",verdict(data["paragraph_count"],8)),
        ("Image Count Actual",data["img_count"],"Image Ideal","3+","Verdict",verdict(data["img_count"],3)),
        ("Alt Tags Actual",data["alt_with"],"Alt Ideal","All","Verdict",verdict(data["alt_with"],ex=data["img_count"])),
        ("Internal Links Actual",data["internal_links"],"Internal Ideal","2–5","Verdict",verdict(data["internal_links"],2,5)),
        ("External Links Actual",data["external_links"],"External Ideal","2–4","Verdict",verdict(data["external_links"],2,4)),
    ]
    return metrics

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – FINAL FIXED VERSION")

urls = st.text_area("Paste URLs", height=200)

if st.button("Run SEO Audit"):
    rows=[]
    for url in urls.splitlines():
        if not url.strip(): continue
        data = extract_article(url.strip())
        row={"URL":url.strip(),"Summary":data["summary"]}
        for a,av,i,iv,vh,v in seo_analysis(data):
            row[a]=av
            row[i]=iv
            row[vh]=v
        rows.append(row)

    df=pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    out=BytesIO()
    df.to_excel(out,index=False)
    st.download_button("⬇ Download Excel",out.getvalue(),"SEO_Report.xlsx")
