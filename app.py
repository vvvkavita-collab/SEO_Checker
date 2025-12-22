import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
import unicodedata
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= PAGE =================
st.set_page_config("Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Director Edition)")

HEADERS = {"User-Agent": "Mozilla/5.0"}
STOP_WORDS = {"and", "or", "the", "is", "was", "of", "to", "for", "with"}

# ================= INPUT =================
st.sidebar.header("Input")
bulk_file = st.sidebar.file_uploader("Upload URLs (TXT / CSV)", ["txt", "csv"])
single_url = st.text_input("Or Paste Single URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

def generate_seo_title(title, max_len=60):
    if visible_len(title) <= max_len:
        return title
    out = ""
    for w in title.split():
        tmp = (out + " " + w).strip()
        if visible_len(tmp) > max_len:
            break
        out = tmp
    return out

def clean_slug(slug):
    words = [w for w in slug.split("-") if w and w not in STOP_WORDS]
    return "-".join(words[:10])

def title_url_seo_score(title, url):
    score = 0
    parsed = urlparse(url)
    slug = parsed.path.strip("/").lower()
    words = slug.split("-") if slug else []

    if visible_len(title) <= 60:
        score += 30
    if len(url) <= 80:
        score += 25
    if not any(w in STOP_WORDS for w in words):
        score += 20
    if len(words) <= 10:
        score += 15
    if "_" not in url and url == url.lower():
        score += 10

    return score

# ================= URL ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    parsed = urlparse(url)

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else "No H1 Found"
    seo_title = generate_seo_title(title)

    slug = parsed.path.strip("/").lower()
    words = slug.split("-") if slug else []
    found_stop = sorted(set(w for w in words if w in STOP_WORDS))
    clean = clean_slug(slug)
    suggested_url = f"{parsed.scheme}://{parsed.netloc}/{clean}" if clean else url

    score = title_url_seo_score(seo_title, url)

    return [
        ["URL", url, "", ""],
        ["Title", title, "≤ 60 chars", "❌" if visible_len(title) > 60 else "✅"],
        ["Suggested SEO Title", seo_title, "", ""],
        ["Unnecessary Words", ", ".join(found_stop) if found_stop else "None", "No", "❌" if found_stop else "✅"],
        ["Suggested Clean SEO URL", suggested_url, "", ""],
        ["Title + URL SEO Score", f"{score} / 100", "≥ 80", "✅" if score >= 80 else "⚠️"],
    ]

# ================= EXCEL FORMAT =================
def format_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active

    header = PatternFill("solid", fgColor="D9EAF7")
    bold = Font(bold=True)
    border = Border(left=Side(style="thin"), right=Side(style="thin"),
                    top=Side(style="thin"), bottom=Side(style="thin"))

    for col in ws.columns:
        width = max(len(str(c.value)) if c.value else 0 for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(width + 3, 50)

    for cell in ws[1]:
        cell.font = bold
        cell.fill = header
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border

    ws.sheet_view.showGridLines = False
    final = BytesIO()
    wb.save(final)
    final.seek(0)
    return final

# ================= RUN =================
if analyze:
    urls = []

    if bulk_file:
        urls = bulk_file.read().decode().splitlines()
        urls = [u.strip() for u in urls if u.strip()]
    elif single_url:
        urls = [single_url]

    all_rows = []

    for u in urls:
        rows = analyze_url(u)
        for r in rows:
            all_rows.append(r)

    df = pd.DataFrame(all_rows, columns=["Metric", "Actual", "Ideal", "Verdict"])
    st.dataframe(df, use_container_width=True)

    # Auto-copy button
    clean_urls = df[df["Metric"] == "Suggested Clean SEO URL"]["Actual"].tolist()
    if clean_urls:
        st.code(clean_urls[0], language="text")
        st.caption("⬆️ Suggested SEO URL (Auto-copy supported)")

    excel = format_excel(df)
    st.download_button(
        "⬇️ Download Combined SEO Report (All URLs)",
        excel,
        "Combined_SEO_Audit_Report.xlsx"
    )
