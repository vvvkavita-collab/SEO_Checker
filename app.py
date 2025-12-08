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

# ----------------------------------------------------
# SAFE GET TEXT
# ----------------------------------------------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# ----------------------------------------------------
# ARTICLE EXTRACTOR
# ----------------------------------------------------
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

# ----------------------------------------------------
# KEYWORD EXTRACTOR
# ----------------------------------------------------
STOPWORDS = set("""a about above after again against all am an and any are as at be because been before being between both but by can cannot could did do does doing down during each few for from further had has have having he her here hers him his how i if in into is it its me more most my myself no nor not of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we well were what when where which while who whom why with you your yours""".split())

def extract_keywords(text, top_n=5):
    if not text: return []
    words = re.findall(r'\b[a-zA-Z\u0900-\u097F0-9]+\b', text.lower())
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    if not words: return []
    cnt = Counter(words)
    return [w for w,_ in cnt.most_common(top_n)]

# ----------------------------------------------------
# SEO ANALYSIS FUNCTION
# ----------------------------------------------------
def seo_analysis_struct(data):
    title = data["title"]
    meta = data["meta"]
    article = data["article"]
    word_count = data["word_count"]
    paragraph_count = data["paragraph_count"]
    img_count = data["img_count"]
    alt_with = data["alt_with"]
    h1_count = len(data["h1"])
    h2_count = len(data["h2"])
    internal_links = data["internal_links"]
    external_links = data["external_links"]
    avg_wps = data["avg_words_per_sentence"]
    keyword_density = 0

    pairs = [
        ("Title Length Ideal","50-60 chars","Title Length Actual",len(title)),
        ("Meta Length Ideal","150-160 chars","Meta Length Actual",len(meta)),
        ("H1 Count Ideal",1,"H1 Count Actual",h1_count),
        ("H2 Count Ideal","2-5","H2 Count Actual",h2_count),
        ("Content Length Ideal","600+","Content Length Actual",word_count),
        ("Paragraph Count Ideal","8+","Paragraph Count Actual",paragraph_count),
        ("Keyword Density Ideal (%)","1-2","Keyword Density Actual (%)",keyword_density),
        ("Image Count Ideal","3+","Image Count Actual",img_count),
        ("Alt Tags Ideal","All images","Alt Tags Actual",alt_with),
        ("Internal Links Ideal","2-5","Internal Links Actual",internal_links),
        ("External Links Ideal","2-4","External Links Actual",external_links),
        ("Readability Ideal (avg words/sent)","10-20","Readability Actual (avg words/sent)",avg_wps)
    ]

    score = 0
    if 50 <= len(title) <= 60: score += 10
    if 150 <= len(meta) <= 160: score += 10
    if h1_count == 1: score += 8
    if 2 <= h2_count <= 5: score += 6
    if word_count >= 600: score += 12
    if paragraph_count >= 8: score += 6
    if 1 <= keyword_density <= 2: score += 8
    if img_count >= 3: score += 8
    if img_count > 0 and alt_with == img_count: score += 6
    if 2 <= internal_links <= 5: score += 4
    if 2 <= external_links <= 4: score += 4
    if 10 <= avg_wps <= 20: score += 8
    score = min(score, 100)
    grade = ("A+" if score>=90 else "A" if score>=80 else "B" if score>=65 else "C" if score>=50 else "D")
    predicted_rating = round(score/10,1)
    extras = {"Summary": data["summary"]}
    return score, grade, predicted_rating, pairs, extras

# ----------------------------------------------------
# NUMERIC PARSER
# ----------------------------------------------------
def parse_numeric(val):
    try:
        if val is None: return None
        if isinstance(val,(int,float)): return float(val)
        s = str(val).strip().replace(",","")
        if s.endswith("%"): return float(s[:-1])
        m = re.search(r"[-]?\d+(\.\d+)?", s)
        return float(m.group(0)) if m else None
    except:
        return None

# ----------------------------------------------------
# COLORING FUNCTION
# ----------------------------------------------------
def apply_coloring_and_flags(workbook_bytes):
    red_fill = PatternFill(start_color="FFC7CE", fill_type="solid")
    grade_colors = {"A+": "C6EFCE","A": "E2EFDA","B": "FFF2CC","C": "FCE4D6","D": "F8CBAD"}
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb.active
    headers = [c.value for c in ws[1]]
    header_index = {h:i for i,h in enumerate(headers)}
    for row in ws.iter_rows(min_row=2):
        data = {headers[i]:row[i] for i in range(len(headers))}
        for h, idx in header_index.items():
            if "Actual" not in h: continue
            cell = row[idx]
            val = parse_numeric(cell.value)
            fail = False
            try:
                if h.lower() == "title length actual": fail = val is None or val<50 or val>60
                elif h.lower() == "meta length actual": fail = val is None or val<150 or val>160
                elif h.lower() == "h1 count actual": fail = val != 1
                elif h.lower() == "h2 count actual": fail = val<2 or val>5
                elif h.lower() == "content length actual": fail = val<600
                elif h.lower() == "paragraph count actual": fail = val<8
                elif "keyword density" in h.lower(): fail = val<1 or val>2
                elif h.lower() == "image count actual": fail = val<3
                elif h.lower() == "alt tags actual":
                    img_act = parse_numeric(data["Image Count Actual"].value)
                    fail = val<img_act
                elif h.lower() == "internal links actual": fail = val<2 or val>5
                elif h.lower() == "external links actual": fail = val<2 or val>4
                elif "readability" in h.lower(): fail = val<10 or val>20
            except: fail=False
            if fail: cell.fill=red_fill
        grade = data.get("SEO Grade").value
        score_cell = data.get("SEO Score")
        if grade in grade_colors:
            color = PatternFill(start_color=grade_colors[grade], fill_type="solid")
            data["SEO Grade"].fill = color
            score_cell.fill = color
    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ----------------------------------------------------
# EXCEL FORMATTING FUNCTION
# ----------------------------------------------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb.active
    ws.sheet_view.showGridLines=False
    header_font = Font(bold=True,color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    thin_border = Border(
        left=Side(style='thin', color='4F81BD'),
        right=Side(style='thin', color='4F81BD'),
        top=Side(style='thin', color='4F81BD'),
        bottom=Side(style='thin', color='4F81BD')
    )
    center_alignment = Alignment(horizontal="center",vertical="center",wrap_text=True)
    for row_idx,row in enumerate(ws.iter_rows(),1):
        for cell in row:
            cell.alignment=center_alignment
            cell.border=thin_border
            if row_idx==1:
                cell.font=header_font
                cell.fill=header_fill
    # Column widths
    for col_idx,col in enumerate(ws.columns,1):
        column_letter = col[0].column_letter
        if col_idx in [1,2,len(ws[1])]: # URL, Title, Summary
            max_len = max(len(str(cell.value)) for cell in col if cell.value)
            ws.column_dimensions[column_letter].width = min(20,max_len+2)
        else:
            max_len = max(len(str(cell.value)) for cell in col if cell.value)
            ws.column_dimensions[column_letter].width=max_len+2
    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ----------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide", page_icon="🔍")

# Custom CSS for background and buttons
st.markdown("""
<style>
body { background: linear-gradient(to right,#e0f7fa,#b2ebf2); }
.stButton>button { background-color:#007acc;color:white;font-weight:bold;border-radius:8px;padding:0.5em 1.5em; }
.stTextArea>div>textarea { border:2px solid #007acc;border-radius:10px; }
.stFileUploader>div { border:2px solid #007acc;border-radius:10px;padding:10px;background-color:#ffffff90; }
.stDataFrame th { background-color:#007acc;color:white;text-align:center; }
.stDataFrame td { text-align:center; }
</style>
""",unsafe_allow_html=True)

st.title("🔍 Advanced SEO Auditor")
st.write("Upload URLs or paste manually. Tool crawls pages & generates Excel with automatic SEO scoring and red-flag highlighting.")

uploaded = st.file_uploader("Upload URL file (txt/csv/xlsx)", type=["txt","csv","xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)

# Load file
try:
    if uploaded:
        if uploaded.name.endswith(".txt"):
            urls = uploaded.read().decode("utf-8").splitlines()
        elif uploaded.name.endswith(".csv"):
            urls = pd.read_csv(uploaded, header=None)[0].dropna().tolist()
        else:
            urls = pd.read_excel(uploaded, header=None)[0].dropna().tolist()
        urls_input="\n".join([u.strip() for u in urls if u.strip()])
        st.success(f"Loaded {len(urls)} URLs.")
except Exception as e:
    st.error(f"Error reading file: {e}")

process_btn=st.button("Process & Create Excel")

if process_btn:
    raw = urls_input.strip()
    if not raw: st.error("No URLs entered.")
    else:
        urls=[u.strip() for u in raw.splitlines() if u.strip()]
        rows=[]
        pairs_reference=None
        progress=st.progress(0)
        status=st.empty()
        for i,url in enumerate(urls,start=1):
            status.text(f"Processing {i}/{len(urls)}: {url}")
            data=extract_article(url)
            score, grade, predicted, pairs, extras=seo_analysis_struct(data)
            if pairs_reference is None: pairs_reference=pairs
            row={
                "URL": url,
                "Title": data["title"],
                "Summary": extras["Summary"],
                "SEO Score": score,
                "SEO Grade": grade,
                "Overall Score": score,
                "Predicted Public Rating": predicted
            }
            for ideal_col, ideal_val, actual_col, actual_val in pairs_reference:
                row[ideal_col]=ideal_val
                row[actual_col]=actual_val
            rows.append(row)
            progress.progress(int(i/len(urls)*100))
        df=pd.DataFrame(rows)
        out=BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer,index=False,sheet_name="Audit")
        raw_bytes=out.getvalue()
        formatted_bytes=apply_excel_formatting(raw_bytes)
        try:
            colored=apply_coloring_and_flags(formatted_bytes)
            st.success("Excel created successfully with formatting & color flags.")
            st.download_button(
                "Download SEO Audit (Colored)",
                data=colored,
                file_name="seo_audit_colored.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except:
            st.warning("Coloring failed — providing formatted plain Excel.")
            st.download_button(
                "Download SEO Audit (Plain Formatted)",
                data=formatted_bytes,
                file_name="seo_audit_formatted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
