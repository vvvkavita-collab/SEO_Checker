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
html, body, [data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #141E30, #243B55) !important; color: white !important;}
h1, h2, h3, h4, h5, h6, p, label { color: white !important; }
.stTextArea textarea, .stTextInput input {background: #1e2a3b !important; color: white !important; border: 2px solid #4F81BD !important; border-radius: 12px !important;}
.stButton>button {background: #4F81BD !important; color: white !important; border-radius: 10px; font-size: 18px; padding: 10px 20px; border: none; box-shadow: 0px 4px 10px rgba(79,129,189,0.5);}
.stButton>button:hover { background: #3A6EA5 !important; }
.stFileUploader {background: #1e2a3b !important; color: white !important; border: 2px dashed #4F81BD !important; border-radius: 12px; padding: 15px;}
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

# ---------------- ARTICLE EXTRACTOR (MAIN CONTENT ONLY) ----------------
def extract_article(url):
    try:
        if not url.lower().startswith(("http://","https://")):
            url = "https://" + url.lstrip("/")

        r = requests.get(url, headers=REQ_HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # ---------------- TITLE (H1) ----------------
        h1_tag = soup.find("h1")
        h1_text = safe_get_text(h1_tag) if h1_tag else ""

        # ---------------- MAIN ARTICLE CONTAINER ----------------
        article_container = (
            soup.find("section", {"class": re.compile(r"article|story|content", re.I)}) or
            soup.find("div", {"role":"main"}) or
            soup.find("article") or
            soup.body
        )

        # ---------------- PARAGRAPHS ----------------
        paras = article_container.find_all("p") if article_container else []
        # Count only non-empty paragraphs
        paragraph_count = len([p for p in paras if safe_get_text(p).strip()])
        article_text = " ".join([safe_get_text(p) for p in paras])

        # ---------------- IMAGES ----------------
        imgs = []
        if article_container:
            for im in article_container.find_all("img"):
                # ignore hidden images or 0x0
                style = im.get("style","")
                width = int(im.get("width") or 0)
                height = int(im.get("height") or 0)
                if "display:none" not in style.lower() and width>0 and height>0:
                    imgs.append(im)
        img_count = len(imgs)
        alt_with = sum(1 for im in imgs if (im.get("alt") or "").strip())

        # ---------------- LINKS ----------------
        anchors = article_container.find_all("a") if article_container else []
        domain = urlparse(url).netloc.lower()
        internal_links = 0
        external_links = 0
        for a in anchors:
            href = a.get("href")
            if not href or href.startswith(("#","mailto:")):
                continue
            full = href if href.startswith(("http://","https://")) else f"https://{domain}{href}"
            net = urlparse(full).netloc.lower()
            if net != domain:
                external_links += 1
            else:
                internal_links += 1

        # ---------------- WORDS & SENTENCE ----------------
        sentences = re.split(r"[.!?]\s+", article_text)
        sentence_count = len([s for s in sentences if s.strip()])
        words = article_text.split()
        word_count = len(words)
        avg_words_per_sentence = round(word_count / max(1,sentence_count),2)

        summary = ""
        if sentence_count >= 1:
            summary = ". ".join([s.strip() for s in sentences[:2]])
            if summary and not summary.endswith("."):
                summary += "."

        return {
            "title": h1_text,
            "paragraph_count": paragraph_count,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal_links,
            "external_links": external_links,
            "word_count": word_count,
            "avg_words_per_sentence": avg_words_per_sentence,
            "summary": summary[:200]
        }
    except:
        return {
            "title":"",
            "paragraph_count":0,
            "img_count":0,
            "alt_with":0,
            "internal_links":0,
            "external_links":0,
            "word_count":0,
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
    word_count = data["word_count"]
    paragraph_count = data["paragraph_count"]
    img_count = data["img_count"]
    alt_with = data["alt_with"]
    internal_links = data["internal_links"]
    external_links = data["external_links"]
    avg_wps = data["avg_words_per_sentence"]

    h1_count = 1 if title else 0
    h2_count = 0  # can enhance later if needed

    metrics = [
        ("Title Length Actual", len(title), "Title Length Ideal", "50–60 characters", "Title Verdict", verdict(len(title),50,60)),
        ("H1 Count Actual", h1_count, "H1 Count Ideal", "Exactly 1", "H1 Verdict", verdict(h1_count, ideal_exact=1)),
        ("Content Length Actual", word_count, "Content Length Ideal", "600+ words", "Content Verdict", verdict(word_count,600,None)),
        ("Paragraph Count Actual", paragraph_count, "Paragraph Count Ideal", "8+ paragraphs", "Paragraph Verdict", verdict(paragraph_count,8,None)),
        ("Image Count Actual", img_count, "Image Count Ideal", "3+ images", "Image Verdict", verdict(img_count,3,None)),
        ("Alt Tags Actual", alt_with, "Alt Tags Ideal", "All images must have alt text", "Alt Tags Verdict", verdict(alt_with, ideal_exact=img_count)),
        ("Internal Links Actual", internal_links, "Internal Links Ideal", "2–5", "Internal Links Verdict", verdict(internal_links,2,5)),
        ("External Links Actual", external_links, "External Links Ideal", "2–4", "External Links Verdict", verdict(external_links,2,4)),
        ("Readability Actual", avg_wps, "Readability Ideal", "10–20 words/sentence", "Readability Verdict", verdict(avg_wps,10,20))
    ]

    score = 0
    if 50<=len(title)<=60: score+=10
    if h1_count==1: score+=8
    if word_count>=600: score+=12
    if paragraph_count>=8: score+=6
    if img_count>=3: score+=8
    if img_count>0 and alt_with==img_count: score+=6
    if 2<=internal_links<=5: score+=4
    if 2<=external_links<=4: score+=4
    if 10<=avg_wps<=20: score+=8
    score = min(score,100)
    if score>=90: grade="A+"
    elif score>=80: grade="A"
    elif score>=65: grade="B"
    elif score>=50: grade="C"
    else: grade="D"

    extras = {"Summary": data["summary"]}
    return score, grade, metrics, extras

# ---------------- EXCEL FORMATTING ----------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    center_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(left=Side(style="thin", color="4F81BD"),
                         right=Side(style="thin", color="4F81BD"),
                         top=Side(style="thin", color="4F81BD"),
                         bottom=Side(style="thin", color="4F81BD"))
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    red_fill = PatternFill("solid", fgColor="FF7F7F")

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        ws.sheet_view.showGridLines = False
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_wrap
            cell.border = thin_border
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = center_wrap
                cell.border = thin_border
        # Column widths
        for col in ws.columns:
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width=22

    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.subheader("URL Analysis → Excel Report → Actual vs Ideal + Human Verdicts")

uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt","csv","xlsx"])
urls_input = st.text_area("Paste URLs here", height=220)

process = st.button("Process & Create Report")

if process:
    urls = list(set([u.strip() for u in urls_input.splitlines() if u.strip()]))
    rows=[]
    progress = st.progress(0)
    status = st.empty()

    for i,url in enumerate(urls,start=1):
        status.text(f"Processing {i}/{len(urls)} : {url}")
        data = extract_article(url)
        score, grade, metrics, extras = seo_analysis_struct(data)

        row = {"URL":url,"Summary":extras["Summary"],"SEO Score":score,"SEO Grade":grade}
        for actual_h, actual_v, ideal_h, ideal_v, verdict_h, verdict_v in metrics:
            row[actual_h]=actual_v
            row[ideal_h]=ideal_v
            row[verdict_h]=verdict_v
        rows.append(row)
        progress.progress(int((i/len(urls))*100))

    df=pd.DataFrame(rows)
    st.success("✅ SEO Report generated successfully!")
    st.dataframe(df, use_container_width=True)

    excel_bytes = BytesIO()
    with pd.ExcelWriter(excel_bytes, engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="Audit")
    formatted_bytes = apply_excel_formatting(excel_bytes.getvalue())

    st.download_button(
        label="📥 Download Styled SEO Report",
        data=formatted_bytes,
        file_name="SEO_Audit_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
