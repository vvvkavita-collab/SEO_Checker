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

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Google Optimized)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return soup.find("article") or soup.find("div", class_=re.compile("content|story|article", re.I)) or soup

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

# ================= CONTENT =================
def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) < 80:
            continue
        if re.search(r"(advertisement|also read|read more|agency|inputs)", t, re.I):
            continue
        paras.append(t)
    return paras

def get_real_images(article):
    imgs = []
    for img in article.find_all("img"):
        src = img.get("src", "")
        if src and not re.search(r"(logo|icon|ads)", src, re.I):
            imgs.append(img)
    return imgs

def get_links(article, domain):
    internal = external = 0
    for a in article.find_all("a", href=True):
        h = a["href"]
        if h.startswith("http"):
            internal += 1 if domain in h else 0
            external += 0 if domain in h else 1
        elif h.startswith("/"):
            internal += 1
    return internal, external

def get_h2_count(article):
    return len([h2 for h2 in article.find_all("h2") if len(h2.get_text(strip=True)) > 20])

# ================= SEO TITLE =================
def generate_seo_title(title, limit=60):
    out = ""
    for w in title.split():
        if visible_len(out + " " + w) > limit:
            break
        out += " " + w
    return out.strip()

# ================= CLEAN URL =================
STOP_WORDS = {"is","the","and","of","to","in","for","on","with","by","who"}

def clean_slug(text):
    text = re.sub(r"[^a-z0-9\s]", "", text.lower())
    return "-".join([w for w in text.split() if w not in STOP_WORDS][:10])

def generate_clean_url(url, title):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/{clean_slug(title)}"

# ================= EXCEL FORMAT =================
def format_excel(sheets):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)

    output.seek(0)
    wb = load_workbook(output)

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        header_fill = PatternFill("solid", fgColor="D9EAF7")
        border = Border(left=Side(style="thin"), right=Side(style="thin"),
                        top=Side(style="thin"), bottom=Side(style="thin"))

        for col in ws.columns:
            ws.column_dimensions[get_column_letter(col[0].column)].width = 40

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(wrap_text=True, horizontal="center")
            cell.border = border

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.border = border

    final = BytesIO()
    wb.save(final)
    final.seek(0)
    return final

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "No H1"
    seo_title = generate_seo_title(title)
    clean_url = generate_clean_url(url, seo_title)

    words = sum(len(p.split()) for p in get_real_paragraphs(article))
    imgs = len(get_real_images(article))
    h1 = len(article.find_all("h1"))
    h2 = get_h2_count(article)
    internal, external = get_links(article, domain)
    stop_found = [w for w in STOP_WORDS if f" {w} " in title.lower()]

    audit = pd.DataFrame([
        ["Title Character Count", visible_len(title), "50–60"],
        ["Suggested SEO Title", title, seo_title],
        ["Word Count", words, "800–1500+"],
        ["News Image Count", imgs, "3–6"],
        ["H1 Count", h1, "1"],
        ["H2 Count", h2, "5–15"],
        ["Internal Links", internal, "3–10"],
        ["External Links", external, "1–3"],
        ["Unnecessary Words", ", ".join(stop_found) or "None", "None"],
        ["SEO URL", url, clean_url],
    ], columns=["Metric", "Actual", "Ideal"])

    explanation = pd.DataFrame([
        ["Title Character Count", "Controls SERP visibility and improves CTR"],
        ["Word Count", "Long-form content performs better in Search & Discover"],
        ["News Image Count", "Improves engagement and Discover reach"],
        ["H1 / H2 Structure", "Helps Google understand content hierarchy"],
        ["Internal Links", "Passes SEO authority within website"],
        ["External Links", "Builds trust and credibility"],
        ["SEO URL", "Clean URLs improve CTR & indexing"],
        ["CTR", "Higher CTR = more traffic, better rankings, more revenue"],
    ], columns=["SEO Factor", "Why It Matters"])

    return audit, explanation

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = bulk_file.read().decode().splitlines()
    elif url_input:
        urls = [url_input]

    audits, explain = [], None

    for u in urls:
        audit, explain = analyze_url(u)
        st.dataframe(audit, use_container_width=True)
        audits.append(audit)

    excel = format_excel({
        "SEO_Audit": pd.concat(audits),
        "SEO_Column_Explanation": explain
    })

    st.download_button("⬇️ Download SEO Audit Excel", excel, "SEO_Audit_Final.xlsx")
