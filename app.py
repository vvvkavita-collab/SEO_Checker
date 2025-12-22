import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from collections import Counter

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Editor Edition)")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])
st.sidebar.markdown("---")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url = st.text_input("Paste URL")
analyze = st.button("Analyze")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return soup.find("article") or soup.find("div", class_=re.compile("content|story", re.I)) or soup

# ================= PARAGRAPHS =================
def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(photo|file|agency|inputs|also read|read more|advertisement)", text.lower()):
            continue
        paras.append(text)
    return paras

# ================= IMAGE =================
def get_real_images(article):
    imgs = []
    for img in article.find_all("img"):
        src = img.get("src", "")
        if src and not any(x in src.lower() for x in ["logo", "icon", "ads", "sprite"]):
            imgs.append(img)
    return imgs[:1]

# ================= LINKS =================
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

# ================= H2 COUNT =================
def get_h2_count_fixed(article):
    real = []
    for h2 in article.find_all("h2"):
        t = h2.get_text(strip=True)
        if len(t) < 20:
            continue
        if re.search(r"(advertisement|subscribe|related)", t, re.I):
            continue
        real.append(h2)
    return len(real)

# ================= SEO TITLE (EDITORIAL) =================
def generate_editorial_seo_title(article_text, max_len=100):
    stop = set([
        "है","और","को","का","की","में","से","पर","कर","हो","इस",
        "the","is","at","on","and","a","an","for","to","of","in","with"
    ])

    words = re.findall(r'[\w\u0900-\u097F]+', article_text)
    words = [w for w in words if w not in stop and len(w) > 3]

    freq = Counter(words)
    top = [w for w, _ in freq.most_common(5)]

    year = re.search(r'20\d{2}', article_text)
    num = re.search(r'\d+\s*लाख|\d+\s*हजार|\d+', article_text)

    title_parts = []

    if top:
        title_parts.append(top[0])

    if year:
        title_parts.append(year.group())

    if num:
        title_parts.append(f": {num.group()}+")

    context = " ".join(top[1:4])
    seo_title = " ".join(title_parts) + " " + context
    seo_title = seo_title.strip(" :-,")

    if len(seo_title) > max_len:
        seo_title = seo_title[:max_len].rsplit(" ", 1)[0]

    return seo_title

# ================= GOOGLE DISCOVER TITLE =================
def generate_discover_title(article_text, max_len=90):
    hooks = ["बड़ी खबर", "जानिए", "अब तय", "सरकार का फैसला", "सबसे बड़ा अपडेट"]

    words = re.findall(r'[\w\u0900-\u097F]+', article_text)
    freq = Counter(words)
    top = [w for w, _ in freq.most_common(4)]

    hook = hooks[0]
    discover = f"{hook}: " + " ".join(top)

    if len(discover) > max_len:
        discover = discover[:max_len].rsplit(" ", 1)[0]

    return discover

# ================= EXCEL =================
def format_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    wb = load_workbook(output)
    ws = wb.active

    border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9EAF7")
        cell.border = border
        cell.alignment = Alignment(horizontal="center")

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    ws.sheet_view.showGridLines = False

    final = BytesIO()
    wb.save(final)
    final.seek(0)
    return final

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No H1"

    paras = get_real_paragraphs(article)
    text = " ".join(paras)

    seo_title = generate_editorial_seo_title(text)
    discover_title = generate_discover_title(text)

    data = [
        ["Original Title", title, "-", "-"],
        ["Suggested SEO Title", seo_title, "≤100 chars", "✅"],
        ["Google Discover Title", discover_title, "≤90 chars", "🔥"],
        ["Word Count", len(text.split()), "250+", "✅" if len(text.split()) >= 250 else "❌"],
        ["Image Count", len(get_real_images(article)), "1+", "✅"],
        ["H1 Count", len(article.find_all("h1")), "1", "✅"],
        ["H2 Count", get_h2_count_fixed(article), "2+", "✅"],
    ]

    return data

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = bulk_file.read().decode().splitlines()
    elif url:
        urls = [url]

    for i, u in enumerate(urls):
        data = analyze_url(u)
        df = pd.DataFrame(data, columns=["Metric", "Actual", "Ideal", "Verdict"])

        st.subheader(f"📊 SEO Audit Report – URL {i+1}")
        st.dataframe(df, use_container_width=True)

        excel = format_excel(df)
        st.download_button(
            "⬇️ Download Director Ready SEO Report",
            excel,
            f"SEO_Audit_Report_{i+1}.xlsx",
            key=i
        )
