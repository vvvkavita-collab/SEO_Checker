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
/* Hide Streamlit chrome */
header[data-testid="stHeader"] {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stFooter"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
.viewerBadge_container__1QSob, .viewerBadge_link__1S137 {display: none !important;}

/* App background + text */
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #141E30, #243B55) !important;
    color: white !important;
    overflow-x: hidden;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F2027, #203A43, #2C5364);
    color: white !important;
}
h1, h2, h3, h4, h5, h6, p, span, div, label { color: white !important; }

/* Inputs */
.stTextArea textarea, .stTextInput input {
    background: #1e2a3b !important;
    border: 2px solid #4F81BD !important;
    border-radius: 12px !important;
    color: white !important;
}

/* File uploader */
.stFileUploader {
    background: #1e2a3b !important;
    color: white !important;
    border: 2px dashed #4F81BD !important;
    border-radius: 12px !important;
    padding: 15px;
}

/* Buttons */
.stButton>button {
    background: #4F81BD !important;
    color: white !important;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 18px;
    border: none;
    box-shadow: 0px 4px 10px rgba(79,129,189,0.5);
}
.stButton>button:hover { background: #3A6EA5 !important; }

/* Mobile */
@media (max-width: 768px) {
    h1 { font-size: 26px !important; text-align: center !important; }
    h2 { font-size: 20px !important; text-align: center !important; }
    p, label, span, div { font-size: 16px !important; }
    .stTextArea textarea, .stTextInput input { font-size: 15px !important; padding: 10px !important; }
    .stFileUploader { padding: 20px !important; }
    .stButton>button { width: 100% !important; font-size: 18px !important; padding: 14px !important; }
}
</style>
""", unsafe_allow_html=True)

# ---------------- SAFE GET TEXT ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except Exception:
        return ""

# ---------------- ARTICLE EXTRACTOR ----------------
def extract_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        meta_desc = md.get("content").strip() if md and md.get("content") else ""

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
            "h1": h1,
            "h2": h2,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal_links,
            "external_links": external_links,
            "paragraph_count": paragraph_count,
            "word_count": word_count,
            "avg_words_per_sentence": avg_words_per_sentence,
            "summary": summary[:20],
        }
    except Exception:
        return {
            "title": "",
            "meta": "",
            "h1": [],
            "h2": [],
            "img_count": 0,
            "alt_with": 0,
            "internal_links": 0,
            "external_links": 0,
            "paragraph_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "summary": "",
        }

# ---------------- HUMAN VERDICT ----------------
def verdict(actual, ideal_min=None, ideal_max=None, ideal_exact=None):
    try:
        val = float(actual)
    except Exception:
        return "❌ Needs Fix"
    if ideal_exact is not None:
        return "✅ Good" if val == ideal_exact else "❌ Needs Fix"
    if ideal_min is not None and ideal_max is not None:
        if ideal_min <= val <= ideal_max:
            return "✅ Good"
        elif val > ideal_max:
            return "⚠️ Excessive"
        else:
            return "❌ Needs Fix"
    if ideal_min is not None:
        return "✅ Good" if val >= ideal_min else "❌ Needs Fix"
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
        ("Title Length Actual", len(title), "Title Length Ideal", "50–60 characters", "Title Verdict", verdict(len(title), 50, 60)),
        ("Meta Length Actual", len(meta), "Meta Length Ideal", "150–160 characters", "Meta Verdict", verdict(len(meta), 150, 160)),
        ("H1 Count Actual", h1_count, "H1 Count Ideal", "Exactly 1", "H1 Verdict", verdict(h1_count, ideal_exact=1)),
        ("H2 Count Actual", h2_count, "H2 Count Ideal", "2–5", "H2 Verdict", verdict(h2_count, 2, 5)),
        ("Content Length Actual", word_count, "Content Length Ideal", "600+ words", "Content Verdict", verdict(word_count, 600, None)),
        ("Paragraph Count Actual", paragraph_count, "Paragraph Count Ideal", "8+ paragraphs", "Paragraph Verdict", verdict(paragraph_count, 8, None)),
        ("Image Count Actual", img_count, "Image Count Ideal", "3+ images", "Image Verdict", verdict(img_count, 3, None)),
        ("Alt Tags Actual", alt_with, "Alt Tags Ideal", "All images must have alt text", "Alt Tags Verdict", verdict(alt_with, ideal_exact=img_count)),
        ("Internal Links Actual", internal_links, "Internal Links Ideal", "2–5", "Internal Links Verdict", verdict(internal_links, 2, 5)),
        ("External Links Actual", external_links, "External Links Ideal", "2–4", "External Links Verdict", verdict(external_links, 2, 4)),
        ("Readability Actual", avg_wps, "Readability Ideal", "10–20 words/sentence", "Readability Verdict", verdict(avg_wps, 10, 20)),
    ]

    # Scoring
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
    extras = {"Summary": (data["summary"] or "")[:20]}
    return score, grade, metrics, extras

# ---------------- EXCEL FORMATTER ----------------
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

    # Style headers
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align

    headers = [c.value for c in ws[1]]

    def num(v):
        try:
            return float(v)
        except Exception:
            try:
                return int(v)
            except Exception:
                return None

    # Red highlight failing Actuals
    for row in ws.iter_rows(min_row=2):
        lookup = {headers[i]: row[i] for i in range(len(headers))}

        def val(h):
            c = lookup.get(h)
            return c.value if c else None

        def mark_red(h, cond):
            c = lookup.get(h)
            if c and cond:
                c.fill = red_fill

        mark_red("Title Length Actual", not (50 <= (num(val("Title Length Actual")) or -1) <= 60))
        mark_red("Meta Length Actual", not (150 <= (num(val("Meta Length Actual")) or -1) <= 160))
        mark_red("H1 Count Actual", (num(val("H1 Count Actual")) or -1) != 1)
        mark_red("H2 Count Actual", not (2 <= (num(val("H2 Count Actual")) or -1) <= 5))
        mark_red("Content Length Actual", (num(val("Content Length Actual")) or -1) < 600)
        mark_red("Paragraph Count Actual", (num(val("Paragraph Count Actual")) or -1) < 8)
        mark_red("Image Count Actual", (num(val("Image Count Actual")) or -1) < 3)
        img_actual = num(val("Image Count Actual")) or 0
        alt_actual = num(val("Alt Tags Actual")) or 0
        mark_red("Alt Tags Actual", alt_actual < img_actual)
        mark_red("Internal Links Actual", not (2 <= (num(val("Internal Links Actual")) or -1) <= 5))
        mark_red("External Links Actual", not (2 <= (num(val("External Links Actual")) or -1) <= 4))
        mark_red("Readability Actual", not (10 <= (num(val("Readability Actual")) or -1) <= 20))

        for cell in row:
            cell.border = thin_border
            cell.alignment = center_align

    # Column widths
    for col in ws.columns:
        col_letter = col[0].column_letter
        header_val = ws[f"{col_letter}1"].value
        if header_val == "Summary":
            ws.column_dimensions[col_letter].width = 20
        elif header_val and "Verdict" in str(header_val):
            ws.column_dimensions[col_letter].width = 18
        elif header_val and "Ideal" in str(header_val):
            ws.column_dimensions[col_letter].width = 30
        else:
            ws.column_dimensions[col_letter].width = 22

    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ---------------- UI ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition")
st.subheader("URL Analysis → Excel Report → Actual vs Ideal + Human Verdicts")

uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt", "csv", "xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)

# Merge uploaded into text area
if uploaded is not None:
    try:
        if uploaded.type == "text/plain":
            content = uploaded.read().decode("utf-8", errors="ignore")
            uploaded_urls = "\n".join([l.strip() for l in content.splitlines() if l.strip()])
        elif uploaded.type == "text/csv":
            df_u = pd.read_csv(uploaded, header=None)
            uploaded_urls = "\n".join(df_u.iloc[:, 0].astype(str).str.strip())
        else:
            df_u = pd.read_excel(uploaded, header=None)
            uploaded_urls = "\n".join(df_u.iloc[:, 0].astype(str).str.strip())
        st.info("File processed. Merged into the text area below.")
        existing = urls_input.strip()
        urls_input = (existing + "\n" + uploaded_urls).strip() if existing else uploaded_urls
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")

process = st.button("Process & Create Report")

if process:
    if not urls_input.strip():
        st.error("Please paste some URLs or upload a file.")
    else:
        urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
        rows = []
        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(urls, start=1):
            status.text(f"Processing {i}/{len(urls)} : {url}")
            data = extract_article(url)
            score, grade, metrics, extras = seo_analysis_struct(data)

            row = {
                "URL": url,
                "Summary": extras["Summary"],
                "SEO Score": score,
                "SEO Grade": grade,
            }

            # Add Actual + Ideal + Verdict for each essential metric
            for actual_h, actual_v, ideal_h, ideal_v, verdict_h, verdict_v in metrics:
                row[actual_h] = actual_v
                row[ideal_h] = ideal_v
                row[verdict_h] = verdict_v

            rows.append(row)
            progress.progress(int((i / len(urls)) * 100))

        df = pd.DataFrame(rows)

        # Excel: Audit + Column Definitions sheets
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")

            # Create Column Definitions sheet (ONLY IDEAL HEADINGS)
            wb = writer.book
            ws_def = wb.create_sheet("Column Definitions")
            ws_def.append(["Ideal Column Heading", "Meaning (Kya hai)", "Why Important (Kyu zaruri)"])

            ideal_definitions = [
                ("Title Length Ideal", "Recommended title length", "Fits search snippet, readable headline, improves CTR"),
                ("Meta Length Ideal", "Recommended meta description length", "Fits Google snippet, persuasive summary without truncation"),
                ("H1 Count Ideal", "Exactly one H1 tag", "Clear main headline, avoids confusion for users and crawlers"),
                ("H2 Count Ideal", "2–5 H2 subheadings", "Improves structure and readability, helps users scan content"),
                ("Content Length Ideal", "600+ words in article", "Shows depth and authority, increases dwell time and trust"),
                ("Paragraph Count Ideal", "8+ paragraphs", "Makes content scannable, reduces fatigue, improves UX"),
                ("Image Count Ideal", "3+ images", "Boosts visual engagement, breaks monotony, supports storytelling"),
                ("Alt Tags Ideal", "All images have alt text", "Accessibility compliance, better image SEO and context"),
                ("Internal Links Ideal", "2–5 internal links", "Guides readers to related content, improves site navigation and retention"),
                ("External Links Ideal", "2–4 external links", "Adds credibility via trusted references, supports fact-checking"),
                ("Readability Ideal", "10–20 words per sentence", "Natural flow, easier comprehension, reduces cognitive load"),
            ]

            for row in ideal_definitions:
                ws_def.append(row)

            for col in ws_def.columns:
                ws_def.column_dimensions[col[0].column_letter].width = 32

        final_bytes = apply_excel_formatting(out.getvalue())

        st.success("🎉 Report created successfully!")
        st.download_button(
            "Download SEO Audit Excel",
            data=final_bytes,
            file_name="SEO_Audit_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
