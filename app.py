import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
import unicodedata
from collections import Counter
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return soup.find("article") or soup.find("div", class_=re.compile("content|story", re.I)) or soup

def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(advertisement|also read|read more|photo|agency)", text.lower()):
            continue
        paras.append(text)
    return paras

def get_real_images(article):
    images = []
    for img in article.find_all("img"):
        src = img.get("src") or ""
        if src and not any(x in src.lower() for x in ["logo","icon","ads"]):
            images.append(img)
    return images[:1]

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

# ================= SEO TITLE (FIXED) =================
def generate_seo_title(original_title, article_text, max_len=100):
    """
    Generates a NEW Google Discover friendly title
    (Does NOT repeat original title)
    """

    stopwords = {
        "है","और","को","का","की","में","से","पर","कर","हो","इस","भी","लिए",
        "the","is","in","on","at","and","of","to","for","with","from"
    }

    # Unicode-safe Hindi + English words
    words = re.findall(r'[\u0900-\u097Fa-zA-Z]+', article_text.lower())
    words = [w for w in words if w not in stopwords and len(w) > 3]

    freq = Counter(words)

    # Remove words already present in original title
    original_words = set(re.findall(r'[\u0900-\u097Fa-zA-Z]+', original_title.lower()))
    keywords = [w for w, _ in freq.most_common(10) if w not in original_words]

    if len(keywords) < 3:
        return original_title[:max_len]

    # Discover-style construction
    seo_title = f"{keywords[0].title()} से जुड़ी बड़ी खबर, {keywords[1]} और {keywords[2]} पर अपडेट"

    # Location boost
    if "बिहार" in article_text:
        seo_title += " | Bihar News"
    elif "राजस्थान" in article_text:
        seo_title += " | Rajasthan News"

    return seo_title[:max_len]

# ================= EXCEL FORMAT =================
def format_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active

    header_fill = PatternFill("solid", fgColor="D9EAF7")
    bold = Font(bold=True)
    border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    for col in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 3, 50)

    for cell in ws[1]:
        cell.font = bold
        cell.fill = header_fill
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

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else "No H1 Found"

    paras = get_real_paragraphs(article)
    article_text = " ".join(paras)

    seo_title = generate_seo_title(title, article_text)

    data = [
        ["Original Title", title, "-", "-"],
        ["Suggested SEO Title (≤100)", seo_title, "≤100", "✅"],
        ["Word Count", len(article_text.split()), "250+", "✅" if len(article_text.split()) >= 250 else "❌"],
        ["Image Count", len(get_real_images(article)), "1+", "✅"],
        ["H1 Count", len(article.find_all("h1")), "1", "✅"],
        ["H2 Count", get_h2_count(article), "2+", "✅"],
        ["Internal Links", *get_links(article, domain), "-"],
    ]
    return data

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = bulk_file.read().decode("utf-8").splitlines()
    elif url:
        urls = [url]

    for idx, u in enumerate(urls):
        data = analyze_url(u)
        df = pd.DataFrame(data, columns=["Metric", "Actual", "Ideal", "Verdict"])
        st.subheader(f"📊 SEO Audit – URL {idx+1}")
        st.dataframe(df, use_container_width=True)

        excel = format_excel(df)
        st.download_button(
            "⬇️ Download SEO Report",
            excel,
            file_name=f"SEO_Report_{idx+1}.xlsx",
            key=f"dl_{idx}"
        )

