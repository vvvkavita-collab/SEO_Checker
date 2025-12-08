import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook, Workbook
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
            "title": title[:20],
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
            "summary": summary[:20]
        }

    except:
        return {
            "title": "",
            "meta": "",
            "article": "",
            "h1": [],
            "h2": [],
            "img_count": 0,
            "alt_with": 0,
            "internal_links": 0,
            "external_links": 0,
            "paragraph_count": 0,
            "sentence_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "summary": ""
        }


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
        ("Title Length Ideal", "50-60 chars", "Title Length Actual", len(title)),
        ("Meta Length Ideal", "150-160 chars", "Meta Length Actual", len(meta)),
        ("H1 Count Ideal", 1, "H1 Count Actual", h1_count),
        ("H2 Count Ideal", "2-5", "H2 Count Actual", h2_count),
        ("Content Length Ideal", "600+", "Content Length Actual", word_count),
        ("Paragraph Count Ideal", "8+", "Paragraph Count Actual", paragraph_count),
        ("Keyword Density Ideal (%)", "1-2", "Keyword Density Actual (%)", keyword_density),
        ("Image Count Ideal", "3+", "Image Count Actual", img_count),
        ("Alt Tags Ideal", "All images", "Alt Tags Actual", alt_with),
        ("Internal Links Ideal", "2-5", "Internal Links Actual", internal_links),
        ("External Links Ideal", "2-4", "External Links Actual", external_links),
        ("Readability Ideal (avg words/sent)", "10-20", "Readability Actual", avg_wps)
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

    grade = ("A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D")
    predicted_rating = round(score / 10, 1)

    extras = {"Summary": data["summary"]}

    return score, grade, predicted_rating, pairs, extras


# ----------------------------------------------------
# EXCEL FORMATTER
# ----------------------------------------------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb.active

    ws.sheet_view.showGridLines = False

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")

    thin_border = Border(
        left=Side(style='thin', color='4F81BD'),
        right=Side(style='thin', color='4F81BD'),
        top=Side(style='thin', color='4F81BD'),
        bottom=Side(style='thin', color='4F81BD')
    )

    center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, row in enumerate(ws.iter_rows(), 1):
        for cell in row:
            cell.alignment = center_alignment
            cell.border = thin_border
            if row_idx == 1:
                cell.font = header_font
                cell.fill = header_fill

    # Limit URL, Title, Summary columns to 20 chars width
    for col in ws.columns:
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = 20

    out = BytesIO()
    wb.save(out)
    return out.getvalue()


# ----------------------------------------------------
# CREATE GUIDELINE SHEET
# ----------------------------------------------------
def add_guideline_sheet(wb):
    ws2 = wb.create_sheet("SEO Guidelines")

    ws2.append(["Parameter", "Meaning / Purpose", "Ideal Range", "Why Important for SEO"])

    guidelines = [
        ("Title Length", "Main title shown on Google search", "50-60 chars", "Helps CTR & keyword visibility"),
        ("Meta Description", "Short description in Google result", "150-160 chars", "Improves click-through rate"),
        ("H1 Count", "Main page heading", "1", "Helps Google understand main topic"),
        ("H2 Count", "Sub-headings", "2-5", "Improves readability & keyword structure"),
        ("Content Length", "Total article words", "600+", "Longer content ranks higher"),
        ("Paragraph Count", "Total paragraphs", "8+", "Improves user experience & clarity"),
        ("Keyword Density", "Keyword % in article", "1-2%", "Prevents keyword stuffing"),
        ("Image Count", "Images in article", "3+", "Improves engagement"),
        ("Alt Tags", "Image alt text", "All", "Helps Google image SEO"),
        ("Internal Links", "Website internal links", "2-5", "Helps site structure"),
        ("External Links", "Outside links", "2-4", "Improves credibility"),
        ("Readability", "Words per sentence", "10-20", "Easy to read = better ranking")
    ]

    for row in guidelines:
        ws2.append(row)

    for col in ws2.columns:
        ws2.column_dimensions[col[0].column_letter].width = 25


# ----------------------------------------------------
# PREMIUM STREAMLIT UI
# ----------------------------------------------------
st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364) !important;
    background-attachment: fixed !important;
}

/* Glass Box */
.main-block {
    background: rgba(255, 255, 255, 0.18);
    padding: 35px;
    border-radius: 18px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    margin-top: 20px;
    margin-bottom: 20px;
}

/* Stylish Inputs */
textarea, input, .stTextInput, .stTextArea, .stFileUploader {
    background: rgba(255,255,255,0.65) !important;
    border-radius: 12px !important;
    padding: 10px !important;
    border: 1px solid #d0d4dc !important;
    box-shadow: inset 0px 1px 6px rgba(0,0,0,0.15);
}

/* Beautiful Headings */
h1 {
    text-align: center;
    color: #ffffff !important;
    font-weight: 900 !important;
    margin-bottom: 5px;
    text-shadow: 1px 1px 4px #000000;
}

h2, h3, h4 {
    color: #ffffff !important;
    text-shadow: 0px 0px 3px #000;
}

/* Premium Buttons */
.stButton button {
    background: #4F81BD !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 10px 25px !important;
    font-size: 18px !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.4);
    font-weight: 600 !important;
    transition: 0.2s ease-in-out;
}

.stButton button:hover {
    transform: scale(1.04);
    background: #3a6595 !important;
}

</style>
""", unsafe_allow_html=True)


st.markdown('<div class="main-block">', unsafe_allow_html=True)

st.title("🚀 Advanced SEO Auditor – Premium UI")
st.subheader("Analyze URLs & download a complete SEO audit Excel with guidelines")

uploaded = st.file_uploader("Upload URL File (txt/csv/xlsx)", type=["txt", "csv", "xlsx"])
urls_input = st.text_area("Paste URLs here (ONE PER LINE)", height=200)

process_btn = st.button("Process & Create Excel")


# ----------------------------------------------------
# PROCESS LOGIC
# ----------------------------------------------------
if process_btn:
    raw = urls_input.strip()

    if not raw:
        st.error("Please enter URLs first.")
    else:

        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        rows = []
        pairs_reference = None

        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(urls, start=1):
            status.text(f"Processing {i}/{len(urls)}: {url}")

            data = extract_article(url)
            score, grade, predicted, pairs, extras = seo_analysis_struct(data)

            if pairs_reference is None:
                pairs_reference = pairs

            row = {
                "URL": url[:20],
                "Title": data["title"],
                "Summary": extras["Summary"],
                "SEO Score": score,
                "SEO Grade": grade,
                "Predicted Public Rating": predicted
            }

            for ideal_col, ideal_val, actual_col, actual_val in pairs_reference:
                row[ideal_col] = ideal_val
                row[actual_col] = actual_val

            rows.append(row)
            progress.progress(int(i / len(urls) * 100))

        df = pd.DataFrame(rows)

        out = BytesIO()
        wb = Workbook()

        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")

        wb2 = load_workbook(out)
        add_guideline_sheet(wb2)

        final_out = BytesIO()
        wb2.save(final_out)

        final_bytes = apply_excel_formatting(final_out.getvalue())

        st.success("Excel created successfully with SEO Guidelines sheet!")

        st.download_button(
            "⬇ Download SEO Audit Excel",
            data=final_bytes,
            file_name="SEO_Audit_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown('</div>', unsafe_allow_html=True)
