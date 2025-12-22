import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

st.sidebar.subheader("Analyze Options")
single_url = st.text_input("Paste URL")

bulk_file = st.sidebar.file_uploader(
    "Upload Bulk URLs (CSV / TXT – single column)",
    type=["csv", "txt"]
)

analyze = st.sidebar.button("Analyze")

# ================= HELPERS =================
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

# ---- REAL NEWS PARAGRAPHS ONLY (UNCHANGED) ----
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

# ---- HERO / NEWS IMAGE ONLY (UNCHANGED) ----
def get_real_images(article):
    images = []

    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img:
            src = img.get("src") or ""
            if src and not any(x in src.lower() for x in ["logo", "icon", "sprite", "ads"]):
                images.append(img)

    if not images:
        for img in article.find_all("img"):
            cls = " ".join(img.get("class", []))
            src = img.get("src") or ""
            if any(x in cls.lower() for x in ["featured", "post", "hero"]) and src:
                images.append(img)

    return images[:1]

# ---- INTERNAL / EXTERNAL LINKS (UNCHANGED) ----
def get_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            h = a["href"]
            if h.startswith("http"):
                if domain in h:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
    return internal, external

# ---- META CLEAN ----
def clean_meta(text):
    return " ".join(text.replace("\n", " ").split()).strip()

# ---- SEO SUGGESTED TITLE (NEW – SAFE ADDITION) ----
def generate_seo_title(title, paragraphs):
    """
    Editor-style SEO title
    Uses title + first paragraphs
    Does NOT affect audit metrics
    """
    title = clean_meta(title)

    if not paragraphs:
        return title

    p = paragraphs[0]

    keywords = [
        "इंजन फेल", "मौत", "हादसा", "गिरफ्तार",
        "फैसला", "अलर्ट", "बारिश", "भूकंप",
        "लॉन्च", "घोषणा", "हमला"
    ]

    action = ""
    for k in keywords:
        if k in p:
            action = k
            break

    topic = title.split(":")[0].strip()

    if action and action not in title:
        return f"{topic}: {action} से जुड़ी बड़ी खबर"

    return title

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
    all_reports = []

    for url in urls:
        try:
            soup = get_soup(url)
            domain = urlparse(url).netloc

            article = soup.find("article") or soup.find("div", class_=re.compile("content|story", re.I)) or soup

            # -------- TITLE --------
            h1_tag = soup.find("h1")
            title = h1_tag.get_text(strip=True) if h1_tag else soup.title.string.strip()
            title_len = len(title)

            # -------- HEADINGS --------
            h1_count = len(article.find_all("h1"))
            h2_count = len(article.find_all("h2"))

            # -------- CONTENT --------
            paragraphs = get_real_paragraphs(article)
            word_count = sum(len(p.split()) for p in paragraphs)

            # -------- IMAGES --------
            images = get_real_images(article)
            img_count = len(images)

            # -------- LINKS --------
            internal, external = get_links(article, domain)

            # -------- SEO TITLE --------
            seo_title = generate_seo_title(title, paragraphs)

            all_reports.append([
                url,
                title,
                seo_title,
                title_len,
                h1_count,
                h2_count,
                word_count,
                img_count,
                internal,
                external
            ])

        except Exception:
            all_reports.append([url, "ERROR", "ERROR", 0, 0, 0, 0, 0, 0, 0])

    df = pd.DataFrame(
        all_reports,
        columns=[
            "URL",
            "Original Title",
            "Suggested SEO Title",
            "Title Length",
            "H1 Count",
            "H2 Count",
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
        "⬇️ Download SEO Report (Formatted)",
        final_output.getvalue(),
        "SEO_Audit_Report.xlsx"
    )
