import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Director Edition)")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

st.sidebar.markdown("---")
st.sidebar.subheader("Analyze Options")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])

url = st.text_input("Paste Single URL")
analyze = st.button("Analyze")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return soup.find("article") or soup.find("div", class_=re.compile("content|story", re.I)) or soup

# -------- CLEAN PARAGRAPHS (REAL CONTENT ONLY) --------
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

# -------- IMAGE COUNT (REAL NEWS IMAGE) --------
def get_real_images(article):
    images = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            images.append(img)

    if not images:
        for img in article.find_all("img"):
            src = img.get("src", "")
            if src and not any(x in src.lower() for x in ["logo", "icon", "sprite", "ads"]):
                images.append(img)

    return images[:1]

# -------- LINKS --------
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

# -------- META CLEAN --------
def clean_meta(text):
    return " ".join(text.replace("\n", " ").split()).strip()

# ================= SEO TITLE GENERATOR (EDITOR LOGIC) =================
def generate_seo_title(original_title, paragraphs):
    text = " ".join(paragraphs)[:1200]

    if re.search(r"emergency|इमरजेंसी", text, re.I):
        reason = ""
        if re.search(r"engine|इंजन", text, re.I):
            reason = "इंजन में खराबी"
        elif re.search(r"technical|तकनीकी", text, re.I):
            reason = "तकनीकी खराबी"
        else:
            reason = "तकनीकी कारण"

        return f"Air India विमान की इमरजेंसी लैंडिंग, {reason} बनी वजह"

    if re.search(r"accident|हादसा|दुर्घटना", text, re.I):
        return "हादसा: Air India विमान से जुड़ी बड़ी घटना, जांच जारी"

    if re.search(r"delay|लेट|रद्द", text, re.I):
        return "Air India की उड़ान प्रभावित, यात्रियों को हुई परेशानी"

    # SAFE FALLBACK
    cut = original_title[:60]
    return cut.rsplit(" ", 1)[0] if " " in cut else cut

# ================= EXCEL FORMATTER =================
def format_excel(file_bytes):
    wb = load_workbook(file_bytes)
    ws = wb.active

    header_fill = PatternFill("solid", fgColor="D9EAF7")
    bold_font = Font(bold=True)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for cell in ws[1]:
        cell.font = bold_font
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, horizontal="center")
        cell.border = border

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border

    ws.sheet_view.showGridLines = False

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out

# ================= MAIN ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    domain = urlparse(url).netloc
    article = get_article(soup)

    title = soup.find("h1").get_text(strip=True)
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta = clean_meta(meta_tag["content"]) if meta_tag else ""

    paragraphs = get_real_paragraphs(article)

    seo_title = generate_seo_title(title, paragraphs)

    return {
        "URL": url,
        "Original Title": title,
        "Suggested SEO Title": seo_title,
        "Title Length": len(title),
        "Word Count": sum(len(p.split()) for p in paragraphs),
        "Image Count": len(get_real_images(article)),
        "H1 Count": len(article.find_all("h1")),
        "H2 Count": len(article.find_all("h2")),
        "Internal Links": get_links(article, domain)[0],
        "External Links": get_links(article, domain)[1],
    }

# ================= RUN =================
results = []

if analyze:
    urls = []

    if bulk_file:
        content = bulk_file.read().decode("utf-8").splitlines()
        urls.extend([u.strip() for u in content if u.strip()])
    elif url:
        urls.append(url)

    for u in urls:
        try:
            results.append(analyze_url(u))
        except Exception:
            pass

    if results:
        df = pd.DataFrame(results)
        st.subheader("📊 SEO Audit Report")
        st.dataframe(df, use_container_width=True)

        excel = BytesIO()
        df.to_excel(excel, index=False)
        excel.seek(0)

        formatted_excel = format_excel(excel)

        st.download_button(
            "⬇️ Download Formatted SEO Report (Director Ready)",
            formatted_excel,
            "SEO_Audit_Report.xlsx"
        )
