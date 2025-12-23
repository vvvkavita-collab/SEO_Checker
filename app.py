import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO

from openpyxl import load_workbook
from openpyxl.styles import Font, Border, Side
from openpyxl.utils import get_column_letter

# ===================== CONFIG =====================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ===================== HELPERS =====================
def safe_text(tag):
    return tag.get_text(strip=True) if tag else ""

def clean_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

def get_article(soup):
    article = soup.find("article")
    if article:
        return article
    for cls in ["story", "content", "article", "post"]:
        div = soup.find("div", class_=re.compile(cls, re.I))
        if div:
            return div
    return soup

# ===================== H2 FIX (FINAL) =====================
def get_h2_count_fixed(article):
    h2s = article.find_all("h2")
    real = []
    for idx, h2 in enumerate(h2s):
        t = safe_text(h2)

        # skip empty / short
        if not t or len(t) < 20:
            continue

        # skip junk headings
        if re.search(r"(advertisement|related|subscribe|promo)", t, re.I):
            continue

        # skip first big heading if page uses H2 as title
        if idx == 0 and len(t) > 100:
            continue

        real.append(h2)
    return len(real)

# ===================== ANALYSIS =====================
def analyze_url(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        article = get_article(soup)

        title = safe_text(soup.title)
        h1 = safe_text(article.find("h1"))

        words = len(re.findall(r"\w+", safe_text(article)))
        images = len(article.find_all("img"))
        links = len(article.find_all("a"))
        h2_count = get_h2_count_fixed(article)

        return {
            "URL": url,
            "Clean URL": clean_url(url),
            "Title": title,
            "H1": h1,
            "Word Count": words,
            "H2 Count": h2_count,
            "Images": images,
            "Links": links
        }

    except Exception as e:
        return {
            "URL": url,
            "Clean URL": "",
            "Title": "ERROR",
            "H1": "",
            "Word Count": 0,
            "H2 Count": 0,
            "Images": 0,
            "Links": 0
        }

# ===================== EXCEL FORMAT =====================
def format_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active

    border = Border(
        left=Side(style="thin", color="ADD8E6"),
        right=Side(style="thin", color="ADD8E6"),
        top=Side(style="thin", color="ADD8E6"),
        bottom=Side(style="thin", color="ADD8E6")
    )

    for row in ws.iter_rows():
        for cell in row:
            cell.border = border
            if cell.row == 1:
                cell.font = Font(bold=True)

    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = 28

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out

# ===================== STREAMLIT UI =====================
st.set_page_config(page_title="News SEO Checker", layout="wide")

st.title("📰 News SEO Audit Tool")

mode = st.radio("Select Input Method", ["Paste URL", "Upload Excel"])

urls = []

if mode == "Paste URL":
    url = st.text_input("Enter News URL")
    if url:
        urls.append(url)

else:
    file = st.file_uploader("Upload Excel (URL column)", type=["xlsx"])
    if file:
        dfu = pd.read_excel(file)
        urls = dfu.iloc[:, 0].dropna().tolist()

if st.button("Run SEO Audit") and urls:
    data = []
    with st.spinner("Analyzing URLs..."):
        for u in urls:
            data.append(analyze_url(u))

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    excel = format_excel(df)
    st.download_button(
        "⬇️ Download Excel Report",
        excel,
        "SEO_Audit_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
