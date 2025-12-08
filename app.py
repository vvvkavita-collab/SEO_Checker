import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
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
        md = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", attrs={"property": "og:description"}
        )
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
            "summary": summary[:20],
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
            "summary": "",
        }


# ----------------------------------------------------
# SEO ANALYSIS STRUCTURE
# ----------------------------------------------------
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
    if 50 <= len(title) <= 60:
        score += 10
    if 150 <= len(meta) <= 160:
        score += 10
    if h1_count == 1:
        score += 8
    if 2 <= h2_count <= 5:
        score += 6
    if word_count >= 600:
        score += 12
    if paragraph_count >= 8:
        score += 6
    if 1 <= keyword_density <= 2:
        score += 8
    if img_count >= 3:
        score += 8
    if img_count > 0 and alt_with == img_count:
        score += 6
    if 2 <= internal_links <= 5:
        score += 4
    if 2 <= external_links <= 4:
        score += 4
    if 10 <= avg_wps <= 20:
        score += 8

    score = min(score, 100)

    grade = (
        "A+"
        if score >= 90
        else "A"
        if score >= 80
        else "B"
        if score >= 65
        else "C"
        if score >= 50
        else "D"
    )

    predicted_rating = round(score / 10, 1)

    extras = {"Summary": data["summary"]}

    return score, grade, predicted_rating, pairs, extras


# ----------------------------------------------------
# EXCEL FORMATTER WITH RED HIGHLIGHT
# ----------------------------------------------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb["Audit"]

    ws.sheet_view.showGridLines = False

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")

    red_fill = PatternFill("solid", fgColor="FF9999")

    thin_border = Border(
        left=Side(style="thin", color="4F81BD"),
        right=Side(style="thin", color="4F81BD"),
        top=Side(style="thin", color="4F81BD"),
        bottom=Side(style="thin", color="4F81BD"),
    )

    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Style header
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align

    # RED highlight for out-of-range values
    for row in ws.iter_rows(min_row=2):
        row_dict = {ws.cell(row=1, column=i + 1).value: cell for i, cell in enumerate(row)}

        # Title length
        if not (50 <= row_dict["Title Length Actual"].value <= 60):
            row_dict["Title Length Actual"].fill = red_fill

        # Meta length
        if not (150 <= row_dict["Meta Length Actual"].value <= 160):
            row_dict["Meta Length Actual"].fill = red_fill

        # H1 count
        if row_dict["H1 Count Actual"].value != 1:
            row_dict["H1 Count Actual"].fill = red_fill

        # H2 count
        if not (2 <= row_dict["H2 Count Actual"].value <= 5):
            row_dict["H2 Count Actual"].fill = red_fill

        # Word count
        if row_dict["Content Length Actual"].value < 600:
            row_dict["Content Length Actual"].fill = red_fill

        # Paragraph count
        if row_dict["Paragraph Count Actual"].value < 8:
            row_dict["Paragraph Count Actual"].fill = red_fill

        # Image count
        if row_dict["Image Count Actual"].value < 3:
            row_dict["Image Count Actual"].fill = red_fill

        # Alt tags
        if row_dict["Alt Tags Actual"].value < row_dict["Image Count Actual"].value:
            row_dict["Alt Tags Actual"].fill = red_fill

        # Internal links
        if not (2 <= row_dict["Internal Links Actual"].value <= 5):
            row_dict["Internal Links Actual"].fill = red_fill

        # External links
        if not (2 <= row_dict["External Links Actual"].value <= 4):
            row_dict["External Links Actual"].fill = red_fill

        # Readability
        if not (10 <= row_dict["Readability Actual"].value <= 20):
            row_dict["Readability Actual"].fill = red_fill

        # Apply borders and alignment
        for cell in row:
            cell.border = thin_border
            cell.alignment = center_align

    # Column width
    for col in ws.columns:
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = 22

    out = BytesIO()
    wb.save(out)
    return out.getvalue()


# ----------------------------------------------------
# Guideline Sheet
# ----------------------------------------------------
def add_guideline_sheet(wb):
    ws = wb.create_sheet("SEO Guidelines")
    ws.append(["Parameter", "Meaning / Purpose", "Ideal Range", "Why Important"])

    data_list = [
        ("Title Length", "Main headline", "50–60 chars", "CTR + Ranking"),
        ("Meta Description", "Search snippet text", "150–160 chars", "CTR improvement"),
        ("H1 Count", "Main heading", "1", "Topic clarity for Google"),
        ("H2 Count", "Subheadings structure", "2–5", "Readability + SEO"),
        ("Content Length", "Total words", "600+", "Depth of content"),
        ("Paragraph Count", "Sections", "8+", "User experience"),
        ("Keyword Density", "Keywords %", "1–2%", "Avoid stuffing"),
        ("Images", "Total visuals", "3+", "Engagement"),
        ("Alt Tags", "Image alt text", "All images", "Image SEO"),
        ("Internal Links", "Same site links", "2–5", "Structure + ranking"),
        ("External Links", "Trusted external links", "2–4", "Credibility"),
        ("Readability", "Words per sentence", "10–20", "Better user retention"),
    ]

    for row in data_list:
        ws.append(row)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 25


# ----------------------------------------------------
# STREAMLIT PREMIUM UI
# ----------------------------------------------------
st.markdown(
    """
<style>
body {
    background: linear-gradient(135deg, #1F1C2C, #928DAB);
}
.main {
    background: #ffffffdd;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.4);
}
textarea, .stTextInput, .stFileUploader {
    border-radius: 10px !important;
    border: 2px solid #4F81BD !important;
    background: #F4F6FA !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🚀 Advanced SEO Auditor – Premium Version")
st.subheader("Analyze URLs + Auto Excel + SEO Guidelines Sheet")


# ----------------------------------------------------
# INPUT AREA
# ----------------------------------------------------
uploaded = st.file_uploader("Upload URL List (txt/csv/xlsx)", type=["txt", "csv", "xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)


# ----------------------------------------------------
# PROCESS BUTTON
# ----------------------------------------------------
if st.button("Process & Create Excel"):

    raw = urls_input.strip()

    if not raw:
        st.error("Please paste some URLs.")
    else:
        urls = [u.strip() for u in raw.splitlines() if u.strip()]

        rows = []
        pairs_reference = None

        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(urls, start=1):
            status.text(f"Processing {i}/{len(urls)} : {url}")

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
                "Predicted Public Rating": predicted,
            }

            for ideal, ideal_val, actual, actual_val in pairs_reference:
                row[ideal] = ideal_val
                row[actual] = actual_val

            rows.append(row)
            progress.progress(int((i / len(urls)) * 100))

        df = pd.DataFrame(rows)

        out = BytesIO()
        wb = Workbook()

        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")

        wb2 = load_workbook(out)
        add_guideline_sheet(wb2)

        final_export = BytesIO()
        wb2.save(final_export)

        final_bytes = apply_excel_formatting(final_export.getvalue())

        st.success("🎉 Excel created successfully with SEO Guidelines")

        st.download_button(
            "Download SEO Audit Excel",
            data=final_bytes,
            file_name="SEO_Audit_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
