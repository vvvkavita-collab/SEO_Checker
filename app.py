import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ---------------- Streamlit Page Config ----------------
st.set_page_config(
    page_title="Advanced SEO Auditor",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

# ---------------- Custom CSS for Premium Look ----------------
st.markdown("""
<style>
header[data-testid="stHeader"], #MainMenu, footer {visibility: hidden;}
[data-testid="stDecoration"] {display: none !important;}
html, body, [data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #141E30, #243B55) !important; color: white !important;}
.stTextArea textarea, .stTextInput input {background: #1e2a3b !important; border: 2px solid #4F81BD !important; border-radius: 12px !important; color: white !important;}
.stFileUploader {background: #1e2a3b !important; color: white !important; border: 2px dashed #4F81BD !important; border-radius: 12px !important; padding: 15px;}
.stButton>button {background: #4F81BD !important; color: white !important; border-radius: 10px; padding: 10px 20px; font-size: 18px; border: none; box-shadow: 0px 4px 10px rgba(79,129,189,0.5);}
.stButton>button:hover {background: #3A6EA5 !important;}
</style>
""", unsafe_allow_html=True)

# ---------------- Safe Text Extract ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# ---------------- Extract Article Data ----------------
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
        article = ".".join([safe_get_text(p) for p in paras]).strip()
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
        sentences = re.split(r"[.!?]\s+", article)
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
            "summary": summary,
        }
    except:
        return {k: "" for k in [
            "title","meta","article","h1","h2","img_count","alt_with","internal_links",
            "external_links","paragraph_count","sentence_count","word_count",
            "avg_words_per_sentence","summary"
        ]}

# ---------------- SEO Analysis ----------------
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
    keyword_density = 0

    pairs = [
        ("Title Length Ideal", "50-60", "Title Length Actual", len(title)),
        ("Meta Length Ideal", "150-160", "Meta Length Actual", len(meta)),
        ("H1 Count Ideal", "1", "H1 Count Actual", h1_count),
        ("H2 Count Ideal", "2-5", "H2 Count Actual", h2_count),
        ("Content Length Ideal", "600+", "Content Length Actual", word_count),
        ("Paragraph Count Ideal", "8+", "Paragraph Count Actual", paragraph_count),
        ("Keyword Density Ideal", "1-2%", "Keyword Density Actual", keyword_density),
        ("Image Count Ideal", "3+", "Image Count Actual", img_count),
        ("Alt Tags Ideal", "All", "Alt Tags Actual", alt_with),
        ("Internal Links Ideal", "2-5", "Internal Links Actual", internal_links),
        ("External Links Ideal", "2-4", "External Links Actual", external_links),
        ("Readability Ideal", "10-20", "Readability Actual", avg_wps),
    ]

    score = 0
    if 50 <= len(title) <= 60: score += 10
    if 150 <= len(meta) <= 160: score += 10
    if h1_count == 1: score += 8
    if 2 <= h2_count <= 5: score += 6
    if word_count >= 600: score += 12
    if paragraph_count >= 8: score += 6
    if img_count >= 3: score += 8
    if img_count > 0 and alt_with == img_count: score += 6
    if 2 <= internal_links <= 5: score += 4
    if 2 <= external_links <= 4: score += 4
    if 10 <= avg_wps <= 20: score += 8

    score = min(score, 100)
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
    predicted_rating = round(score / 10, 1)
    extras = {"Summary": data["summary"]}

    return score, grade, predicted_rating, pairs, extras

# ---------------- Excel Formatter ----------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb["Audit"]
    ws.sheet_view.showGridLines = False
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    red_fill = PatternFill("solid", fgColor="FF7F7F")
    thin_border = Border(
        left=Side(style="thin", color="4F81BD"),
        right=Side(style="thin", color="4F81BD"),
        top=Side(style="thin", color="4F81BD"),
        bottom=Side(style="thin", color="4F81BD"),
    )
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align

    headers = [c.value for c in ws[1]]
    def num(v):
        try: return float(v)
        except: return None
    for row in ws.iter_rows(min_row=2):
        lookup = {headers[i]: row[i] for i in range(len(headers))}
        for h, c in lookup.items():
            if h.endswith("Actual"):
                val = num(c.value)
                if val is None: continue
                if ("Title" in h and not 50 <= val <= 60) or \
                   ("Meta" in h and not 150 <= val <= 160) or \
                   ("H1" in h and val != 1) or \
                   ("H2" in h and not 2 <= val <= 5) or \
                   ("Content" in h and val < 600) or \
                   ("Paragraph" in h and val < 8) or \
                   ("Image" in h and val < 3) or \
                   ("Alt" in h and val < num(lookup.get("Image Count Actual",0))) or \
                   ("Internal" in h and not 2 <= val <=5) or \
                   ("External" in h and not 2 <= val <=4) or \
                   ("Readability" in h and not 10 <= val <=20):
                    c.fill = red_fill
            c.border = thin_border
            c.alignment = center_align

    # Column width
    for col in ws.columns:
        col_letter = col[0].column_letter
        if ws[col_letter + "1"].value == "Summary":
            ws.column_dimensions[col_letter].width = 20
        else:
            ws.column_dimensions[col_letter].width = 22

    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.subheader("URL Analysis → Excel Report → SEO Guidelines (Auto Generated)")

uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt","csv","xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)

# Merge uploaded file URLs with pasted URLs
merged_urls = []
if uploaded:
    try:
        if uploaded.type == "text/plain":
            merged_urls = [l.strip() for l in uploaded.read().decode("utf-8", errors="ignore").splitlines() if l.strip()]
        elif uploaded.type == "text/csv":
            df = pd.read_csv(uploaded, header=None)
            merged_urls = df.iloc[:,0].astype(str).str.strip().tolist()
        else:
            df = pd.read_excel(uploaded, header=None)
            merged_urls = df.iloc[:,0].astype(str).str.strip().tolist()
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")

# Combine pasted + uploaded
all_urls = [u.strip() for u in urls_input.splitlines() if u.strip()] + merged_urls
urls_input = "\n".join(all_urls)  # display merged URLs in textarea

process = st.button("Process & Create Excel")

if process:
    if not all_urls:
        st.error("Please paste or upload URLs to process.")
    else:
        rows = []
        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(all_urls, start=1):
            status.text(f"Processing {i}/{len(all_urls)} : {url}")
            data = extract_article(url)
            score, grade, predicted, pairs, extras = seo_analysis_struct(data)

            row = {
                "URL": url,
                "Title": data["title"],
                "Summary": extras["Summary"],
                "SEO Score": score,
                "SEO Grade": grade,
                "Predicted Public Rating": predicted,
            }
            for ideal, ideal_val, actual, actual_val in pairs:
                row[ideal] = ideal_val
                row[actual] = actual_val
            rows.append(row)
            progress.progress(int((i / len(all_urls)) * 100))

        df = pd.DataFrame(rows)

        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")
            wb_in_writer = writer.book
            ws_g = wb_in_writer.create_sheet("SEO Guidelines")
            ws_g.append(["Parameter", "Meaning / Purpose", "Ideal Range", "Why Important"])
            guidelines = [
                ("Title Length", "Main headline", "50–60 chars", "CTR + Ranking"),
                ("Meta Description", "Search snippet text", "150–160 chars", "CTR improvement"),
                ("H1 Count", "Main heading", "1", "Topic clarity"),
                ("H2 Count", "Subheadings", "2–5", "Readability + SEO"),
                ("Content Length", "Total words", "600+", "Depth of content"),
                ("Paragraph Count", "Sections", "8+", "User experience"),
                ("Keyword Density", "Keyword %", "1–2%", "Avoid stuffing"),
                ("Images", "Visuals", "3+", "Engagement"),
                ("Alt Tags", "Image alt text", "All", "Image SEO"),
                ("Internal Links", "Site links", "2–5", "Ranking"),
                ("External Links", "Trusted links", "2–4", "Credibility"),
                ("Readability", "Words/sentence", "10–20", "Better retention"),
            ]
            for r in guidelines:
                ws_g.append(r)
            for col in ws_g.columns:
                ws_g.column_dimensions[col[0].column_letter].width = 25

        final_bytes = apply_excel_formatting(out.getvalue())

        st.success("🎉 Excel created successfully!")
        st.download_button(
            "Download SEO Audit Excel",
            data=final_bytes,
            file_name="SEO_Audit_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
