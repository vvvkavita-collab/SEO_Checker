import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.views import SheetView

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Editor Mode)")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

st.sidebar.subheader("Analyze Options")
single_url = st.text_input("Paste Single URL")

bulk_file = st.sidebar.file_uploader(
    "Upload Bulk URLs (CSV / TXT)",
    type=["csv", "txt"]
)

analyze = st.sidebar.button("Analyze")

# ================= HELPERS =================
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# ---- REAL PARAGRAPHS ----
def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(photo|file|agency|inputs|also read|read more)", text.lower()):
            continue
        paras.append(text)
    return paras

# ---- IMAGES ----
def get_real_images(article):
    images = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            images.append(img)
    return images[:1]

# ---- LINKS ----
def get_links(article, domain):
    internal = external = 0
    for a in article.find_all("a", href=True):
        h = a["href"]
        if h.startswith("http"):
            if domain in h:
                internal += 1
            else:
                external += 1
        else:
            internal += 1
    return internal, external

# ---- SEO SUGGESTED TITLE (GENERIC ENGINE) ----
def generate_seo_title(title, paragraphs):
    title = clean_text(title)

    action_words = [
        "फेल", "गिरफ्तार", "मौत", "हादसा", "बारिश", "अलर्ट",
        "फैसला", "घोषणा", "लॉन्च", "विस्फोट", "हमला"
    ]

    action = ""
    for p in paragraphs[:2]:
        for w in action_words:
            if w in p:
                action = w
                break
        if action:
            break

    # Primary topic = first phrase
    topic = title.split(":")[0]

    if action and action not in topic:
        seo_title = f"{topic}: {action} से जुड़ी बड़ी खबर"
    else:
        seo_title = title

    return clean_text(seo_title)

# ================= COLLECT URLS =================
urls = []

if single_url:
    urls.append(single_url)

if bulk_file:
    if bulk_file.name.endswith(".csv"):
        df_urls = pd.read_csv(bulk_file)
        urls.extend(df_urls.iloc[:, 0].dropna().tolist())
    else:
        text = bulk_file.read().decode("utf-8")
        urls.extend([u.strip() for u in text.splitlines() if u.strip()])

# ================= ANALYSIS =================
if analyze and urls:
    final_rows = []

    for url in urls:
        try:
            soup = get_soup(url)
            domain = urlparse(url).netloc
            article = soup.find("article") or soup

            title = soup.find("h1").get_text(strip=True)
            title_len = len(title)

            paragraphs = get_real_paragraphs(article)
            word_count = sum(len(p.split()) for p in paragraphs)

            seo_title = generate_seo_title(title, paragraphs)

            images = get_real_images(article)
            internal, external = get_links(article, domain)

            final_rows.append([
                url,
                title,
                seo_title,
                title_len,
                word_count,
                len(images),
                internal,
                external
            ])

        except Exception as e:
            final_rows.append([url, "ERROR", "ERROR", 0, 0, 0, 0, 0])

    df = pd.DataFrame(
        final_rows,
        columns=[
            "URL",
            "Original Title",
            "Suggested SEO Title",
            "Title Length",
            "Word Count",
            "Image Count",
            "Internal Links",
            "External Links"
        ]
    )

    st.subheader("📊 SEO Audit Report")
    st.dataframe(df, use_container_width=True)

    # ================= EXCEL EXPORT (FORMATTED) =================
    output = BytesIO()
    df.to_excel(output, index=False, sheet_name="SEO Report")
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active

    # Gridlines OFF
    ws.sheet_view.showGridLines = False

    header_fill = PatternFill("solid", fgColor="CFE8FF")
    header_font = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = wrap

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 30

    final_output = BytesIO()
    wb.save(final_output)

    st.download_button(
        "⬇️ Download Formatted SEO Report",
        final_output.getvalue(),
        "SEO_Audit_Report.xlsx"
    )
