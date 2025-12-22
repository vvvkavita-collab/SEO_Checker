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
st.set_page_config(
    page_title="Advanced SEO Auditor – Director Edition",
    layout="wide"
)
st.title("🧠 Advanced SEO Auditor – News & Blog")


# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio(
    "Select Content Type",
    ["News Article", "Blog / Evergreen"]
)

st.sidebar.markdown("---")

bulk_file = st.sidebar.file_uploader(
    "Upload Bulk URLs (TXT / CSV)",
    type=["txt", "csv"]
)

url = st.text_input("Paste URL")
analyze = st.button("Analyze")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ================= HELPERS =================
def get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def get_article(soup):
    return (
        soup.find("article")
        or soup.find("div", class_=re.compile("content|story", re.I))
        or soup
    )


# ================= IMAGE LOGIC =================
def get_real_images(article):
    images = []

    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img:
            src = img.get("src") or ""
            if src and not any(
                x in src.lower()
                for x in ["logo", "icon", "sprite", "ads"]
            ):
                images.append(img)

    if not images:
        for img in article.find_all("img"):
            cls = " ".join(img.get("class", []))
            src = img.get("src") or ""
            if (
                any(x in cls.lower() for x in ["featured", "post", "hero"])
                and src
            ):
                images.append(img)

    return images[:1]


# ================= PARAGRAPHS =================
def get_real_paragraphs(article):
    paras = []

    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)

        if len(text) < 80:
            continue

        if re.search(
            r"(photo|file|agency|inputs|also read|read more|advertisement)",
            text.lower()
        ):
            continue

        paras.append(text)

    return paras


# ================= LINKS =================
def get_links(article, domain):
    internal = 0
    external = 0

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


# ================= SEO TITLE =================
def generate_seo_title(title, max_len=60):
    """
    Unicode-safe truncate without cutting last word
    """
    words = title.split()
    result = ""

    def visible_len(s):
        return sum(
            1 for c in s
            if not unicodedata.category(c).startswith("C")
        )

    for w in words:
        candidate = (result + " " + w).strip() if result else w
        if visible_len(candidate) > max_len:
            break
        result = candidate

    return result


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
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    for col in ws.columns:
        max_len = max(
            len(str(cell.value)) if cell.value else 0
            for cell in col
        )
        ws.column_dimensions[
            get_column_letter(col[0].column)
        ].width = min(max_len + 3, 50)

    for cell in ws[1]:
        cell.font = bold
        cell.fill = header_fill
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )
        cell.border = border

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )
            cell.border = border

    ws.sheet_view.showGridLines = False

    final = BytesIO()
    wb.save(final)
    final.seek(0)

    return final


# ================= H2 COUNT FIX =================
def get_h2_count_fixed(article):
    h2s = article.find_all("h2")
    real_h2 = []

    for idx, h2 in enumerate(h2s):
        text = h2.get_text(strip=True)

        if idx == 0 and len(text) > 100:
            continue

        if re.search(
            r"(advertisement|related|subscribe|promo|sponsored|news in short)",
            text,
            re.I
        ):
            continue

        if len(text) < 20:
            continue

        real_h2.append(h2)

    return len(real_h2)


# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No H1 Found"
    title_len = len(title)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    img_count = len(get_real_images(article))
    h1_count = len(article.find_all("h1"))
    h2_count = get_h2_count_fixed(article)

    internal, external = get_links(article, domain)
    seo_title = generate_seo_title(title)

    return [
        ["Title Character Count", title_len, "≤ 60", "❌" if title_len > 60 else "✅"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "250+", "✅" if word_count >= 250 else "❌"],
        ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "❌"],
        ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "❌"],
        ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "❌"],
        ["Internal Links", internal, "2–10", "❌" if internal < 2 else "✅"],
        ["External Links", external, "0–2", "❌" if external > 2 else "✅"],
    ]


# ================= RUN =================
if analyze:
    urls = []

    if bulk_file:
        lines = bulk_file.read().decode("utf-8").splitlines()
        urls = [l.strip() for l in lines if l.strip()]
    elif url:
        urls = [url]

    for idx, u in enumerate(urls):
        data = analyze_url(u)
        df = pd.DataFrame(
            data,
            columns=["Metric", "Actual", "Ideal", "Verdict"]
        )

        st.subheader(f"📊 SEO Audit Report – URL {idx + 1}")
        st.dataframe(df, use_container_width=True)

        excel = format_excel(df)

        st.download_button(
            label="⬇️ Download Director Ready SEO Report",
            data=excel,
            file_name=f"SEO_Audit_Report_{idx + 1}.xlsx",
            key=f"download_{idx}"
        )
