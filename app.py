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

        # ---------------- FOCUS ONLY ON MAIN ARTICLE ----------------
        article_container = soup.find("div", {"class": re.compile(r"article-content|content|story|entry", re.I)}) \
                           or soup.find("article") \
                           or soup.find("div", {"id": re.compile(r"article|content|story", re.I)})
        if not article_container:
            article_container = soup.body  # fallback to whole body if no article container

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        md = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
        meta_desc = md.get("content").strip() if md and md.get("content") else ""

        paras = article_container.find_all("p")
        article_text = " ".join([safe_get_text(p) for p in paras])
        article_text = re.sub(r"\s+", " ", article_text)

        h1 = [safe_get_text(t) for t in article_container.find_all("h1")]
        h2 = [safe_get_text(t) for t in article_container.find_all("h2")]

        imgs = article_container.find_all("img")
        img_count = len(imgs)
        alt_with = sum(1 for im in imgs if (im.get("alt") or "").strip())

        anchors = article_container.find_all("a")
        internal_links = 0
        external_links = 0
        domain = urlparse(url).netloc.lower()
        for a in anchors:
            href = a.get("href") or ""
            if href.startswith("#") or href.startswith("mailto:") or href.strip() == "":
                continue
            parsed = urlparse(href if href.startswith(("http://","https://")) else "https://" + domain + href)
            if parsed.netloc and parsed.netloc.lower() != domain:
                external_links += 1
            else:
                internal_links += 1

        paragraph_count = len([p for p in paras if safe_get_text(p)])
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
            "summary": summary[:20]
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

    # Scoring
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
    score = min(score,100)
    # Grade calculation fix
    if score>=90: grade="A+"
    elif score>=80: grade="A"
    elif score>=65: grade="B"
    elif score>=50: grade="C"
    else: grade="D"

    extras = {"Summary": (data["summary"] or "")[:20]}
    return score, grade, metrics, extras

# ---------------- COLUMN GUIDE ----------------
def get_column_guide_df():
    data = [
        ("Column Name","Meaning","Ideal","SEO Impact"),
        ("SEO Score","Overall SEO performance score","80+","Higher score = better ranking"),
        ("SEO Grade","Grade based on SEO Score","A/A+","Quick quality indicator"),
        ("Title Length Actual","Number of characters in page title","50–60 characters","Too short/long reduces CTR"),
        ("Meta Length Actual","Meta description length","150–160 characters","Improves click-through rate"),
        ("H1 Count Actual","Total H1 headings","Exactly 1","Multiple H1s confuse search engines"),
        ("H2 Count Actual","Number of H2 subheadings","2–5","Helps content structure & readability"),
        ("Content Length Actual","Total words in main content","600+ words","Longer content ranks better"),
        ("Paragraph Count Actual","Number of paragraphs","8+","Improves readability"),
        ("Image Count Actual","Total images","3+ images","Images increase engagement"),
        ("Alt Tags Actual","Images having ALT text","All images","ALT tags help SEO"),
        ("Internal Links Actual","Links pointing inside website","2–5","Improves crawlability"),
        ("External Links Actual","Links pointing outside","2–4","Adds trust & credibility"),
        ("Readability Actual","Average words per sentence","10–20 words","Easier to read"),
        ("Summary","Short content preview","Clear & meaningful","Helps editors quickly")
    ]
    return pd.DataFrame(data[1:], columns=data[0])

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
        # headers
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_wrap
            cell.border = thin_border
        # data rows
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = center_wrap
                cell.border = thin_border
        # red highlight only in Audit sheet
        if sheet_name=="Audit":
            headers = [c.value for c in ws[1]]
            for row in ws.iter_rows(min_row=2):
                lookup={headers[i]:row[i] for i in range(len(headers))}
                def val(h): 
                    c=lookup.get(h)
                    return c.value if c else None
                def mark_red(h,cond): 
                    c=lookup.get(h)
                    if c and cond:
                        c.fill=red_fill

                mark_red("Title Length Actual", not(50 <= (float(val("Title Length Actual") or 0) <= 60)))
                mark_red("Meta Length Actual", not(150 <= (float(val("Meta Length Actual") or 0) <=160)))
                mark_red("H1 Count Actual",(float(val("H1 Count Actual") or 0)!=1))
                mark_red("H2 Count Actual",not(2 <= (float(val("H2 Count Actual") or 0) <=5)))
                mark_red("Content Length Actual",(float(val("Content Length Actual") or 0)<600))
                mark_red("Paragraph Count Actual",(float(val("Paragraph Count Actual") or 0)<8))
                mark_red("Image Count Actual",(float(val("Image Count Actual") or 0)<3))
                img_actual=float(val("Image Count Actual") or 0)
                alt_actual=float(val("Alt Tags Actual") or 0)
                mark_red("Alt Tags Actual",alt_actual<img_actual)
                mark_red("Internal Links Actual",not(2 <= (float(val("Internal Links Actual") or 0) <=5)))
                mark_red("External Links Actual",not(2 <= (float(val("External Links Actual") or 0) <=4)))
                mark_red("Readability Actual",not(10 <= (float(val("Readability Actual") or 0) <=20)))

            # Column widths
            for col in ws.columns:
                col_letter = col[0].column_letter
                header_val = ws[f"{col_letter}1"].value
                if header_val=="Summary": ws.column_dimensions[col_letter].width=25
                elif header_val and "Verdict" in str(header_val): ws.column_dimensions[col_letter].width=18
                elif header_val and "Ideal" in str(header_val): ws.column_dimensions[col_letter].width=30
                else: ws.column_dimensions[col_letter].width=22

    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.subheader("URL Analysis → Excel Report → Actual vs Ideal + Human Verdicts")

if "merged_urls" not in st.session_state: st.session_state.merged_urls=""

uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt","csv","xlsx"])
urls_input = st.text_area("Paste URLs here", value=st.session_state.merged_urls, height=220)

if uploaded is not None:
    try:
        if uploaded.type=="text/plain":
            content = uploaded.read().decode("utf-8", errors="ignore")
            uploaded_urls = "\n".join([l.strip() for l in content.splitlines() if l.strip()])
        elif uploaded.type=="text/csv":
            df_u = pd.read_csv(uploaded, header=None)
            uploaded_urls = "\n".join(df_u.iloc[:,0].astype(str).str.strip())
        else:
            df_u = pd.read_excel(uploaded, header=None)
            uploaded_urls = "\n".join(df_u.iloc[:,0].astype(str).str.strip())
        existing = urls_input.strip()
        st.session_state.merged_urls = (existing+"\n"+uploaded_urls).strip() if existing else uploaded_urls
        urls_input = st.session_state.merged_urls
    except Exception as e: st.error(f"Failed to read uploaded file: {e}")

process = st.button("Process & Create Report")

if process:
    if not urls_input.strip(): st.error("Please paste some URLs or upload a file.")
    else:
        seen=set()
        urls=[]
        for u in urls_input.splitlines():
            u=u.strip()
            if u and u not in seen:
                seen.add(u)
                urls.append(u)

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
            get_column_guide_df().to_excel(writer,index=False,sheet_name="Column_Guide")
        formatted_bytes = apply_excel_formatting(excel_bytes.getvalue())

        st.download_button(
            label="📥 Download Styled SEO Report",
            data=formatted_bytes,
            file_name="SEO_Audit_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
