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

# ---------------- SAFE GET TEXT ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

# ---------------- ARTICLE EXTRACTOR ----------------
def extract_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip()[:20] if soup.title and soup.title.string else ""

        meta_desc = ""
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if md and md.get("content"):
            meta_desc = md.get("content").strip()[:20]

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
            summary = summary[:20]

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
            "title": "", "meta": "", "article": "",
            "h1": [], "h2": [],
            "img_count": 0, "alt_with": 0,
            "internal_links": 0, "external_links": 0,
            "paragraph_count": 0, "sentence_count": 0,
            "word_count": 0, "avg_words_per_sentence": 0,
            "summary": ""
        }

# ---------------- EXCEL FORMATTING ----------------
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

    # Column widths with max 20 for URL, Title, Summary
    for col_idx, col in enumerate(ws.columns, 1):
        column_letter = col[0].column_letter
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        if col_idx in [1, 2, len(ws[1])]:  # URL, Title, Summary
            ws.column_dimensions[column_letter].width = min(20, max_len + 2)
        else:
            ws.column_dimensions[column_letter].width = max_len + 2

    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")
st.title("Advanced SEO Auditor")
st.write("Upload URLs or paste manually. Tool crawls pages & generates Excel with automatic SEO scoring and red-flag highlighting.")

uploaded = st.file_uploader("Upload URL file (txt/csv/xlsx)", type=["txt","csv","xlsx"])
urls_input = st.text_area("Paste URLs here", height=200)

# Load file
if uploaded:
    try:
        if uploaded.name.endswith(".txt"):
            urls = uploaded.read().decode("utf-8").splitlines()
        elif uploaded.name.endswith(".csv"):
            urls = pd.read_csv(uploaded, header=None)[0].dropna().tolist()
        else:
            urls = pd.read_excel(uploaded, header=None)[0].dropna().tolist()
        urls_input = "\n".join([u.strip()[:20] for u in urls if u.strip()])
        st.success(f"Loaded {len(urls)} URLs.")
    except Exception as e:
        st.error(f"Error reading file: {e}")

process_btn = st.button("Process & Create Excel")

if process_btn:
    raw = urls_input.strip()
    if not raw:
        st.error("No URLs entered.")
    else:
        urls = [u.strip()[:20] for u in raw.splitlines() if u.strip()]
        rows = []
        progress = st.progress(0)
        status = st.empty()
        for i, url in enumerate(urls, start=1):
            status.text(f"Processing {i}/{len(urls)}: {url}")
            data = extract_article(url)
            row = {
                "URL": url,
                "Title": data["title"][:20],
                "Summary": data["summary"][:20]
            }
            rows.append(row)
            progress.progress(int(i / len(urls) * 100))

        df = pd.DataFrame(rows)
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")
        formatted_bytes = apply_excel_formatting(out.getvalue())

        st.success("Excel created successfully.")
        st.dataframe(df.style.set_properties(**{
            'text-align': 'center',
            'white-space': 'nowrap',
            'overflow': 'hidden',
            'text-overflow': 'ellipsis'
        }))

        st.download_button(
            "Download SEO Audit",
            data=formatted_bytes,
            file_name="seo_audit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
